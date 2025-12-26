#!/usr/bin/env python3
"""Run reproducible poker evolution experiments (3 tanks + benchmark).

This script runs headless simulations for fixed seeds, exports per-tank stats,
and evaluates top poker fish vs the standard algorithm using duplicate deals.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_SEEDS = [101, 202, 303]
DEFAULT_FRAMES = 108000  # 30 FPS * 3600 seconds
DEFAULT_STATS_INTERVAL = 1000
DEFAULT_TOP_N = 3
DEFAULT_MIN_GAMES = 5
DEFAULT_HANDS = 1000
DEFAULT_SMALL_BLIND = 5.0
DEFAULT_BIG_BLIND = 10.0
DEFAULT_STARTING_STACK = 50000.0


@dataclass
class CandidateResult:
    fish_id: int
    generation: int
    strategy_id: str
    strategy_snapshot: Dict[str, Any]
    poker_stats: Dict[str, Any]
    benchmark: Dict[str, Any]


def _parse_seeds(raw: str) -> List[int]:
    seeds = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        seeds.append(int(part))
    return seeds


def _get_timestamp(raw: Optional[str] = None) -> str:
    if raw:
        return raw
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _safe_strategy_snapshot(strategy: Any) -> Dict[str, Any]:
    if strategy is None:
        return {}
    to_dict = getattr(strategy, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return {"strategy_id": getattr(strategy, "strategy_id", "unknown")}


def _select_top_fish(
    fish_list: Sequence[Any],
    top_n: int,
    min_games: int,
    rng_seed: int,
) -> Tuple[List[Any], str]:
    """Select top fish based on poker net energy, with deterministic fallback."""
    eligible = []
    for fish in fish_list:
        stats = getattr(fish, "poker_stats", None)
        if stats is None:
            continue
        if getattr(stats, "total_games", 0) >= min_games:
            eligible.append(fish)

    if eligible:
        eligible.sort(key=lambda f: f.poker_stats.get_net_energy(), reverse=True)
        return eligible[:top_n], "poker_stats_net_energy"

    # Fallback to deterministic random sample if no poker stats
    import random

    rng = random.Random(rng_seed)
    if not fish_list:
        return [], "no_fish"
    sample = list(fish_list)
    rng.shuffle(sample)
    return sample[:top_n], "random_fallback"


def _evaluate_candidate_vs_standard(
    candidate_fish: Any,
    candidate_strategy: Any,
    *,
    hands: int,
    small_blind: float,
    big_blind: float,
    starting_stack: float,
    rng_seed: int,
) -> Dict[str, Any]:
    from core.auto_evaluate_poker import AutoEvaluatePokerGame

    game = AutoEvaluatePokerGame(
        game_id=f"benchmark_fish_{candidate_fish.fish_id}",
        player_pool=[
            {
                "name": f"Fish #{candidate_fish.fish_id}",
                "poker_strategy": candidate_strategy,
                "fish_id": candidate_fish.fish_id,
                "generation": getattr(candidate_fish, "generation", 0),
                "species": getattr(candidate_fish, "species", "fish"),
            }
        ],
        standard_energy=starting_stack,
        max_hands=hands,
        small_blind=small_blind,
        big_blind=big_blind,
        rng_seed=rng_seed,
        include_standard_player=True,
        position_rotation=True,
    )

    stats = game.run_evaluation()
    candidate_stats = next((p for p in stats.players if not p.get("is_standard")), None)
    standard_stats = next((p for p in stats.players if p.get("is_standard")), None)

    num_players = len(stats.players) if stats.players else 2
    deal_sets = stats.hands_played / num_players if stats.hands_played else 0

    return {
        "hands_played": stats.hands_played,
        "position_rotation": True,
        "players_per_hand": num_players,
        "duplicate_deal_sets": int(deal_sets),
        "candidate": candidate_stats or {},
        "standard": standard_stats or {},
    }


def _summarize_candidates(candidates: List[CandidateResult]) -> Dict[str, Any]:
    if not candidates:
        return {"count": 0}

    bb_values = [c.benchmark["candidate"].get("bb_per_100", 0.0) for c in candidates]
    win_values = [c.benchmark["candidate"].get("win_rate", 0.0) for c in candidates]
    net_values = [c.benchmark["candidate"].get("net_energy", 0.0) for c in candidates]

    return {
        "count": len(candidates),
        "bb_per_100": {
            "mean": round(statistics.mean(bb_values), 3),
            "median": round(statistics.median(bb_values), 3),
            "min": round(min(bb_values), 3),
            "max": round(max(bb_values), 3),
        },
        "win_rate_pct": {
            "mean": round(statistics.mean(win_values), 2),
            "median": round(statistics.median(win_values), 2),
            "min": round(min(win_values), 2),
            "max": round(max(win_values), 2),
        },
        "net_energy": {
            "mean": round(statistics.mean(net_values), 2),
            "median": round(statistics.median(net_values), 2),
            "min": round(min(net_values), 2),
            "max": round(max(net_values), 2),
        },
    }


def _get_git_commit() -> Optional[str]:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _build_metadata(args: argparse.Namespace, timestamp: str) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "variant": args.variant,
        "command": " ".join([sys.executable] + sys.argv),
        "seeds": args.seeds,
        "frames": args.frames,
        "stats_interval": args.stats_interval,
        "top_n": args.top_n,
        "min_poker_games": args.min_games,
        "benchmark_hands": args.hands,
        "small_blind": args.small_blind,
        "big_blind": args.big_blind,
        "starting_stack": args.starting_stack,
        "position_rotation": True,
        "git_commit": _get_git_commit(),
        "python": sys.version.split()[0],
        "env_overrides": {
            "TANK_POKER_EVOLUTION_EXPERIMENT": os.getenv("TANK_POKER_EVOLUTION_EXPERIMENT"),
            "TANK_POKER_WINNER_WEIGHT": os.getenv("TANK_POKER_WINNER_WEIGHT"),
            "TANK_POKER_MUTATION_RATE_MULTIPLIER": os.getenv("TANK_POKER_MUTATION_RATE_MULTIPLIER"),
            "TANK_POKER_MUTATION_STRENGTH_MULTIPLIER": os.getenv("TANK_POKER_MUTATION_STRENGTH_MULTIPLIER"),
            "TANK_POKER_NOVELTY_INJECTION_RATE": os.getenv("TANK_POKER_NOVELTY_INJECTION_RATE"),
            "TANK_POKER_STAKE_MULTIPLIER": os.getenv("TANK_POKER_STAKE_MULTIPLIER"),
            "TANK_POKER_MAX_BET_CAP": os.getenv("TANK_POKER_MAX_BET_CAP"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run poker evolution experiment (3 tanks + benchmark)."
    )
    parser.add_argument(
        "--variant",
        default="baseline",
        help="Result label (baseline or improved).",
    )
    parser.add_argument(
        "--seeds",
        default=",".join(str(s) for s in DEFAULT_SEEDS),
        help="Comma-separated seeds (default: 101,202,303).",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=DEFAULT_FRAMES,
        help="Max frames per tank (default: 108000).",
    )
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=DEFAULT_STATS_INTERVAL,
        help="Stats interval for headless run.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Top N fish to benchmark per tank.",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=DEFAULT_MIN_GAMES,
        help="Minimum poker games for eligibility.",
    )
    parser.add_argument(
        "--hands",
        type=int,
        default=DEFAULT_HANDS,
        help="Benchmark hands per candidate vs standard.",
    )
    parser.add_argument(
        "--small-blind",
        type=float,
        default=DEFAULT_SMALL_BLIND,
        help="Small blind amount.",
    )
    parser.add_argument(
        "--big-blind",
        type=float,
        default=DEFAULT_BIG_BLIND,
        help="Big blind amount.",
    )
    parser.add_argument(
        "--starting-stack",
        type=float,
        default=DEFAULT_STARTING_STACK,
        help="Starting stack for benchmark players.",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Override timestamp folder (YYYYMMDD_HHMMSS).",
    )
    parser.add_argument(
        "--enable-poker-evolution",
        action="store_true",
        help="Enable poker evolution tuning via env overrides.",
    )
    args = parser.parse_args()

    seeds = _parse_seeds(args.seeds)
    if len(seeds) != 3:
        raise SystemExit("Expected exactly 3 seeds (e.g., 101,202,303).")

    if args.enable_poker_evolution:
        os.environ["TANK_POKER_EVOLUTION_EXPERIMENT"] = "1"

    # Import after env overrides are set.
    from core.simulation_stats_exporter import SimulationStatsExporter
    from core.tank_world import TankWorld, TankWorldConfig

    timestamp = _get_timestamp(args.timestamp)
    results_root = ROOT / "results" / timestamp / args.variant
    results_root.mkdir(parents=True, exist_ok=True)

    metadata = _build_metadata(args, timestamp)
    _write_json(results_root / "run_metadata.json", metadata)

    tank_ids = ["A", "B", "C"]
    benchmark_output: Dict[str, Any] = {
        "metadata": metadata,
        "tanks": {},
        "aggregate": {},
    }

    for tank_id, seed in zip(tank_ids, seeds):
        start_time = time.time()
        print(f"[{tank_id}] Running headless sim (seed={seed}, frames={args.frames})...")

        config = TankWorldConfig(headless=True)
        world = TankWorld(config=config, seed=seed)
        world.run_headless(
            max_frames=args.frames,
            stats_interval=args.stats_interval,
            export_json=None,
        )

        export_path = results_root / f"{tank_id}.json"
        SimulationStatsExporter(world.engine).export_stats_json(str(export_path))
        stats_snapshot = world.engine.get_stats()
        if export_path.exists():
            export_payload = json.loads(export_path.read_text(encoding="utf-8"))
            export_payload["stats_snapshot"] = stats_snapshot
            _write_json(export_path, export_payload)

        fish_list = world.engine.get_fish_list()
        ecosystem = world.engine.ecosystem

        leaderboard = []
        strategy_distribution = {}
        if ecosystem is not None:
            leaderboard = ecosystem.get_poker_leaderboard(
                fish_list, limit=args.top_n, sort_by="net_energy"
            )
            strategy_distribution = ecosystem.get_poker_strategy_distribution(fish_list)

        selected, selection_basis = _select_top_fish(
            fish_list, args.top_n, args.min_games, seed
        )

        candidates: List[CandidateResult] = []
        for idx, fish in enumerate(selected):
            strategy = fish.get_poker_strategy()
            if strategy is None:
                continue

            benchmark = _evaluate_candidate_vs_standard(
                fish,
                strategy,
                hands=args.hands,
                small_blind=args.small_blind,
                big_blind=args.big_blind,
                starting_stack=args.starting_stack,
                rng_seed=seed * 1000 + idx,
            )

            poker_stats = {}
            if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
                poker_stats = fish.poker_stats.get_stats_dict()

            candidates.append(
                CandidateResult(
                    fish_id=fish.fish_id,
                    generation=getattr(fish, "generation", 0),
                    strategy_id=getattr(strategy, "strategy_id", "unknown"),
                    strategy_snapshot=_safe_strategy_snapshot(strategy),
                    poker_stats=poker_stats,
                    benchmark=benchmark,
                )
            )

        tank_payload = {
            "seed": seed,
            "selection_basis": selection_basis,
            "leaderboard": leaderboard,
            "strategy_distribution": strategy_distribution,
            "energy_summary": {
                "energy_from_poker": stats_snapshot.get("energy_from_poker", 0.0),
                "energy_from_poker_plant": stats_snapshot.get("energy_from_poker_plant", 0.0),
                "energy_from_nectar": stats_snapshot.get("energy_from_nectar", 0.0),
                "energy_from_live_food": stats_snapshot.get("energy_from_live_food", 0.0),
                "energy_from_falling_food": stats_snapshot.get("energy_from_falling_food", 0.0),
                "energy_sources_recent": stats_snapshot.get("energy_sources_recent", {}),
                "energy_burn_recent": stats_snapshot.get("energy_burn_recent", {}),
                "energy_net_recent": stats_snapshot.get("energy_net_recent", 0.0),
                "poker_stats_summary": stats_snapshot.get("poker_stats", {}),
                "total_population": stats_snapshot.get("total_population", 0),
                "fish_count": stats_snapshot.get("fish_count", 0),
                "total_births": stats_snapshot.get("total_births", 0),
            },
            "candidates": [asdict(c) for c in candidates],
            "aggregate": _summarize_candidates(candidates),
            "wall_time_seconds": round(time.time() - start_time, 1),
        }
        benchmark_output["tanks"][tank_id] = tank_payload

    all_candidates: List[CandidateResult] = []
    for tank_data in benchmark_output["tanks"].values():
        for candidate in tank_data.get("candidates", []):
            all_candidates.append(CandidateResult(**candidate))

    benchmark_output["aggregate"] = _summarize_candidates(all_candidates)

    _write_json(results_root / "poker_benchmark.json", benchmark_output)
    print(f"Results saved to {results_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
