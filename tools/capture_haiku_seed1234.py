#!/usr/bin/env python3
"""Test seed 1234 with 75k frames."""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.solutions import SolutionBenchmark, SolutionTracker
from core.solutions.benchmark import SolutionBenchmarkConfig
from core.tank_world import TankWorld, TankWorldConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_sim(max_frames=75000, seed=1234):
    logger.info(f"Running {max_frames} frames with seed {seed}")
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()
    for frame in range(max_frames):
        world.update()
        if frame > 0 and frame % 5000 == 0:
            from core.entities import Fish

            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
            poker_games = sum(
                f.poker_stats.total_games if hasattr(f, "poker_stats") and f.poker_stats else 0
                for f in fish_list
            )
            logger.info(f"Frame {frame}: {len(fish_list)} fish, {poker_games} total poker games")
    return world


def capture_and_eval(world):
    from core.entities import Fish

    tracker = SolutionTracker()
    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    poker_fish = [
        (f, f.poker_stats.total_games)
        for f in fish_list
        if hasattr(f, "poker_stats") and f.poker_stats and f.poker_stats.total_games > 0
    ]
    if not poker_fish:
        if fish_list:
            best_fish = max(fish_list, key=lambda f: f.energy)
        else:
            logger.error("No fish found!")
            return None
    else:
        poker_fish.sort(key=lambda x: x[1], reverse=True)
        best_fish = poker_fish[0][0]

    solution = tracker.capture_solution(
        best_fish,
        name="Haiku-4.5 Poker Stratege",
        description="75k frames seed 1234",
        author="Haiku-4.5",
    )

    config = SolutionBenchmarkConfig(
        hands_per_opponent=200,
        num_duplicate_sets=10,
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
    benchmark = SolutionBenchmark(config)
    result = benchmark.evaluate_solution(solution, verbose=True)
    solution.benchmark_result = result

    logger.info(
        f"SEED 1234: Elo {result.elo_rating:.0f}, Tier {result.skill_tier}, bb/100 {result.weighted_bb_per_100:+.2f}"
    )
    tracker.save_solution(solution)
    return solution


world = run_sim()
solution = capture_and_eval(world)
