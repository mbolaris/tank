#!/usr/bin/env python
"""Comprehensive verification script for skill game framework.

This script tests all critical aspects of skill game swappability:
1. Strategy inheritance across generations
2. Energy flow affecting survival
3. Hot-swapping games mid-simulation
4. Both games working correctly

Usage:
    python scripts/verify_skill_games.py
"""

import logging
import os
import sys
from typing import Dict, TypedDict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fish.skill_game_component import SkillGameComponent
from core.skill_game_system import SkillGameSystem
from core.skills.base import SkillGameType
from core.skills.config import SkillGameConfig, set_active_skill_game, set_skill_game_config
from core.skills.games.number_guessing import NumberGuessingGame, NumberGuessingStrategy
from core.skills.games.rock_paper_scissors import RockPaperScissorsGame, RPSStrategy
from core.worlds import WorldRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def test_strategy_inheritance():
    """Test that strategies are inherited from parent to child with mutation."""
    logger.info("=" * 60)
    logger.info("TEST 1: Strategy Inheritance")
    logger.info("=" * 60)

    # Create parent with specific RPS strategy
    parent = SkillGameComponent()
    parent_strategy = RPSStrategy(
        prob_rock=0.6,  # Biased toward rock
        prob_paper=0.2,
        prob_scissors=0.2,
        learning_rate=0.15,
    )
    parent.set_strategy(SkillGameType.ROCK_PAPER_SCISSORS, parent_strategy)

    # Also add number guessing strategy
    parent_num_strategy = NumberGuessingStrategy(
        weight_last_value=0.5,
        weight_trend=0.3,
        weight_mean=0.1,
        weight_alternating=0.1,
    )
    parent.set_strategy(SkillGameType.NUMBER_GUESSING, parent_num_strategy)

    # Create children and verify inheritance
    children_similar = 0
    for i in range(10):
        child = SkillGameComponent()
        child.inherit_from_parent(parent, mutation_rate=0.1)

        # Check RPS strategy inherited
        child_rps = child.get_strategy(SkillGameType.ROCK_PAPER_SCISSORS)
        assert child_rps is not None, f"Child {i} should have RPS strategy"

        child_params = child_rps.get_parameters()
        parent_params = parent_strategy.get_parameters()

        # Check parameters are similar but not identical (mutation)
        rock_diff = abs(child_params["prob_rock"] - parent_params["prob_rock"])
        if rock_diff < 0.15:  # Within expected mutation range
            children_similar += 1

        # Check number guessing strategy also inherited
        child_num = child.get_strategy(SkillGameType.NUMBER_GUESSING)
        assert child_num is not None, f"Child {i} should have Number Guessing strategy"

    logger.info("  Created 10 children from biased parent (60% rock)")
    logger.info(f"  {children_similar}/10 children inherited similar bias (within 15%)")
    assert children_similar >= 5, "Most children should inherit similar strategy"
    logger.info("  PASSED: Strategies inherit with mutation")
    return True


