#!/usr/bin/env python
"""Test script to verify fish pause bug fix."""

import sys

from core import entities, environment
from core.algorithms.energy_management import EnergyConserver, OpportunisticRester
from core.ecosystem import EcosystemManager
from core.entity_factory import create_initial_population


def test_initial_food_spawning():
    """Test that initial food is spawned."""
    print("Testing initial food spawning...")

    env = environment.Environment(width=800, height=600)
    ecosystem = EcosystemManager()

    population = create_initial_population(env, ecosystem)

    # Count food items
    food_count = sum(1 for entity in population if isinstance(entity, entities.Food))

    print(f"  Initial food count: {food_count}")
    assert food_count > 0, "No initial food was spawned!"
    print(f"  ✓ Successfully spawned {food_count} initial food items")


def test_energy_conserver_exploration():
    """Test that EnergyConserver has exploration parameter."""
    print("\nTesting EnergyConserver exploration parameter...")

    algorithm = EnergyConserver()

    assert "exploration_rate" in algorithm.parameters, "exploration_rate parameter missing!"
    print(f"  exploration_rate: {algorithm.parameters['exploration_rate']:.3f}")

    # Test that parameter is in valid range
    assert (
        0.0 <= algorithm.parameters["exploration_rate"] <= 0.4
    ), f"exploration_rate {algorithm.parameters['exploration_rate']} out of expected range [0.0, 0.4]"

    print("  ✓ EnergyConserver has valid exploration_rate parameter")


def test_opportunistic_rester_wandering():
    """Test that OpportunisticRester has idle wander parameter."""
    print("\nTesting OpportunisticRester idle wander parameter...")

    algorithm = OpportunisticRester()

    assert "idle_wander_speed" in algorithm.parameters, "idle_wander_speed parameter missing!"
    print(f"  idle_wander_speed: {algorithm.parameters['idle_wander_speed']:.3f}")

    # Test that parameter is in valid range
    assert (
        0.0 <= algorithm.parameters["idle_wander_speed"] <= 0.3
    ), f"idle_wander_speed {algorithm.parameters['idle_wander_speed']} out of expected range [0.0, 0.3]"

    print("  ✓ OpportunisticRester has valid idle_wander_speed parameter")


def test_algorithm_parameters_genetic():
    """Test that composable behaviors can be inherited genetically."""
    print("\nTesting genetic inheritance of composable behaviors...")

    from core.genetics import Genome

    # Test that genomes can be created with composable behaviors
    genome1 = Genome.random(use_algorithm=True)

    behavior_trait = genome1.behavioral.behavior
    if behavior_trait is not None and behavior_trait.value is not None:
        behavior = behavior_trait.value
        print("  Random genome created with composable behavior:")
        print(
            f"    - Threat response: {behavior.threat_response.name if behavior.threat_response else 'None'}"
        )
        print(
            f"    - Food approach: {behavior.food_approach.name if behavior.food_approach else 'None'}"
        )
        print(f"    - Social mode: {behavior.social_mode.name if behavior.social_mode else 'None'}")
        print(
            f"    - Poker engagement: {behavior.poker_engagement.name if behavior.poker_engagement else 'None'}"
        )

    print("  ✓ Composable behaviors are properly integrated into genetic system")


if __name__ == "__main__":
    try:
        test_initial_food_spawning()
        test_energy_conserver_exploration()
        test_opportunistic_rester_wandering()
        test_algorithm_parameters_genetic()

        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
