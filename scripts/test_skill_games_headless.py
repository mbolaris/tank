#!/usr/bin/env python
"""Test script to run headless simulations with different skill games.

This script runs the simulation for each available skill game and reports
metrics about how the fish population is learning/evolving.

Usage:
    python scripts/test_skill_games_headless.py
"""

import logging
import os
import sys
import time
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.skill_game_system import SkillGameSystem
from core.skills.base import SkillGameType
from core.skills.config import SkillGameConfig, get_active_skill_game, set_skill_game_config
from core.worlds import WorldRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def run_skill_game_simulation(
    game_type: SkillGameType,
    max_frames: int = 3000,
    seed: int = 42,
    encounter_rate: float = 0.15,
) -> Dict[str, Any]:
    """Run a headless simulation with a specific skill game.

    Args:
        game_type: Which skill game to use
        max_frames: Number of frames to simulate
        seed: Random seed for reproducibility
        encounter_rate: How often skill games trigger

    Returns:
        Dictionary of results/metrics
    """
    logger.info("=" * 60)
    logger.info(f"Running simulation with: {game_type.value}")
    logger.info("=" * 60)

    # Configure the skill game
    config = SkillGameConfig(
        active_game=game_type,
        encounter_rate=encounter_rate,
        min_energy_to_play=15.0,
        stake_multiplier=1.0,
    )
    set_skill_game_config(config)

    # Get the active game for info
    active_game = get_active_skill_game()
    if active_game:
        logger.info(f"Game: {active_game.name}")
        logger.info(f"Description: {active_game.description}")
        logger.info(f"Optimal strategy: {active_game.optimal_strategy_description}")
    logger.info("")

    # Create tank world
    world = WorldRegistry.create_world("tank", seed=seed, headless=True)
    world.reset(seed=seed)

    engine = world.engine

    # Create skill game system
    skill_system = SkillGameSystem(engine, config=config)
    engine.skill_game_system = skill_system  # Attach for stats export

    # Run simulation
    start_time = time.time()
    stats_interval = max_frames // 5  # Print 5 times during run

    total_skill_games = 0
    total_energy_transferred = 0.0

    for frame in range(max_frames):
        # Update simulation
        engine.update()

        # Run skill game encounters
        fish_list = engine.get_fish_list()
        events = skill_system.check_and_run_encounters(
            fish_list,
            current_frame=frame,
            encounter_distance=60.0,
        )

        total_skill_games += len(events)
        for event in events:
            total_energy_transferred += event.energy_transferred

        # Print progress
        if (frame + 1) % stats_interval == 0:
            fish_count = len(fish_list)
            logger.info(
                f"  Frame {frame + 1}/{max_frames}: "
                f"{fish_count} fish, {total_skill_games} games played"
            )

    elapsed = time.time() - start_time

    # Collect final statistics
    fish_list = engine.get_fish_list()

    # Analyze skill game performance across population
    optimality_rates = []
    win_rates = []
    games_per_fish = []

    for fish in fish_list:
        if hasattr(fish, "_skill_game_component"):
            stats = fish._skill_game_component.get_stats(game_type)
            if stats.total_games > 0:
                optimality_rates.append(stats.get_optimality_rate())
                win_rates.append(stats.get_win_rate())
                games_per_fish.append(stats.total_games)

    # Calculate aggregate metrics
    results = {
        "game_type": game_type.value,
        "frames_run": max_frames,
        "elapsed_seconds": elapsed,
        "final_population": len(fish_list),
        "total_skill_games": total_skill_games,
        "total_energy_transferred": total_energy_transferred,
        "fish_with_game_stats": len(optimality_rates),
        "avg_optimality_rate": (
            sum(optimality_rates) / len(optimality_rates) if optimality_rates else 0.0
        ),
        "avg_win_rate": sum(win_rates) / len(win_rates) if win_rates else 0.0,
        "avg_games_per_fish": sum(games_per_fish) / len(games_per_fish) if games_per_fish else 0.0,
        "max_games_by_fish": max(games_per_fish) if games_per_fish else 0,
    }

    # Get recent events for sample output
    recent_events = skill_system.get_recent_events(5)

    logger.info("")
    logger.info("Results:")
    logger.info(f"  Elapsed time: {elapsed:.2f}s ({max_frames/elapsed:.0f} fps)")
    logger.info(f"  Final population: {results['final_population']} fish")
    logger.info(f"  Total skill games: {results['total_skill_games']}")
    logger.info(f"  Total energy transferred: {results['total_energy_transferred']:.1f}")
    logger.info(f"  Fish with game stats: {results['fish_with_game_stats']}")
    logger.info(f"  Avg optimality rate: {results['avg_optimality_rate']:.1%}")
    logger.info(f"  Avg win rate: {results['avg_win_rate']:.1%}")
    logger.info(f"  Avg games per fish: {results['avg_games_per_fish']:.1f}")
    logger.info("")

    if recent_events:
        logger.info("Sample recent events:")
        for event_data in recent_events[:3]:
            logger.info(
                f"  Frame {event_data['frame']}: Player #{event_data['player1_id']} vs #{event_data['player2_id']} "
                f"- Winner: #{event_data['winner_id']}, Energy: {event_data['energy_transferred']:.1f}"
            )

    return results


def main():
    """Run simulations with each skill game type."""
    logger.info("=" * 60)
    logger.info("SKILL GAME FRAMEWORK TEST")
    logger.info("Testing evolution with different toy problems")
    logger.info("=" * 60)
    logger.info("")

    results = {}

    # Test each skill game
    skill_games = [
        SkillGameType.ROCK_PAPER_SCISSORS,
        SkillGameType.NUMBER_GUESSING,
    ]

    for game_type in skill_games:
        try:
            result = run_skill_game_simulation(
                game_type=game_type,
                max_frames=3000,  # About 100 seconds of sim time at 30fps
                seed=42,
                encounter_rate=0.15,
            )
            results[game_type.value] = result
        except Exception as e:
            logger.error(f"Error running {game_type.value}: {e}")
            import traceback

            traceback.print_exc()
            results[game_type.value] = {"error": str(e)}

        logger.info("")

    # Print summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info("")

    for game_type_name, result in results.items():
        if "error" in result:
            logger.info(f"{game_type_name}: ERROR - {result['error']}")
        else:
            logger.info(
                f"{game_type_name}: "
                f"{result['total_skill_games']} games, "
                f"{result['avg_optimality_rate']:.1%} avg optimality, "
                f"{result['final_population']} fish"
            )

    logger.info("")
    logger.info("Interpretation:")
    logger.info("- Higher optimality rate = fish playing closer to Nash equilibrium (RPS)")
    logger.info("- Higher optimality rate = fish predicting patterns better (Number Prediction)")
    logger.info("- Over generations, optimality should increase as better strategies survive")


if __name__ == "__main__":
    main()
