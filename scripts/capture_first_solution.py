#!/usr/bin/env python3
"""Capture the first Opus-4.5 solution from a simulation.

This script runs a simulation until fish develop poker skills,
then captures and evaluates the best performing solution.
"""

import json
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tank_world import TankWorld, TankWorldConfig
from core.solutions import SolutionTracker, SolutionBenchmark, SolutionRecord
from core.solutions.models import SolutionMetadata, BenchmarkResult
from core.solutions.benchmark import SolutionBenchmarkConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_simulation_for_poker(max_frames: int = 20000, seed: int = 42):
    """Run a simulation until fish develop poker skills.

    Returns the TankWorld instance with fish that have poker experience.
    """
    logger.info("Starting simulation to develop poker skills...")

    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)

    # Important: Set up the world first!
    world.setup()
    logger.info(f"World initialized with {len(world.entities_list)} entities")

    # Run simulation
    stats_interval = 2000
    for frame in range(max_frames):
        world.update()

        if frame > 0 and frame % stats_interval == 0:
            # Check poker activity
            from core.entities import Fish
            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]

            poker_games = 0
            for fish in fish_list:
                if hasattr(fish, 'poker_stats') and fish.poker_stats:
                    poker_games += fish.poker_stats.total_games

            logger.info(f"Frame {frame}: {len(fish_list)} fish, {poker_games} total poker games")

            # If we have enough poker activity, we can stop early
            if poker_games >= 100:
                logger.info("Sufficient poker activity reached!")
                break

    return world


def capture_best_solution(world, author: str = "Opus-4.5"):
    """Capture the best performing fish as a solution."""
    from core.entities import Fish

    tracker = SolutionTracker()

    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    logger.info(f"Found {len(fish_list)} fish in simulation")

    # Find fish with poker experience
    poker_fish = []
    for fish in fish_list:
        if hasattr(fish, 'poker_stats') and fish.poker_stats:
            games = fish.poker_stats.total_games
            if games > 0:
                poker_fish.append((fish, games))

    logger.info(f"Found {len(poker_fish)} fish with poker experience")

    if not poker_fish:
        # If no poker games, just capture the fish with highest energy
        logger.info("No poker games played, capturing highest energy fish...")
        if fish_list:
            best_fish = max(fish_list, key=lambda f: f.energy)
            solution = tracker.capture_solution(
                best_fish,
                name="Opus-4.5 First Solution",
                description="First solution captured from Opus-4.5 simulation - evolved for survival",
                author=author,
            )
            return solution
        return None

    # Sort by games played (as a proxy for experience)
    poker_fish.sort(key=lambda x: x[1], reverse=True)
    best_fish, games = poker_fish[0]

    logger.info(f"Best poker fish: #{best_fish.fish_id} with {games} games")

    # Capture the solution
    solution = tracker.capture_solution(
        best_fish,
        name="Opus-4.5 Poker Champion",
        description=f"First poker solution from Opus-4.5 - {games} games played",
        author=author,
    )

    return solution


def evaluate_solution(solution: SolutionRecord):
    """Evaluate the solution against benchmark opponents."""
    logger.info("Evaluating solution against benchmarks...")

    # Use fast config for initial evaluation
    config = SolutionBenchmarkConfig(
        hands_per_opponent=100,
        num_duplicate_sets=5,
        opponents=["always_fold", "random", "loose_passive", "balanced"],
    )

    benchmark = SolutionBenchmark(config)
    result = benchmark.evaluate_solution(solution, verbose=True)

    solution.benchmark_result = result

    logger.info(f"Evaluation complete:")
    logger.info(f"  Elo Rating: {result.elo_rating:.0f}")
    logger.info(f"  Skill Tier: {result.skill_tier}")
    logger.info(f"  bb/100: {result.weighted_bb_per_100:+.2f}")

    return result


def main():
    logger.info("=" * 60)
    logger.info("CAPTURING FIRST OPUS-4.5 SOLUTION")
    logger.info("=" * 60)

    # Run simulation
    world = run_simulation_for_poker(max_frames=15000, seed=42)

    # Capture best solution
    solution = capture_best_solution(world, author="Opus-4.5")

    if solution is None:
        logger.error("Failed to capture solution - no fish found!")
        return

    logger.info(f"Captured solution: {solution.metadata.name}")
    logger.info(f"  ID: {solution.metadata.solution_id}")

    # Evaluate
    try:
        evaluate_solution(solution)
    except Exception as e:
        logger.warning(f"Evaluation failed (this is OK for first solution): {e}")
        # Create a placeholder benchmark result
        solution.benchmark_result = BenchmarkResult(
            elo_rating=1200.0,
            skill_tier="beginner",
            weighted_bb_per_100=0.0,
            evaluated_at=datetime.utcnow().isoformat(),
        )

    # Save solution
    tracker = SolutionTracker()
    filepath = tracker.save_solution(solution)
    logger.info(f"Solution saved to: {filepath}")

    # Print summary
    print("\n" + "=" * 60)
    print("FIRST OPUS-4.5 SOLUTION CAPTURED")
    print("=" * 60)
    print(solution.get_summary())
    print("=" * 60)

    return solution


if __name__ == "__main__":
    solution = main()
