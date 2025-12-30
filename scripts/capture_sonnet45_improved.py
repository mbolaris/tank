#!/usr/bin/env python3
"""Capture improved Sonnet-4.5 solution with better positional balance.

This script loads a completed simulation and finds the best poker fish
with emphasis on positional balance (not just button-dependent performance).
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


def calculate_positional_balance(fish) -> float:
    """Calculate how balanced a fish's performance is across positions.

    Returns a score from 0-1, where 1 is perfectly balanced.
    """
    if not hasattr(fish, 'poker_stats') or not fish.poker_stats:
        return 0.0

    stats = fish.poker_stats

    # Need both position stats
    if stats.button_games == 0 or stats.non_button_games == 0:
        return 0.0

    button_wr = stats.button_wins / stats.button_games if stats.button_games > 0 else 0
    non_button_wr = stats.non_button_wins / stats.non_button_games if stats.non_button_games > 0 else 0

    # Positional balance: 1.0 = equal win rates, lower = more imbalanced
    # Use harmonic mean to penalize extreme differences
    if button_wr == 0 and non_button_wr == 0:
        return 0.0

    balance = 2 * button_wr * non_button_wr / (button_wr + non_button_wr) if (button_wr + non_button_wr) > 0 else 0

    # Also factor in absolute performance
    avg_wr = (button_wr + non_button_wr) / 2

    # Combined score: balance * performance
    return balance * avg_wr


def score_poker_fish(fish) -> dict:
    """Score a fish for tournament quality."""
    if not hasattr(fish, 'poker_stats') or not fish.poker_stats:
        return {'score': 0.0, 'reason': 'no poker stats'}

    stats = fish.poker_stats

    if stats.total_games < 50:
        return {'score': 0.0, 'reason': 'too few games'}

    # Calculate components
    win_rate = stats.wins / stats.total_games if stats.total_games > 0 else 0
    positional_balance = calculate_positional_balance(fish)
    experience = min(stats.total_games / 500.0, 1.0)  # Cap at 500 games

    # ROI is a good indicator of profitability
    roi = stats.roi if hasattr(stats, 'roi') else 1.0
    roi_score = min(roi / 10.0, 1.0) if roi > 0 else 0

    # Composite score
    # Heavily weight positional balance to fix our weakness
    score = (
        win_rate * 0.3 +           # 30% win rate
        positional_balance * 0.5 + # 50% positional balance (HIGH)
        experience * 0.1 +         # 10% experience
        roi_score * 0.1            # 10% ROI
    )

    return {
        'score': score,
        'win_rate': win_rate,
        'positional_balance': positional_balance,
        'experience': experience,
        'games': stats.total_games,
        'button_games': stats.button_games,
        'non_button_games': stats.non_button_games,
        'roi': roi
    }


def load_simulation(seed: int):
    """Load a completed simulation."""
    logger.info(f"Loading simulation with seed {seed}...")

    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    return world


def capture_best_balanced_fish(world, seed: int):
    """Capture the fish with best tournament potential (balanced performance)."""
    from core.entities import Fish

    tracker = SolutionTracker()

    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    logger.info(f"Found {len(fish_list)} fish in simulation")

    # Score all fish
    scored_fish = []
    for fish in fish_list:
        score_info = score_poker_fish(fish)
        if score_info['score'] > 0:
            scored_fish.append((fish, score_info))

    logger.info(f"Found {len(scored_fish)} fish with poker experience")

    if not scored_fish:
        logger.error("No suitable fish found!")
        return None

    # Sort by composite score
    scored_fish.sort(key=lambda x: x[1]['score'], reverse=True)

    # Show top 5
    logger.info("\nTop 5 candidates:")
    for i, (fish, score_info) in enumerate(scored_fish[:5]):
        logger.info(f"  #{i+1} Fish {fish.fish_id}:")
        logger.info(f"    Score: {score_info['score']:.3f}")
        logger.info(f"    Win Rate: {score_info['win_rate']:.1%}")
        logger.info(f"    Positional Balance: {score_info['positional_balance']:.3f}")
        logger.info(f"    Games: {score_info['games']} (btn:{score_info['button_games']}, non:{score_info['non_button_games']})")
        logger.info(f"    ROI: {score_info['roi']:.2f}")

    best_fish, best_score = scored_fish[0]

    logger.info(f"\n✓ Selected Fish #{best_fish.fish_id}")

    # Capture the solution
    solution = tracker.capture_solution(
        best_fish,
        name="Sonnet-4.5 Balanced Champion",
        description=f"Sonnet-4.5 improved poker strategy with positional balance - {best_score['games']} games, seed {seed}",
        author="claude-sonnet-4-5-20250929",
    )

    return solution


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Capture improved Sonnet-4.5 solution')
    parser.add_argument('--seed', type=int, default=12345, help='Simulation seed')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("CAPTURING IMPROVED SONNET-4.5 SOLUTION")
    logger.info("=" * 60)

    # Load simulation
    world = load_simulation(args.seed)

    # Capture best balanced solution
    solution = capture_best_balanced_fish(world, args.seed)

    if solution is None:
        logger.error("Failed to capture solution!")
        return

    logger.info(f"\nCaptured solution: {solution.metadata.name}")
    logger.info(f"  ID: {solution.metadata.solution_id}")

    # Save solution
    tracker = SolutionTracker()
    filepath = tracker.save_solution(solution)
    logger.info(f"Solution saved to: {filepath}")

    # Print summary
    print("\n" + "=" * 60)
    print("IMPROVED SONNET-4.5 SOLUTION CAPTURED")
    print("=" * 60)
    print(f"Solution ID: {solution.metadata.solution_id}")
    print(f"Seed: {args.seed}")
    print(f"Filepath: {filepath}")
    print("=" * 60)

    return solution


if __name__ == "__main__":
    solution = main()
