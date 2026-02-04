#!/usr/bin/env python3
"""Capture Haiku-4.5 poker solution from a 100k frame simulation with different seed."""

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.solutions import SolutionBenchmark, SolutionRecord, SolutionTracker
from core.solutions.benchmark import SolutionBenchmarkConfig
from core.worlds import WorldRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_simulation_for_poker(max_frames: int = 100000, seed: int = 9999):
    """Run an even longer simulation to evolve superior poker skills.

    Uses 100k frames with a different seed to potentially discover
    better strategies than the Sonnet-4.5 champion.
    """
    logger.info("Starting 100k frame simulation for Haiku-4.5...")
    logger.info(f"Running {max_frames} frames with seed {seed}")

    world = WorldRegistry.create_world("tank", seed=seed, headless=True)
    world.reset(seed=seed)
    logger.info(f"World initialized with {len(world.entities_list)} entities")

    # Run simulation
    stats_interval = 10000
    for frame in range(max_frames):
        world.step()

        if frame > 0 and frame % stats_interval == 0:
            # Check poker activity
            from core.entities import Fish

            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]

            poker_games = 0
            for fish in fish_list:
                if hasattr(fish, "poker_stats") and fish.poker_stats:
                    poker_games += fish.poker_stats.total_games

            logger.info(f"Frame {frame}: {len(fish_list)} fish, {poker_games} total poker games")

    logger.info(f"Simulation complete at frame {max_frames}")
    return world


def capture_best_solution(world, author: str = "Haiku-4.5", name: str = "Haiku-4.5 Poker Ace"):
    """Capture the best performing fish as a solution."""
    from core.entities import Fish

    tracker = SolutionTracker()

    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    logger.info(f"Found {len(fish_list)} fish in simulation")

    # Find fish with poker experience
    poker_fish = []
    for fish in fish_list:
        if hasattr(fish, "poker_stats") and fish.poker_stats:
            games = fish.poker_stats.total_games
            if games > 0:
                poker_fish.append((fish, games))

    logger.info(f"Found {len(poker_fish)} fish with poker experience")

    if not poker_fish:
        # If no poker games, capture highest energy fish
        logger.info("No poker games played, capturing highest energy fish...")
        if fish_list:
            best_fish = max(fish_list, key=lambda f: f.energy)
            solution = tracker.capture_solution(
                best_fish,
                name=name,
                description="Haiku-4.5 solution evolved from 100k frame simulation",
                author=author,
            )
            return solution
        return None

    # Sort by games played and find best
    poker_fish.sort(key=lambda x: x[1], reverse=True)
    best_fish, games = poker_fish[0]

    logger.info(f"Best poker fish: #{best_fish.fish_id} with {games} games")

    # Capture the solution
    solution = tracker.capture_solution(
        best_fish,
        name=name,
        description=f"Haiku-4.5 poker strategy evolved from 100k frame simulation - {games} games played",
        author=author,
    )

    return solution


def evaluate_solution(solution: SolutionRecord):
    """Evaluate the solution against all benchmark opponents."""
    logger.info("Evaluating solution against full benchmark suite...")

    # Use comprehensive evaluation to get accurate Elo
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

    logger.info("Evaluation complete:")
    logger.info(f"  Elo Rating: {result.elo_rating:.0f}")
    logger.info(f"  Skill Tier: {result.skill_tier}")
    logger.info(f"  bb/100: {result.weighted_bb_per_100:+.2f}")

    return result


def main():
    logger.info("=" * 60)
    logger.info("CAPTURING HAIKU-4.5 POKER SOLUTION (100K FRAMES)")
    logger.info("=" * 60)

    # Run extended simulation with different seed
    world = run_simulation_for_poker(max_frames=100000, seed=9999)

    # Capture best solution
    solution = capture_best_solution(world, author="Haiku-4.5", name="Haiku-4.5 Poker Ace")

    if solution is None:
        logger.error("Failed to capture solution - no fish found!")
        return

    logger.info(f"Captured solution: {solution.metadata.name}")
    logger.info(f"  ID: {solution.metadata.solution_id}")

    # Evaluate against full benchmark suite
    try:
        evaluate_solution(solution)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Save solution
    tracker = SolutionTracker()
    filepath = tracker.save_solution(solution)
    logger.info(f"Solution saved to: {filepath}")

    # Print summary
    print("\n" + "=" * 60)
    print("HAIKU-4.5 POKER ACE CAPTURED (100K FRAMES)")
    print("=" * 60)
    print(solution.get_summary())
    print("=" * 60)

    return solution


if __name__ == "__main__":
    solution = main()