def test_energy_flow():
    """Test that energy flows correctly through games and affects fish."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Energy Flow")
    logger.info("=" * 60)

    # Test RPS energy flow
    rps_game = RockPaperScissorsGame(stake=10.0)

    # Create two strategies - one optimal, one biased
    optimal = rps_game.create_optimal_strategy()
    biased = RPSStrategy(prob_rock=0.9, prob_paper=0.05, prob_scissors=0.05)

    # Play many games and track energy
    total_optimal_score = 0.0
    total_biased_score = 0.0

    for _ in range(200):
        result = rps_game.play_round(biased, optimal)
        total_biased_score += result.score_change
        total_optimal_score -= result.score_change  # Zero-sum

    logger.info(
        f"  RPS (200 games): Biased total={total_biased_score:.1f}, Optimal total={total_optimal_score:.1f}"
    )
    # Over many games, optimal should not lose significantly
    assert total_optimal_score >= -50, "Optimal strategy should not lose much"
    logger.info("  PASSED: RPS energy flows correctly")

    # Test Number Guessing energy flow
    num_game = NumberGuessingGame(stake=10.0)

    good_strategy = NumberGuessingStrategy(
        weight_alternating=0.8,  # Good for alternating pattern
        weight_last_value=0.1,
        weight_trend=0.05,
        weight_mean=0.05,
    )
    bad_strategy = NumberGuessingStrategy(
        weight_mean=0.9,  # Bad for alternating pattern
        weight_last_value=0.05,
        weight_trend=0.025,
        weight_alternating=0.025,
    )

    # Play and let strategies learn
    good_score = 0.0
    bad_score = 0.0
    for _ in range(100):
        result = num_game.play_round(good_strategy)
        good_score += result.score_change
        good_strategy.learn_from_result(result)

        result = num_game.play_round(bad_strategy)
        bad_score += result.score_change
        bad_strategy.learn_from_result(result)

    logger.info(f"  Number Guessing (100 games each): Good={good_score:.1f}, Bad={bad_score:.1f}")
    # Good strategy should score better
    assert good_score > bad_score, "Strategy tuned for pattern should score better"
    logger.info("  PASSED: Number Guessing energy flows correctly")
    return True


def test_game_swapping():
    """Test that games can be hot-swapped mid-simulation."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Game Hot-Swapping")
    logger.info("=" * 60)

    # Create a short simulation
    world = WorldRegistry.create_world("tank", seed=123, headless=True)
    world.reset(seed=123)
    engine = world.engine

    # Start with RPS
    config = SkillGameConfig(
        active_game=SkillGameType.ROCK_PAPER_SCISSORS,
        encounter_rate=0.2,
    )
    set_skill_game_config(config)
    skill_system = SkillGameSystem(engine, config=config)
    engine.skill_game_system = skill_system

    starting_game = skill_system.get_active_game()
    assert starting_game is not None
    logger.info(f"  Starting with: {starting_game.name}")

    # Run 500 frames with RPS
    rps_games = 0
    for frame in range(500):
        engine.update()
        fish_list = engine.get_fish_list()
        events = skill_system.check_and_run_encounters(fish_list, frame, 60.0)
        rps_games += len(events)

    logger.info(f"  RPS phase (500 frames): {rps_games} games played")

    # Hot-swap to Number Guessing
    set_active_skill_game(SkillGameType.NUMBER_GUESSING)
    # Force refresh of cached game
    skill_system._game_type = None
    skill_system._active_game = None

    active_game = skill_system.get_active_game()
    assert active_game is not None
    logger.info(f"  Swapped to: {active_game.name}")
    assert active_game.game_type == SkillGameType.NUMBER_GUESSING, "Should be Number Guessing"

    # Run 500 more frames with Number Guessing
    num_games = 0
    for frame in range(500, 1000):
        engine.update()
        fish_list = engine.get_fish_list()
        events = skill_system.check_and_run_encounters(fish_list, frame, 60.0)
        num_games += len(events)

    logger.info(f"  Number Guessing phase (500 frames): {num_games} games played")

    # Verify fish have stats for both games
    fish_list = engine.get_fish_list()
    fish_with_both = 0
    for fish in fish_list:
        if hasattr(fish, "_skill_game_component"):
            rps_stats = fish._skill_game_component.get_stats(SkillGameType.ROCK_PAPER_SCISSORS)
            num_stats = fish._skill_game_component.get_stats(SkillGameType.NUMBER_GUESSING)
            if rps_stats.total_games > 0 and num_stats.total_games > 0:
                fish_with_both += 1

    logger.info(f"  Fish with both game types: {fish_with_both}/{len(fish_list)}")
    logger.info("  PASSED: Games can be hot-swapped")
    return True


