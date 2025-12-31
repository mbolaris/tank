#!/usr/bin/env python3
"""Run a per-author poker solution tournament.

This script:
1) Loads all solutions from a solutions directory
2) Re-evaluates them with a shared benchmark config
3) Selects the single best solution per author (by Elo)
4) Runs a round-robin head-to-head tournament among those winners
5) Writes a human-readable report (and optional JSON artifacts)

For reproducibility, head-to-head seeding is deterministic (see core/solutions/benchmark.py).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.solutions import SolutionRecord, SolutionTracker
from core.solutions.benchmark import SolutionBenchmark, SolutionBenchmarkConfig


@dataclass(frozen=True)
class TournamentConfig:
    solutions_dir: str
    benchmark_hands: int
    benchmark_duplicates: int
    benchmark_seed: int
    matchup_hands: int
    output_path: str
    json_output_path: Optional[str]
    write_back: bool
    include_all_authors: bool
    include_live_tank: bool
    api_base_url: str
    tank_id: Optional[str]
    live_name: str
    live_author: str
    live_description: Optional[str]
    live_selection_mode: str
    live_candidate_pool_size: int
    live_hands_per_matchup: int
    live_opponent_limit: int


def _http_json(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    timeout_s: float = 5.0,
) -> Dict[str, Any]:
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body, headers=headers, method=method)
    with urlopen(req, timeout=timeout_s) as resp:  # nosec B310 (local trusted URL)
        payload = resp.read().decode("utf-8")
        return json.loads(payload)


def _resolve_default_tank_id(api_base_url: str) -> Optional[str]:
    url = api_base_url.rstrip("/") + "/api/tanks"
    data = _http_json(url, method="GET")

    default_id = data.get("default_tank_id")
    if isinstance(default_id, str) and default_id:
        return default_id

    tanks = data.get("tanks", [])
    if isinstance(tanks, list) and tanks:
        first = tanks[0]
        if isinstance(first, dict):
            tank = first.get("tank", {})
            if isinstance(tank, dict):
                tid = tank.get("tank_id")
                if isinstance(tid, str) and tid:
                    return tid

    return None


def _capture_best_from_live_tank(config: TournamentConfig) -> Optional[str]:
    tank_id = config.tank_id or _resolve_default_tank_id(config.api_base_url)
    if not tank_id:
        raise RuntimeError("Could not determine a tank_id from /api/tanks; pass --tank-id explicitly.")

    url = config.api_base_url.rstrip("/") + f"/api/solutions/capture/{tank_id}"
    req = {
        "name": config.live_name,
        "description": config.live_description,
        "author": config.live_author,
        "evaluate": False,
        "selection_mode": config.live_selection_mode,
        "candidate_pool_size": config.live_candidate_pool_size,
        "hands_per_matchup": config.live_hands_per_matchup,
        "opponent_limit": config.live_opponent_limit,
    }
    resp = _http_json(url, method="POST", data=req)
    solution_id = resp.get("solution_id")
    if isinstance(solution_id, str) and solution_id:
        return solution_id
    return None


def _git_head_sha() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def _git_branch() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    except Exception:
        return None


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _avg_head_to_head_win_rates(
    solution_ids: List[str],
    head_to_head: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    avg: Dict[str, float] = {}
    for sid in solution_ids:
        row = head_to_head.get(sid, {})
        vals = [v for opp, v in row.items() if opp != sid]
        avg[sid] = sum(vals) / len(vals) if vals else 0.5
    return avg


def _format_head_to_head_matrix(
    selected: List[SolutionRecord],
    head_to_head: Dict[str, Dict[str, float]],
) -> List[str]:
    ids = [s.metadata.solution_id for s in selected]
    authors = [s.metadata.author for s in selected]

    col_labels = [a[:10] for a in authors]
    lines = []
    lines.append(" " * 18 + " ".join([f"{c:>10}" for c in col_labels]))

    for row_sol in selected:
        row_id = row_sol.metadata.solution_id
        row_author = row_sol.metadata.author[:16]
        cells: List[str] = []
        for col_id in ids:
            if col_id == row_id:
                cells.append("   --    ")
            else:
                wr = head_to_head.get(row_id, {}).get(col_id, 0.5)
                cells.append(f"{wr*100:7.1f}%")
        lines.append(f"{row_author:16} " + " ".join([f"{c:>10}" for c in cells]))
    return lines


def load_solutions(solutions_dir: str) -> List[SolutionRecord]:
    tracker = SolutionTracker(solutions_dir=solutions_dir)
    return tracker.load_all_solutions()


def choose_best_per_author(solutions: List[SolutionRecord]) -> List[SolutionRecord]:
    by_author: Dict[str, List[SolutionRecord]] = defaultdict(list)
    for sol in solutions:
        author = (sol.metadata.author or "unknown").strip() or "unknown"
        by_author[author].append(sol)

    winners: List[SolutionRecord] = []
    for author, items in by_author.items():
        items.sort(
            key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0.0,
            reverse=True,
        )
        winners.append(items[0])

    winners.sort(
        key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0.0,
        reverse=True,
    )
    return winners


def run_tournament(config: TournamentConfig) -> Tuple[str, Dict[str, Any]]:
    started_at = datetime.utcnow().isoformat()
    head_sha = _git_head_sha()
    branch = _git_branch()

    captured_live_solution_id: Optional[str] = None
    if config.include_live_tank:
        try:
            captured_live_solution_id = _capture_best_from_live_tank(config)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"Warning: live tank capture failed ({exc}); continuing without live tank solution.")
        except Exception as exc:
            print(f"Warning: live tank capture failed ({exc}); continuing without live tank solution.")

    solutions = load_solutions(config.solutions_dir)
    if not solutions:
        raise SystemExit(f"No solutions found in {config.solutions_dir!r}.")

    bench = SolutionBenchmark(
        SolutionBenchmarkConfig(
            hands_per_opponent=config.benchmark_hands,
            num_duplicate_sets=config.benchmark_duplicates,
            base_seed=config.benchmark_seed,
        )
    )

    bench.evaluate_all_solutions(solutions, verbose=True)

    if config.write_back:
        tracker = SolutionTracker(solutions_dir=config.solutions_dir)
        for sol in solutions:
            tracker.save_solution(sol)

        bench.generate_report(solutions, output_path=os.path.join(config.solutions_dir, "benchmark_report.txt"))

    selected = choose_best_per_author(solutions)

    comparison = bench.compare_solutions(
        selected,
        hands_per_matchup=config.matchup_hands,
        verbose=True,
    )

    avg_wr = _avg_head_to_head_win_rates(comparison.solution_ids, comparison.head_to_head)
    standings = sorted(avg_wr.items(), key=lambda kv: kv[1], reverse=True)
    id_to_solution = {s.metadata.solution_id: s for s in selected}

    lines: List[str] = []
    lines.extend(
        [
            "=" * 60,
            "TankWorld AI Tournament (Best Solution Per Author)",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Git Branch: {branch or 'unknown'}",
            f"Git Commit: {head_sha or 'unknown'}",
            "",
            "CONFIG",
            "-" * 60,
            f"solutions_dir: {config.solutions_dir}",
            f"benchmark_hands_per_opponent: {config.benchmark_hands}",
            f"benchmark_duplicate_sets: {config.benchmark_duplicates}",
            f"benchmark_base_seed: {config.benchmark_seed}",
            f"head_to_head_hands_per_matchup: {config.matchup_hands}",
            "",
            "SELECTED (best per author after re-eval)",
            "-" * 60,
        ]
    )

    for sol in selected:
        br = sol.benchmark_result
        lines.append(
            f"- {sol.metadata.author:<18} | {sol.metadata.name:<30} | "
            f"Elo {br.elo_rating:7.1f} ({br.skill_tier:<8}) | bb/100 {br.weighted_bb_per_100:+8.2f} | "
            f"id {sol.metadata.solution_id}"
        )

    lines.extend(["", "TOURNAMENT STANDINGS (avg head-to-head win rate)", "-" * 60])
    for rank, (sid, wr) in enumerate(standings, 1):
        sol = id_to_solution[sid]
        br = sol.benchmark_result
        lines.append(
            f"#{rank:<2} {sol.metadata.author:<18} | WR {wr*100:6.1f}% | "
            f"Elo {br.elo_rating:7.1f} | bb/100 {br.weighted_bb_per_100:+8.2f} | {sol.metadata.name}"
        )

    lines.extend(["", "HEAD-TO-HEAD MATRIX (row beats column)", "-" * 60])
    lines.extend(_format_head_to_head_matrix(selected, comparison.head_to_head))
    lines.append("")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    artifact: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "started_at": started_at,
        "git": {"branch": branch, "commit": head_sha},
        "config": asdict(config),
        "live_capture": {
            "enabled": config.include_live_tank,
            "api_base_url": config.api_base_url,
            "tank_id": config.tank_id,
            "captured_solution_id": captured_live_solution_id,
        },
        "selected_solution_ids": [s.metadata.solution_id for s in selected],
        "selected": [
            {
                "author": s.metadata.author,
                "name": s.metadata.name,
                "solution_id": s.metadata.solution_id,
                "elo": s.benchmark_result.elo_rating if s.benchmark_result else None,
                "skill_tier": s.benchmark_result.skill_tier if s.benchmark_result else None,
                "bb_per_100": s.benchmark_result.weighted_bb_per_100 if s.benchmark_result else None,
            }
            for s in selected
        ],
        "tournament": {
            "solution_ids": comparison.solution_ids,
            "head_to_head": comparison.head_to_head,
            "avg_win_rate": avg_wr,
            "standings": standings,
            "compared_at": comparison.compared_at,
        },
    }

    return report_text, artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a best-per-author poker solution tournament.")
    parser.add_argument("--solutions-dir", default="solutions", help="Solutions directory (default: solutions)")
    parser.add_argument("--benchmark-hands", type=int, default=300, help="Hands per opponent (default: 300)")
    parser.add_argument("--benchmark-duplicates", type=int, default=10, help="Duplicate sets (default: 10)")
    parser.add_argument("--benchmark-seed", type=int, default=42, help="Benchmark base seed (default: 42)")
    parser.add_argument("--matchup-hands", type=int, default=1000, help="Hands per head-to-head matchup (default: 1000)")
    parser.add_argument(
        "--output",
        default=os.path.join("solutions", "ai_tournament_report.txt"),
        help="Path to write the tournament report (default: solutions/ai_tournament_report.txt)",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to write JSON results (recommended: results/ai_tournament_results.json)",
    )
    parser.add_argument(
        "--write-back",
        action="store_true",
        help="Write updated benchmark results back into solution JSON files and regenerate solutions/benchmark_report.txt",
    )
    parser.add_argument(
        "--include-live-tank",
        action="store_true",
        help="Capture best fish from a running local tank via API and include it as an extra author",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://localhost:8000",
        help="Base URL for TankWorld server API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--tank-id",
        default=None,
        help="Tank ID to capture from (defaults to /api/tanks default_tank_id)",
    )
    parser.add_argument(
        "--live-name",
        default="Local Tank Best",
        help="Solution name for captured live tank fish (default: Local Tank Best)",
    )
    parser.add_argument(
        "--live-author",
        default="LocalSimulation",
        help="Author name for captured live tank fish (default: LocalSimulation)",
    )
    parser.add_argument(
        "--live-description",
        default=None,
        help="Optional description for captured live tank fish",
    )
    parser.add_argument(
        "--live-selection",
        choices=["heuristic_elo", "tournament"],
        default="heuristic_elo",
        help="How to select the live tank fish to capture (default: heuristic_elo)",
    )
    parser.add_argument(
        "--live-candidate-pool",
        type=int,
        default=12,
        help="Candidate pool size for live selection_mode=tournament (default: 12)",
    )
    parser.add_argument(
        "--live-hands-per-matchup",
        type=int,
        default=500,
        help="Hands per matchup for live selection_mode=tournament (default: 500)",
    )
    parser.add_argument(
        "--live-opponent-limit",
        type=int,
        default=8,
        help="How many top opponent solutions to use for live selection_mode=tournament (default: 8)",
    )
    args = parser.parse_args()

    cfg = TournamentConfig(
        solutions_dir=args.solutions_dir,
        benchmark_hands=args.benchmark_hands,
        benchmark_duplicates=args.benchmark_duplicates,
        benchmark_seed=args.benchmark_seed,
        matchup_hands=args.matchup_hands,
        output_path=args.output,
        json_output_path=args.json_output,
        write_back=args.write_back,
        include_all_authors=True,
        include_live_tank=args.include_live_tank,
        api_base_url=args.api_base_url,
        tank_id=args.tank_id,
        live_name=args.live_name,
        live_author=args.live_author,
        live_description=args.live_description,
        live_selection_mode=args.live_selection,
        live_candidate_pool_size=args.live_candidate_pool,
        live_hands_per_matchup=args.live_hands_per_matchup,
        live_opponent_limit=args.live_opponent_limit,
    )

    report_text, artifact = run_tournament(cfg)

    _ensure_parent_dir(cfg.output_path)
    with open(cfg.output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    if cfg.json_output_path:
        _ensure_parent_dir(cfg.json_output_path)
        with open(cfg.json_output_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

    print(report_text)
    print(f"\nSaved report to: {cfg.output_path}")
    if cfg.json_output_path:
        print(f"Saved JSON results to: {cfg.json_output_path}")


if __name__ == "__main__":
    main()
