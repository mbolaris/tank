#!/usr/bin/env python3
"""Capture a GPT-5.2 poker solution using an extended simulation with candidate scanning."""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tank_world import TankWorld, TankWorldConfig
from core.solutions import SolutionBenchmark, SolutionRecord, SolutionTracker
from core.solutions.benchmark import SolutionBenchmarkConfig

AUTHOR = "GPT-5.2-Codex-Prime"
FINAL_NAME = "GPT-5.2-Codex-Prime Poker Overlord"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_simulation(max_frames: int = 100000, seed: int = 8888):
    """Run an extended headless simulation to evolve poker play."""
    from core.entities import Fish

    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    stats_interval = 10000
    for frame in range(max_frames):
        world.update()

        if frame and frame % stats_interval == 0:
            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
            poker_games = 0
            for fish in fish_list:
                if hasattr(fish, "poker_stats") and fish.poker_stats:
                    poker_games += fish.poker_stats.total_games

            logger.info(
                "Frame %s: %s fish alive, %s poker games played",
                frame,
                len(fish_list),
                poker_games,
            )

    logger.info("Simulation complete at frame %s", max_frames)
    return world


def gather_candidates(fish_list, min_games: int = 100):
    """Pick candidate fish using multiple metrics."""
    tracker = SolutionTracker(min_games_threshold=min_games)
    candidate_map: Dict[int, Dict] = {}

    metric_specs: List[Tuple[str, int]] = [
        ("elo", 4),
        ("net_energy", 2),
        ("roi", 2),
    ]

    for metric, top_n in metric_specs:
        for fish, score in tracker.identify_best_fish(fish_list, metric=metric, top_n=top_n):
            if fish.fish_id in candidate_map:
                continue
            candidate_map[fish.fish_id] = {
                "fish": fish,
                "metric": metric,
                "score": score,
            }

    candidates = list(candidate_map.values())
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return tracker, candidates


def evaluate_candidates(
    candidates,
    tracker: SolutionTracker,
    fish_list,
    max_frames: int,
    seed: int,
    bench: SolutionBenchmark,
):
    """Evaluate candidate fish and return the best SolutionRecord."""
    from core.entities import Fish

    if not candidates:
        logger.warning("No candidates met the poker games threshold; falling back to highest energy fish.")
        fallback_list = [f for f in fish_list if isinstance(f, Fish)]
        if not fallback_list:
            return None, None, None, None
        fallback = sorted(fallback_list, key=lambda f: getattr(f, "energy", 0.0), reverse=True)[:1]
        candidates = [
            {
                "fish": fallback[0],
                "metric": "energy",
                "score": getattr(fallback[0], "energy", 0.0),
            }
        ]

    best_record: SolutionRecord | None = None
    best_result = None
    best_stats = None
    best_entry = None

    for idx, entry in enumerate(candidates, 1):
        fish = entry["fish"]
        if not isinstance(fish, Fish):
            continue

        stats = fish.poker_stats
        games = stats.total_games if stats else 0
        win_rate = stats.get_win_rate() if stats else 0.0
        roi = stats.get_roi() if stats else 0.0
        net_energy = stats.get_net_energy() if stats else 0.0

        desc = (
            f"Candidate from {max_frames:,} frames seed {seed}; "
            f"metric={entry['metric']} score={entry['score']:.2f}; "
            f"games={games}, win_rate={win_rate:.3f}, roi={roi:.3f}, net_energy={net_energy:.1f}"
        )

        record = tracker.capture_solution(
            fish,
            name=f"{AUTHOR} Candidate {idx} (Fish {fish.fish_id})",
            description=desc,
            author=AUTHOR,
        )

        logger.info("Evaluating candidate %s (%s)", idx, desc)
        result = bench.evaluate_solution(record, verbose=True)
        record.benchmark_result = result

        logger.info(
            "Candidate %s Elo %.1f bb/100 %+0.2f",
            idx,
            result.elo_rating,
            result.weighted_bb_per_100,
        )

        if best_result is None or result.elo_rating > best_result.elo_rating:
            best_record = record
            best_result = result
            best_stats = stats
            best_entry = entry

    return best_record, best_result, best_stats, best_entry