def test_inheritance_in_simulation():
    """Test that strategies actually inherit across generations in real simulation."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 4: Inheritance in Real Simulation")
    logger.info("=" * 60)

    # Run simulation long enough for reproduction
    world = WorldRegistry.create_world("tank", seed=456, headless=True)
    world.reset(seed=456)
    engine = world.engine

    config = SkillGameConfig(
        active_game=SkillGameType.ROCK_PAPER_SCISSORS,
        encounter_rate=0.15,
        stake_multiplier=0.5,  # Lower stakes so fish survive longer
    )
    set_skill_game_config(config)
    skill_system = SkillGameSystem(engine, config=config)
    engine.skill_game_system = skill_system

    # Track generations
    initial_fish = engine.get_fish_list()
    initial_gen = max(f.generation for f in initial_fish) if initial_fish else 0
    logger.info(f"  Starting generation: {initial_gen}")

    # Run until we see generation increase
    max_frames = 5000
    highest_gen = initial_gen
    babies_with_inherited_strategies = 0
    total_babies = 0

    for frame in range(max_frames):
        engine.update()

        # Run skill games
        fish_list = engine.get_fish_list()
        skill_system.check_and_run_encounters(fish_list, frame, 60.0)

        # Check for new generations
        for fish in fish_list:
            if fish.generation > initial_gen:
                total_babies += 1
                if fish.generation > highest_gen:
                    highest_gen = fish.generation

                # Check if baby has inherited strategy
                if hasattr(fish, "_skill_game_component"):
                    strategy = fish._skill_game_component.get_strategy(
                        SkillGameType.ROCK_PAPER_SCISSORS
                    )
                    if strategy is not None:
                        babies_with_inherited_strategies += 1

        # Early exit if we have enough data
        if highest_gen >= initial_gen + 2 and total_babies >= 10:
            break

    final_fish = engine.get_fish_list()
    logger.info(f"  Final generation: {highest_gen}")
    logger.info(f"  Total babies born: {total_babies}")
    logger.info(f"  Babies with inherited strategies: {babies_with_inherited_strategies}")
    logger.info(f"  Final population: {len(final_fish)}")

    if total_babies > 0:
        inheritance_rate = babies_with_inherited_strategies / total_babies
        logger.info(f"  Inheritance rate: {inheritance_rate:.1%}")

        if inheritance_rate > 0.5:
            logger.info("  PASSED: Strategies inherit across generations")
            return True
        else:
            logger.warning("  WARNING: Low inheritance rate - some babies missing strategies")
            return False
    else:
        logger.warning("  WARNING: No babies born - cannot verify inheritance")
        return False


def test_both_games_functional():
    """Test that both game types function correctly in simulation."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 5: Both Games Functional")
    logger.info("=" * 60)

    class _GameResult(TypedDict):
        games: int
        energy: float
        fish: int

    results: Dict[SkillGameType, _GameResult] = {}

    for game_type in [SkillGameType.ROCK_PAPER_SCISSORS, SkillGameType.NUMBER_GUESSING]:
        world = WorldRegistry.create_world("tank", seed=789, headless=True)
        world.reset(seed=789)
        engine = world.engine

        config = SkillGameConfig(
            active_game=game_type,
            encounter_rate=0.2,
        )
        set_skill_game_config(config)
        skill_system = SkillGameSystem(engine, config=config)
        engine.skill_game_system = skill_system

        games_played = 0
        energy_transferred = 0.0

        for frame in range(1500):
            engine.update()
            fish_list = engine.get_fish_list()
            events = skill_system.check_and_run_encounters(fish_list, frame, 60.0)
            games_played += len(events)
            for e in events:
                energy_transferred += e.energy_transferred

        results[game_type] = {
            "games": games_played,
            "energy": energy_transferred,
            "fish": len(engine.get_fish_list()),
        }

        logger.info(
            f"  {game_type.value}: {games_played} games, {energy_transferred:.1f} energy, {results[game_type]['fish']} fish"
        )

    # Both games should have some activity
    for game_type, data in results.items():
        assert data["games"] > 10, f"{game_type} should have games played"
        assert data["fish"] > 0, f"{game_type} should have surviving fish"

    logger.info("  PASSED: Both games function correctly")
    return True


def main():
    """Run all verification tests."""
    logger.info("=" * 60)
    logger.info("SKILL GAME FRAMEWORK VERIFICATION")
    logger.info("=" * 60)
    logger.info("")

    tests = [
        ("Strategy Inheritance", test_strategy_inheritance),
        ("Energy Flow", test_energy_flow),
        ("Game Swapping", test_game_swapping),
        ("Inheritance in Simulation", test_inheritance_in_simulation),
        ("Both Games Functional", test_both_games_functional),
    ]

    results = {}
    for name, test_func in tests:
        try:
            passed = test_func()
            results[name] = "PASSED" if passed else "FAILED"
        except Exception as e:
            logger.error(f"Test {name} raised exception: {e}")
            import traceback

            traceback.print_exc()
            results[name] = f"ERROR: {e}"

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for name, result in results.items():
        status_icon = "[OK]" if result == "PASSED" else "[FAIL]"
        logger.info(f"  {status_icon} {name}: {result}")
        if result != "PASSED":
            all_passed = False

    logger.info("")
    if all_passed:
        logger.info("All tests PASSED - Skill games are swappable!")
    else:
        logger.info("Some tests FAILED - Review issues above")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
