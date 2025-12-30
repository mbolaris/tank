#!/usr/bin/env python3
"""Evolve and capture improved Sonnet-4.5 solution with better positional balance."""

import json
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tank_world import TankWorld, TankWorldConfig
from core.solutions import SolutionTracker
from core.entities import Fish

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_positional_balance(fish) -> float:
    """Calculate how balanced a fish's performance is across positions."""
    if not hasattr(fish, 'poker_stats') or not fish.poker_stats:
        return 0.0

    stats = fish.poker_stats
    if stats.games_on_button == 0 or stats.games_non_button == 0:
        return 0.0

    button_wr = stats.wins_on_button / stats.games_on_button
    non_button_wr = stats.wins_non_button / stats.games_non_button

    if button_wr == 0 and non_button_wr == 0:
        return 0.0

    # Harmonic mean to penalize extreme differences
    balance = 2 * button_wr * non_button_wr / (button_wr + non_button_wr) if (button_wr + non_button_wr) > 0 else 0
    avg_wr = (button_wr + non_button_wr) / 2

    return balance * avg_wr


def score_poker_fish(fish) -> dict:
    """Score a fish for tournament quality."""
    if not hasattr(fish, 'poker_stats') or not fish.poker_stats:
        return {'score': 0.0}

    stats = fish.poker_stats
    if stats.total_games < 100:  # Need at least 100 games
        return {'score': 0.0}

    win_rate = stats.wins / stats.total_games
    positional_balance = calculate_positional_balance(fish)
    experience = min(stats.total_games / 500.0, 1.0)
    roi = stats.get_roi()
    roi_score = min(roi / 10.0, 1.0) if roi > 0 else 0

    # 50% weight on positional balance to fix weakness
    score = (win_rate * 0.3 + positional_balance * 0.5 +
             experience * 0.1 + roi_score * 0.1)

    return {
        'score': score,
        'win_rate': win_rate,
        'positional_balance': positional_balance,
        'games': stats.total_games,
        'button_games': stats.games_on_button,
        'non_button_games': stats.games_non_button,
        'button_wr': stats.wins_on_button / stats.games_on_button if stats.games_on_button > 0 else 0,
        'non_button_wr': stats.wins_non_button / stats.games_non_button if stats.games_non_button > 0 else 0,
        'roi': roi
    }


def run_and_capture(seed: int, max_frames: int = 150000):
    """Run simulation and capture the best balanced fish."""
    logger.info(f"Starting simulation with seed {seed}, max_frames {max_frames}")

    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    logger.info(f"World initialized with {len(world.entities_list)} entities")

    # Run simulation
    stats_interval = 5000
    for frame in range(max_frames):
        world.update()

        if frame > 0 and frame % stats_interval == 0:
            fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
            poker_games = sum(f.poker_stats.total_games for f in fish_list
                            if hasattr(f, 'poker_stats') and f.poker_stats)

            logger.info(f"Frame {frame:6d}: {len(fish_list)} fish, {poker_games} total poker games")

            # Check if we have enough quality poker fish
            scored = [score_poker_fish(f) for f in fish_list]
            qualified = [s for s in scored if s['score'] > 0]

            if len(qualified) >= 3:
                logger.info(f"  → {len(qualified)} qualified fish found!")

    logger.info("Simulation complete. Finding best fish...")

    # Score all fish
    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    scored_fish = []
    for fish in fish_list:
        score_info = score_poker_fish(fish)
        if score_info['score'] > 0:
            scored_fish.append((fish, score_info))

    logger.info(f"Found {len(scored_fish)} qualified fish")

    if not scored_fish:
        logger.error("No qualified fish found!")
        return None

    scored_fish.sort(key=lambda x: x[1]['score'], reverse=True)

    # Show top 5
    logger.info("\n" + "=" * 60)
    logger.info("TOP 5 CANDIDATES")
    logger.info("=" * 60)
    for i, (fish, info) in enumerate(scored_fish[:5]):
        logger.info(f"#{i+1} Fish {fish.fish_id}:")
        logger.info(f"  Score: {info['score']:.3f}")
        logger.info(f"  Win Rate: {info['win_rate']:.1%}")
        logger.info(f"  Positional Balance: {info['positional_balance']:.3f}")
        logger.info(f"  Button WR: {info['button_wr']:.1%} ({info['button_games']} games)")
        logger.info(f"  Non-Button WR: {info['non_button_wr']:.1%} ({info['non_button_games']} games)")
        logger.info(f"  Total Games: {info['games']}")
        logger.info(f"  ROI: {info['roi']:.2f}")
        logger.info("")

    best_fish, best_info = scored_fish[0]
    logger.info(f"✓ SELECTED: Fish #{best_fish.fish_id}")

    # Capture solution
    tracker = SolutionTracker()
    solution = tracker.capture_solution(
        best_fish,
        name="Sonnet-4.5 Balanced Champion",
        description=f"Improved Sonnet-4.5 with positional balance - {best_info['games']} games, seed {seed}, {max_frames} frames",
        author="claude-sonnet-4-5-20250929",
    )

    # Save
    filepath = tracker.save_solution(solution)

    logger.info("\n" + "=" * 60)
    logger.info("SOLUTION CAPTURED")
    logger.info("=" * 60)
    logger.info(f"Solution ID: {solution.metadata.solution_id}")
    logger.info(f"Filepath: {filepath}")
    logger.info(f"Seed: {seed}")
    logger.info(f"Frames: {max_frames}")
    logger.info("=" * 60)

    return solution


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=12345)
    parser.add_argument('--frames', type=int, default=150000)
    args = parser.parse_args()

    solution = run_and_capture(args.seed, args.frames)
    return solution


if __name__ == "__main__":
    main()