def main():
    parser = argparse.ArgumentParser(description="Capture GPT-5.2 poker solutions with extended simulation.")
    parser.add_argument("--frames", type=int, default=100000, help="Frames per simulation run (default: 100000)")
    parser.add_argument(
        "--seeds",
        type=str,
        default="8888",
        help="Comma-separated list of seeds to try (default: 8888)",
    )
    parser.add_argument("--min-games", type=int, default=100, help="Minimum poker games to consider a fish")
    parser.add_argument("--hands", type=int, default=200, help="Hands per opponent for benchmark")
    parser.add_argument("--duplicates", type=int, default=10, help="Duplicate sets for benchmark")

    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        seeds = [8888]
    max_frames = args.frames

    logger.info("=" * 60)
    logger.info("RUNNING GPT-5.2 EXTENDED POKER SIMULATION")
    logger.info("=" * 60)

    best_overall: Optional[Tuple[SolutionRecord, SolutionBenchmark, str, int]] = None

    for seed in seeds:
        logger.info("=== Seed %s | Frames %s ===", seed, max_frames)
        world = run_simulation(max_frames=max_frames, seed=seed)

        from core.entities import Fish

        fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
        logger.info("Total fish after simulation: %s", len(fish_list))

        tracker, candidates = gather_candidates(fish_list, min_games=args.min_games)
        logger.info("Found %s candidate fish for evaluation", len(candidates))

        bench = SolutionBenchmark(
            SolutionBenchmarkConfig(
                hands_per_opponent=args.hands,
                num_duplicate_sets=args.duplicates,
                opponents=[
                    "always_fold",
                    "random",
                    "loose_passive",
                    "tight_passive",
                    "tight_aggressive",
                    "loose_aggressive",
                    "maniac",
                    "balanced",
                ],
            )
        )

        best_record, best_result, best_stats, best_entry = evaluate_candidates(
            candidates,
            tracker,
            fish_list,
            max_frames,
            seed,
            bench,
        )

        if best_record is None or best_result is None:
            logger.error("Failed to evaluate any candidate solution for seed %s.", seed)
            continue

        games = best_stats.total_games if best_stats else 0
        win_rate = best_stats.get_win_rate() if best_stats else 0.0
        roi = best_stats.get_roi() if best_stats else 0.0
        net_energy = best_stats.get_net_energy() if best_stats else 0.0

        best_record.metadata.name = FINAL_NAME
        best_record.metadata.description = (
            f"{FINAL_NAME} evolved over {max_frames:,} frames (seed {seed}) "
            f"using multi-metric candidate scan (metric {best_entry['metric']} "
            f"score {best_entry['score']:.2f}). "
            f"Poker games={games}, win_rate={win_rate:.3f}, roi={roi:.3f}, net_energy={net_energy:.1f}."
        )
        best_record.metadata.author = AUTHOR

        filepath = tracker.save_solution(best_record)
        logger.info("Best solution for seed %s saved to %s", seed, filepath)
        logger.info(
            "Final Elo %.1f (%s) bb/100 %+0.2f",
            best_result.elo_rating,
            best_result.skill_tier,
            best_result.weighted_bb_per_100,
        )

        if (
            best_overall is None
            or best_result.elo_rating > best_overall[0].benchmark_result.elo_rating
        ):
            best_overall = (best_record, bench, filepath, seed)

        print("\n" + "=" * 60)
        print(FINAL_NAME)
        print("=" * 60)
        print(best_record.get_summary())
        print("=" * 60)

    if best_overall is None:
        logger.error("No solutions produced across all seeds.")
        return None

    record, bench, filepath, seed = best_overall
    result = record.benchmark_result
    print("\nBEST OVERALL")
    print("=" * 60)
    print(f"Seed: {seed}")
    print(f"File: {filepath}")
    print(f"Elo: {result.elo_rating:.1f} ({result.skill_tier})")
    print(f"bb/100: {result.weighted_bb_per_100:+.2f}")
    print("=" * 60)

    return record


if __name__ == "__main__":
    main()
