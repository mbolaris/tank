#!/usr/bin/env python3
"""
Evaluate newly captured solution and compare with Sonnet-4.5 benchmark.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.solutions import SolutionBenchmark, SolutionRecord


def find_latest_solution():
    """Find the most recently created solution file."""
    solutions_dir = Path("solutions")
    solution_files = sorted(
        [f for f in solutions_dir.glob("*_*.json") if f.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not solution_files:
        return None

    return solution_files[0]


def evaluate_solution(solution_path):
    """Evaluate a solution and print detailed report."""
    print(f"\n{'='*70}")
    print("EVALUATING SOLUTION")
    print(f"{'='*70}")
    print(f"Solution: {solution_path.name}\n")

    # Load solution
    solution = SolutionRecord.load(str(solution_path))

    print("Metadata:")
    print(f"  ID: {solution.metadata.solution_id}")
    print(f"  Author: {solution.metadata.author}")
    print(f"  Name: {solution.metadata.name}")
    print(f"  Description: {solution.metadata.description}")

    # Show capture stats
    if solution.capture_stats:
        stats = solution.capture_stats
        print("\nCapture Stats:")
        print(f"  Total Games: {stats.total_games}")
        print(f"  Win Rate: {stats.win_rate:.1%}")
        print(f"  Button WR: {stats.button_win_rate:.1%} ({stats.games_on_button} games)")
        print(f"  Non-Button WR: {stats.non_button_win_rate:.1%} ({stats.games_non_button} games)")
        print(f"  Positional Balance: {stats.positional_advantage:.3f}")
        print(f"  ROI: {stats.roi:.2f}")
        print(f"  Best Streak: {stats.best_streak}")
        print(f"  Skill Trend: {stats.skill_trend}")

    # Evaluate against benchmark
    print(f"\n{'─'*70}")
    print("Running Benchmark Evaluation...")
    print(f"{'─'*70}\n")

    benchmark = SolutionBenchmark()
    result = benchmark.evaluate_solution(solution, verbose=True)

    solution.benchmark_result = result

    print(f"\n{'='*70}")
    print("BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"Elo Rating: {result.elo_rating:.0f}")
    print(f"Skill Tier: {result.skill_tier}")
    print(f"bb/100: {result.weighted_bb_per_100:+.2f}")
    print(f"Total Hands: {result.total_hands_played}")

    print("\nPer-Opponent Performance:")
    for opponent, bb100 in sorted(result.per_opponent.items(), key=lambda x: x[1], reverse=True):
        print(f"  {opponent:20s}: {bb100:+8.2f} bb/100")

    # Save updated solution with benchmark results
    output_path = solution_path
    with open(output_path, "w") as f:
        json.dump(solution.to_dict(), f, indent=2)

    print(f"\n{'='*70}")
    print(f"✓ Solution updated and saved to: {output_path}")
    print(f"{'='*70}\n")

    # Comparison with Sonnet-4.5
    print("\nComparison with Sonnet-4.5 (fec218b7_20251230_180755):")
    print(f"{'─'*70}")
    print("Metric                           Haiku-4.5      Sonnet-4.5")
    print(f"{'─'*70}")
    print(f"Button WR                        {stats.button_win_rate:>7.1%}         35.3%")
    print(f"Non-Button WR                    {stats.non_button_win_rate:>7.1%}         35.1%")
    print(f"Positional Balance               {stats.positional_advantage:>7.3f}         0.124")
    print(f"Elo Rating                       {result.elo_rating:>7.0f}       1534.6")
    print(f"bb/100                           {result.weighted_bb_per_100:>7.2f}       758.78")
    print(f"{'─'*70}")

    return solution


if __name__ == "__main__":
    latest = find_latest_solution()
    if latest:
        evaluate_solution(latest)
    else:
        print("No solution files found!")
        sys.exit(1)
