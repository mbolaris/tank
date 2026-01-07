#!/usr/bin/env python3
"""Capture a GPT-5.2 poker solution tuned for the current tournament field.

This script:
1) Loads the opponent field from a tournament JSON artifact (from run_ai_tournament.py)
2) Runs one or more headless TankWorld simulations (seeds)
3) Selects the best fish via tournament-aware selection against that field
4) Captures and saves exactly one solution JSON under solutions/
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entities import Fish
from core.solutions import SolutionRecord, SolutionTracker
from core.tank_world import TankWorld, TankWorldConfig

AUTHOR = "GPT-5.2-Codex-Max"
DEFAULT_NAME = "GPT-5.2-Codex-Max Tournament Hunter"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CandidateResult:
    seed: int
    frames: int
    fish_id: int
    generation: int
    poker_games: int
    selection_avg_wr: float
    solution: SolutionRecord


def _load_opponents_from_tournament_json(
    tournament_json_path: str,
    *,
    solutions_dir: str,
) -> list[SolutionRecord]:
    with open(tournament_json_path, encoding="utf-8") as f:
        payload = json.load(f)

    ids = payload.get("selected_solution_ids", [])
    if not isinstance(ids, list) or not ids:
        raise SystemExit(
            f"{tournament_json_path!r} did not contain a non-empty 'selected_solution_ids' list."
        )

    tracker = SolutionTracker(solutions_dir=solutions_dir)
    solutions = tracker.load_all_solutions()

    by_id = {s.metadata.solution_id: s for s in solutions}

    opponents: list[SolutionRecord] = []
    missing: list[str] = []
    for sid in ids:
        if not isinstance(sid, str) or not sid:
            continue
        if sid in by_id:
            opponents.append(by_id[sid])
            continue
        prefix = next((s for s in solutions if s.metadata.solution_id.startswith(sid)), None)
        if prefix is not None:
            opponents.append(prefix)
            continue
        missing.append(sid)

    if missing:
        raise SystemExit(
            "Missing opponent solution(s) referenced by tournament JSON: " + ", ".join(missing)
        )

    return opponents


def _run_headless_simulation(*, frames: int, seed: int) -> tuple[list[Fish], int]:
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    stats_interval = max(10_000, frames // 10)
    for frame in range(frames):
        world.update()

        if frame and frame % stats_interval == 0:
            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
            poker_games = sum(
                (f.poker_stats.total_games if getattr(f, "poker_stats", None) else 0)
                for f in fish_list
            )
            logger.info(
                "Seed %s frame %s/%s: %s fish alive, %s total poker games",
                seed,
                frame,
                frames,
                len(fish_list),
                poker_games,
            )

    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    poker_games = sum(
        (f.poker_stats.total_games if getattr(f, "poker_stats", None) else 0) for f in fish_list
    )
    return fish_list, poker_games


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a GPT-5.2 poker solution for the tournament field."
    )
    parser.add_argument(
        "--tournament-json",
        default=os.path.join(".tmp", f"{AUTHOR}_baseline.json"),
        help=f"Tournament JSON artifact (default: .tmp/{AUTHOR}_baseline.json)",
    )
    parser.add_argument(
        "--solutions-dir", default="solutions", help="Solutions directory (default: solutions)"
    )
    parser.add_argument(
        "--name", default=DEFAULT_NAME, help=f"Solution name (default: {DEFAULT_NAME!r})"
    )
    parser.add_argument("--author", default=AUTHOR, help=f"Solution author (default: {AUTHOR!r})")
    parser.add_argument(
        "--frames", type=int, default=100_000, help="Frames per simulation seed (default: 100000)"
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="4242,2024,1234,8888,9001",
        help="Comma-separated list of seeds to try",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=100,
        help="Min poker games to consider a fish (default: 100)",
    )
    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=12,
        help="Candidate pool size for tournament-aware selection (default: 12)",
    )
    parser.add_argument(
        "--matchup-hands",
        type=int,
        default=400,
        help="Hands per opponent matchup during selection (default: 400)",
    )
    parser.add_argument(
        "--output-json",
        default=os.path.join(".tmp", f"{AUTHOR}_capture.json"),
        help=f"Optional capture summary JSON path (default: .tmp/{AUTHOR}_capture.json)",
    )

    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        raise SystemExit("No seeds provided.")
    if args.frames <= 0:
        raise SystemExit("--frames must be > 0")

    opponents = _load_opponents_from_tournament_json(
        args.tournament_json,
        solutions_dir=args.solutions_dir,
    )
    logger.info("Loaded %s opponent solutions from %s", len(opponents), args.tournament_json)

    tracker = SolutionTracker(solutions_dir=args.solutions_dir, min_games_threshold=args.min_games)

    results: list[CandidateResult] = []
    for seed in seeds:
        logger.info("=" * 70)
        logger.info("Simulating seed %s for %s frames", seed, args.frames)
        fish_list, poker_games = _run_headless_simulation(frames=args.frames, seed=seed)
        logger.info("Seed %s complete: %s fish, %s poker games", seed, len(fish_list), poker_games)

        ranked = tracker.identify_best_fish_for_tournament(
            fish_list,
            opponents,
            candidate_pool_size=args.candidate_pool,
            hands_per_matchup=args.matchup_hands,
            top_n=1,
        )
        if not ranked:
            logger.warning(
                "Seed %s: no eligible poker fish met min-games threshold %s", seed, args.min_games
            )
            continue

        fish, avg_wr = ranked[0]
        stats = getattr(fish, "poker_stats", None)
        games = stats.total_games if stats else 0
        generation = getattr(fish, "generation", 0)

        description = (
            f"{args.name} captured from headless TankWorld poker evolution.\n"
            f"Selected via tournament-aware head-to-head vs {len(opponents)} opponents "
            f"loaded from {args.tournament_json}.\n"
            f"Selection score: avg_wr={avg_wr:.4f} with hands_per_matchup={args.matchup_hands} "
            f"candidate_pool={args.candidate_pool} min_games={args.min_games}.\n"
            f"Repro: frames_per_seed={args.frames} seeds_tried={seeds} chosen_seed={seed}.\n"
            f"Fish: id={getattr(fish, 'fish_id', None)} generation={generation} poker_games={games}."
        )

        record = tracker.capture_solution(
            fish,
            name=args.name,
            description=description,
            author=args.author,
        )

        results.append(
            CandidateResult(
                seed=seed,
                frames=args.frames,
                fish_id=getattr(fish, "fish_id", -1),
                generation=generation,
                poker_games=games,
                selection_avg_wr=avg_wr,
                solution=record,
            )
        )

        logger.info(
            "Seed %s selected Fish %s (gen %s) games=%s selection_avg_wr=%.3f",
            seed,
            getattr(fish, "fish_id", None),
            generation,
            games,
            avg_wr,
        )

    if not results:
        raise SystemExit("No candidate solutions found across provided seeds.")

    results.sort(key=lambda r: (r.selection_avg_wr, r.poker_games), reverse=True)
    best = results[0]

    filepath = tracker.save_solution(best.solution)
    logger.info("Saved best solution to %s", filepath)
    logger.info(
        "solution_id=%s author=%s name=%s",
        best.solution.metadata.solution_id,
        best.solution.metadata.author,
        best.solution.metadata.name,
    )

    out_payload: dict[str, Any] = {
        "author": best.solution.metadata.author,
        "name": best.solution.metadata.name,
        "solution_id": best.solution.metadata.solution_id,
        "saved_path": filepath,
        "tournament_json": args.tournament_json,
        "selection_config": {
            "candidate_pool": args.candidate_pool,
            "matchup_hands": args.matchup_hands,
            "min_games": args.min_games,
        },
        "simulation": {
            "frames_per_seed": args.frames,
            "seeds_tried": seeds,
            "chosen_seed": best.seed,
        },
        "candidates": [
            {
                "seed": r.seed,
                "frames": r.frames,
                "fish_id": r.fish_id,
                "generation": r.generation,
                "poker_games": r.poker_games,
                "selection_avg_wr": r.selection_avg_wr,
                "solution_id": r.solution.metadata.solution_id,
            }
            for r in results
        ],
    }

    if args.output_json:
        os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, indent=2)
        logger.info("Wrote capture summary to %s", args.output_json)

    print(best.solution.get_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
