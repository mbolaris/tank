#!/usr/bin/env python3
"""Run a comprehensive tournament to evaluate AI-submitted solutions.

This script creates solutions from multiple simulated AI models,
evaluates them against benchmark opponents, and generates a tournament report.
"""

import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tank_world import TankWorld, TankWorldConfig
from core.solutions import SolutionTracker, SolutionBenchmark, SolutionRecord
from core.solutions.benchmark import SolutionBenchmarkConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define AI models to simulate with different configurations
AI_MODELS = [
    {"name": "Claude Opus-4.5", "author": "Opus-4.5", "seed": 1001, "frames": 30000},
    {"name": "Claude Sonnet-4.5", "author": "Sonnet-4.5", "seed": 2002, "frames": 35000},
    {"name": "Claude Haiku-4.5", "author": "Haiku-4.5", "seed": 3003, "frames": 25000},
    {"name": "GPT-5 Prime", "author": "GPT-5", "seed": 4004, "frames": 32000},
    {"name": "Gemini 2.5 Ultra", "author": "Gemini-2.5", "seed": 5005, "frames": 28000},
]


def run_simulation(seed: int, max_frames: int) -> TankWorld:
    """Run a simulation to evolve fish with poker skills."""
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    for frame in range(max_frames):
        world.update()
        if frame > 0 and frame % 10000 == 0:
            logger.info(f"  Frame {frame}/{max_frames}")

    return world


def capture_solution_from_world(world: TankWorld, name: str, author: str) -> SolutionRecord:
    """Capture the best fish as a solution."""
    from core.entities import Fish

    tracker = SolutionTracker()
    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]

    # Find fish with most poker experience or highest energy
    best_fish = None
    best_score = -1

    for fish in fish_list:
        score = fish.energy
        if hasattr(fish, "poker_stats") and fish.poker_stats:
            score += fish.poker_stats.total_games * 10
            if fish.poker_stats.wins > 0:
                score += fish.poker_stats.wins * 5
        if score > best_score:
            best_score = score
            best_fish = fish

    if best_fish is None and fish_list:
        best_fish = fish_list[0]

    solution = tracker.capture_solution(
        best_fish,
        name=f"{name} Champion",
        description=f"AI solution from {author} evolved in tournament simulation",
        author=author,
    )

    return solution


def evaluate_solution(solution: SolutionRecord, benchmark: SolutionBenchmark):
    """Evaluate a solution against all benchmark opponents."""
    result = benchmark.evaluate_solution(solution, verbose=False)
    solution.benchmark_result = result
    return result


def run_tournament():
    """Run the full AI tournament."""
    print("=" * 70)
    print("                    AI POKER SOLUTIONS TOURNAMENT")
    print("=" * 70)
    print()

    tracker = SolutionTracker()
    benchmark = SolutionBenchmark(
        SolutionBenchmarkConfig(
            hands_per_opponent=300,
            num_duplicate_sets=15,
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

    # Load existing solutions
    existing_solutions = tracker.load_all_solutions()
    logger.info(f"Found {len(existing_solutions)} existing solutions")

    all_solutions = list(existing_solutions)

    # Create solutions for each AI model
    print("\n[PHASE 1] Creating AI Solutions")
    print("-" * 70)

    for model in AI_MODELS:
        print(f"\nSimulating {model['name']}...")
        print(f"  Running {model['frames']} frames with seed {model['seed']}")

        world = run_simulation(model["seed"], model["frames"])
        solution = capture_solution_from_world(world, model["name"], model["author"])

        # Save the solution
        filepath = tracker.save_solution(solution)
        all_solutions.append(solution)
        print(f"  Captured: {solution.metadata.name} (ID: {solution.metadata.solution_id[:8]})")

    print(f"\nTotal solutions: {len(all_solutions)}")

    # Evaluate all solutions
    print("\n[PHASE 2] Evaluating Solutions Against Benchmarks")
    print("-" * 70)

    for i, solution in enumerate(all_solutions, 1):
        if solution.benchmark_result is None:
            print(f"\n[{i}/{len(all_solutions)}] Evaluating {solution.metadata.name}...")
            result = evaluate_solution(solution, benchmark)
            tracker.save_solution(solution)
            print(
                f"  Elo: {result.elo_rating:.0f} | Tier: {result.skill_tier} | bb/100: {result.weighted_bb_per_100:+.2f}"
            )
        else:
            print(f"\n[{i}/{len(all_solutions)}] {solution.metadata.name} (already evaluated)")
            print(f"  Elo: {solution.benchmark_result.elo_rating:.0f}")

    # Generate final report
    print("\n[PHASE 3] Tournament Results")
    print("-" * 70)

    report = benchmark.generate_report(all_solutions, "solutions/tournament_report.txt")
    print(report)

    # Print summary table
    print("\n" + "=" * 70)
    print("                         FINAL STANDINGS")
    print("=" * 70)

    # Sort by Elo
    sorted_solutions = sorted(
        all_solutions,
        key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0,
        reverse=True,
    )

    print(f"\n{'Rank':<6} {'AI Model':<30} {'Elo':<8} {'Tier':<14} {'bb/100':<10}")
    print("-" * 70)

    for rank, sol in enumerate(sorted_solutions, 1):
        if sol.benchmark_result:
            print(
                f"#{rank:<5} {sol.metadata.name:<30} {sol.benchmark_result.elo_rating:<8.0f} "
                f"{sol.benchmark_result.skill_tier:<14} {sol.benchmark_result.weighted_bb_per_100:>+.2f}"
            )

    print("\n" + "=" * 70)
    print(f"Tournament completed at {datetime.now().isoformat()}")
    print(f"Report saved to: solutions/tournament_report.txt")
    print("=" * 70)

    return sorted_solutions


if __name__ == "__main__":
    run_tournament()
