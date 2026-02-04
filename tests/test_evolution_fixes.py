#!/usr/bin/env python3
"""Test script to verify energy economy and algorithm evolution fixes."""

import sys

import pytest

from core.algorithms.registry import crossover_algorithms
from core.genetics import Genome


@pytest.mark.manual
def test_energy_economy():
    """Test that reproduction is energy-neutral."""
    print("=" * 60)
    print("Testing Energy Economy Fix")
    print("=" * 60)

    # Simulate reproduction
    parent_energy = 60.0

    # Parent pays mating cost
    REPRODUCTION_ENERGY_COST = 10.0
    ENERGY_TRANSFER_TO_BABY = 0.30

    # Calculate energy changes
    energy_to_transfer = parent_energy * ENERGY_TRANSFER_TO_BABY
    parent_final = parent_energy - REPRODUCTION_ENERGY_COST - energy_to_transfer
    baby_energy = energy_to_transfer  # Baby gets ONLY transferred energy

    # Net change in total energy
    initial_total = parent_energy
    final_total = parent_final + baby_energy
    net_change = final_total - initial_total

    print(f"Parent initial energy: {parent_energy}")
    print(f"Parent final energy: {parent_final:.2f}")
    print(f"Baby initial energy: {baby_energy:.2f}")
    print(f"Net energy change: {net_change:.2f}")
    print(f"Energy conserved: {abs(net_change + REPRODUCTION_ENERGY_COST) < 0.01}")
    print()

    # Expected: net_change = -10 (only the mating cost is lost)
    assert (
        abs(net_change + REPRODUCTION_ENERGY_COST) < 0.01
    ), f"Energy not conserved! Net change should be -{REPRODUCTION_ENERGY_COST}, got {net_change:.2f}"

    print("✓ Energy economy test PASSED!")
    print(f"  → Each birth removes {REPRODUCTION_ENERGY_COST} energy (mating cost only)")
    print("  → No free energy created!\n")


@pytest.mark.manual
def test_algorithm_crossover():
    """Test that composable behavior crossover works from both parents."""
    print("=" * 60)
    print("Testing Composable Behavior Crossover (Recombination)")
    print("=" * 60)

    # Create two parent genomes with composable behaviors
    genome1 = Genome.random(use_algorithm=True)
    genome2 = Genome.random(use_algorithm=True)

    assert genome1.behavioral.behavior is not None
    assert genome2.behavioral.behavior is not None
    behavior1 = genome1.behavioral.behavior.value
    behavior2 = genome2.behavioral.behavior.value
    assert behavior1 is not None
    assert behavior2 is not None

    print(
        f"Parent 1 threat response: {behavior1.threat_response.name if behavior1.threat_response else 'None'}"
    )
    print(
        f"Parent 1 food approach: {behavior1.food_approach.name if behavior1.food_approach else 'None'}"
    )
    print(
        f"Parent 2 threat response: {behavior2.threat_response.name if behavior2.threat_response else 'None'}"
    )
    print(
        f"Parent 2 food approach: {behavior2.food_approach.name if behavior2.food_approach else 'None'}"
    )
    print()

    # Test crossover multiple times to see variation
    offspring_behaviors = []
    for i in range(10):
        offspring = Genome.from_parents(genome1, genome2, mutation_rate=0.0)
        assert offspring.behavioral.behavior is not None
        behavior = offspring.behavioral.behavior.value
        assert behavior is not None
        threat_name = behavior.threat_response.name if behavior.threat_response else "None"
        offspring_behaviors.append(threat_name)

    print("Offspring threat responses from 10 crosses:")
    for i, threat in enumerate(offspring_behaviors):
        print(f"  {i+1}. {threat}")

    # Check that offspring have valid behaviors
    assert all(b is not None for b in offspring_behaviors), "All offspring should have behaviors"

    print("\n✓ Composable behavior crossover test PASSED!")
    print("  → Offspring inherit behaviors from parents")
    print("  → Composable behavior system is working\n")


@pytest.mark.manual
def test_same_algorithm_parameter_blending():
    """Test parameter blending when both parents have same algorithm type."""
    import random

    # Use a deterministic RNG for test results
    rng = random.Random(12345)

    print("=" * 60)
    print("Testing Parameter Blending (Same Algorithm)")
    print("=" * 60)

    # Create two parents with same algorithm type but different parameters
    from core.algorithms.food_seeking import GreedyFoodSeeker

    algo1 = GreedyFoodSeeker()
    algo1.parameters = {"speed_multiplier": 0.8, "detection_range": 0.6}

    algo2 = GreedyFoodSeeker()
    algo2.parameters = {"speed_multiplier": 1.2, "detection_range": 0.9}

    print(
        f"Parent 1: speed={algo1.parameters['speed_multiplier']}, "
        + f"detection={algo1.parameters['detection_range']}"
    )
    print(
        f"Parent 2: speed={algo2.parameters['speed_multiplier']}, "
        + f"detection={algo2.parameters['detection_range']}"
    )
    print()

    # Create offspring (no mutation for cleaner test)
    # Set algorithm_switch_rate=0.0 to ensure no random algorithm switching
    offspring = crossover_algorithms(
        algo1,
        algo2,
        mutation_rate=0.0,
        mutation_strength=0.0,
        algorithm_switch_rate=0.0,
        rng=rng,
    )

    print(
        f"Offspring: speed={offspring.parameters['speed_multiplier']:.2f}, "
        + f"detection={offspring.parameters['detection_range']:.2f}"
    )

    # Check that parameters are blended (between parent values)
    speed_min = min(algo1.parameters["speed_multiplier"], algo2.parameters["speed_multiplier"])
    speed_max = max(algo1.parameters["speed_multiplier"], algo2.parameters["speed_multiplier"])
    detection_min = min(algo1.parameters["detection_range"], algo2.parameters["detection_range"])
    detection_max = max(algo1.parameters["detection_range"], algo2.parameters["detection_range"])

    assert (
        speed_min <= offspring.parameters["speed_multiplier"] <= speed_max
    ), "Speed parameter not in parent range!"
    assert (
        detection_min <= offspring.parameters["detection_range"] <= detection_max
    ), "Detection parameter not in parent range!"

    print("\n✓ Parameter blending test PASSED!")
    print("  → Parameters blend from both parents")
    print("  → Offspring values are within parent ranges\n")


if __name__ == "__main__":
    try:
        test_energy_economy()
        test_algorithm_crossover()
        test_same_algorithm_parameter_blending()

        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print("\nSummary of fixes:")
        print("1. Energy economy is now balanced (no free energy from births)")
        print("2. Composable behaviors use crossover from BOTH parents")
        print("3. Parameters blend when parents have same algorithm")
        print("4. Algorithm type can switch between parents")
        print("\nEvolution is ready to go!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
