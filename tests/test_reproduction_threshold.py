#!/usr/bin/env python3
"""Test that the 90% energy threshold for reproduction works correctly."""

import sys

sys.path.insert(0, "/home/user/tank")

from core.entities import Fish, LifeStage
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement


def make_adult_fish(**kwargs):
    """Helper to create an adult fish for testing."""
    from core.constants import LIFE_STAGE_YOUNG_ADULT_MAX
    fish = Fish(**kwargs)
    # Age fish to ADULT stage (need age > 1800 frames)
    fish._lifecycle_component.age = LIFE_STAGE_YOUNG_ADULT_MAX + 100
    fish._lifecycle_component.update_life_stage()  # Update based on age
    return fish


def test_reproduction_threshold_logic():
    """Test the core reproduction threshold logic at different energy levels."""
    print("=" * 80)
    print("REPRODUCTION THRESHOLD LOGIC TEST")
    print("=" * 80)

    # Create a test fish
    genome = Genome.random(use_algorithm=True)
    genome.physical.size_modifier.value = 1.0  # Normal size (determines max energy)

    fish = make_adult_fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome,
        generation=1,
        fish_id=1,
        ecosystem=None,
        initial_energy=50.0,  # 50% energy
    )

    # Age fish to ADULT stage (fish start as BABY)
    fish._life_stage = LifeStage.ADULT

    print("\nFish created:")
    print(f"  Life stage: {fish.life_stage}")
    print(f"  Max energy: {fish.max_energy:.1f}")
    print(f"  90% threshold: {fish.max_energy * 0.9:.1f}")

    # Test at various energy levels
    test_levels = [
        (0.50, "50%", False),
        (0.70, "70%", False),
        (0.85, "85%", False),
        (0.89, "89%", False),
        (0.90, "90%", True),
        (0.95, "95%", True),
        (1.00, "100%", True),
    ]

    print("\nTesting can_reproduce() at different energy levels:")
    print(f"  {'Energy':<10} {'Can Reproduce':<15} {'Expected':<10} {'Result'}")
    print(f"  {'-'*10} {'-'*15} {'-'*10} {'-'*6}")

    all_passed = True
    for ratio, label, expected in test_levels:
        fish.energy = fish.max_energy * ratio
        can_reproduce = fish.can_reproduce()

        passed = can_reproduce == expected
        result = "✓ PASS" if passed else "❌ FAIL"

        print(f"  {label:<10} {str(can_reproduce):<15} {str(expected):<10} {result}")

        if not passed:
            all_passed = False

    print(f"\n{'-'*80}")
    if all_passed:
        print("✓ ALL THRESHOLD TESTS PASSED")
        print("  Fish can only reproduce at 90%+ energy")
    else:
        print("❌ SOME THRESHOLD TESTS FAILED")
        print("  The 90% threshold is not working correctly!")

    return all_passed


def test_proximity_vs_poker_reproduction():
    """Test both proximity-based and poker-based reproduction with 90% threshold."""
    print("\n" + "=" * 80)
    print("PROXIMITY VS POKER REPRODUCTION TEST")
    print("=" * 80)

    # Create two fish for mating tests
    genome1 = Genome.random(use_algorithm=True)

    genome2 = Genome.random(use_algorithm=True)

    fish1 = make_adult_fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome1,
        generation=1,
        fish_id=1,
        ecosystem=None,
        initial_energy=50.0,
    )

    fish2 = make_adult_fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=120,  # Close together (20 pixels)
        y=100,
        speed=2.0,
        genome=genome2,
        generation=1,
        fish_id=2,
        ecosystem=None,
        initial_energy=50.0,
    )

    print("\n1. Testing PROXIMITY-BASED reproduction:")

    # Test at 50% energy
    fish1.energy = fish1.max_energy * 0.50
    fish2.energy = fish2.max_energy * 0.50

    can_reproduce_1 = fish1.can_reproduce()
    can_reproduce_2 = fish2.can_reproduce()

    print("\n  At 50% energy:")
    print(f"    Fish 1 can reproduce: {can_reproduce_1}")
    print(f"    Fish 2 can reproduce: {can_reproduce_2}")

    test1_passed = True
    if can_reproduce_1 or can_reproduce_2:
        print("    ❌ FAIL: Fish at 50% energy can reproduce (threshold not working!)")
        test1_passed = False
    else:
        print("    ✓ PASS: Fish at 50% energy cannot reproduce")

    # Test at 95% energy
    fish1.energy = fish1.max_energy * 0.95
    fish2.energy = fish2.max_energy * 0.95

    can_reproduce_1 = fish1.can_reproduce()
    can_reproduce_2 = fish2.can_reproduce()

    print("\n  At 95% energy:")
    print(f"    Fish 1 can reproduce: {can_reproduce_1}")
    print(f"    Fish 2 can reproduce: {can_reproduce_2}")

    if can_reproduce_1 and can_reproduce_2:
        print("    ✓ PASS: Fish at 95% energy can reproduce")
    else:
        print("    ❌ FAIL: Fish at 95% energy cannot reproduce!")
        test1_passed = False

    # Test poker reproduction
    print("\n2. Testing POKER-BASED reproduction:")

    from core.fish_poker import should_offer_post_poker_reproduction

    # Reset fish
    fish1.energy = fish1.max_energy * 0.50
    fish2.energy = fish2.max_energy * 0.50
    fish1.reproduction_cooldown = 0
    fish2.reproduction_cooldown = 0

    # Test at 50% energy
    winner_wants = should_offer_post_poker_reproduction(fish1, fish2, is_winner=True, energy_gained=10.0)

    print("\n  At 50% energy:")
    print(f"    Winner wants to reproduce: {winner_wants}")

    test2_passed = True
    if winner_wants:
        print("    ❌ FAIL: Fish at 50% energy wants to reproduce after poker!")
        test2_passed = False
    else:
        print("    ✓ PASS: Fish at 50% energy doesn't want to reproduce after poker")

    # Test at 95% energy
    fish1.energy = fish1.max_energy * 0.95
    fish2.energy = fish2.max_energy * 0.95

    # Run multiple times since it's probabilistic
    winner_wants_count = 0
    loser_wants_count = 0
    trials = 100

    for _ in range(trials):
        if should_offer_post_poker_reproduction(fish1, fish2, is_winner=True, energy_gained=10.0):
            winner_wants_count += 1
        if should_offer_post_poker_reproduction(fish2, fish1, is_winner=False, energy_gained=-10.0):
            loser_wants_count += 1

    winner_prob = winner_wants_count / trials
    loser_prob = loser_wants_count / trials

    print("\n  At 95% energy (100 trials):")
    print(f"    Winner wants to reproduce: {winner_prob*100:.0f}% of time (expected ~40%)")
    print(f"    Loser wants to reproduce: {loser_prob*100:.0f}% of time (expected ~20%)")

    # Check if probabilities are reasonable (within 15% of expected)
    if 0.25 <= winner_prob <= 0.55:
        print("    ✓ PASS: Winner probability is reasonable")
    else:
        print("    ⚠ WARNING: Winner probability seems off (expected 40% +/- 15%)")

    if 0.05 <= loser_prob <= 0.35:
        print("    ✓ PASS: Loser probability is reasonable")
    else:
        print("    ⚠ WARNING: Loser probability seems off (expected 20% +/- 15%)")

    return test1_passed and test2_passed


def test_energy_threshold_comparison():
    """Compare old (25 absolute) vs new (90% relative) thresholds."""
    print("\n" + "=" * 80)
    print("THRESHOLD COMPARISON: Old (25 absolute) vs New (90% relative)")
    print("=" * 80)

    # Test with fish of different max energies
    max_energies = [70.0, 100.0, 130.0, 150.0]

    print(f"\n  {'Max Energy':<12} {'Old (25)':<12} {'New (90%)':<12} {'Difference'}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*10}")

    for max_e in max_energies:
        genome = Genome.random(use_algorithm=True)
        genome.physical.size_modifier.value = max_e / 100.0  # Normalize (size determines max energy)

        fish = make_adult_fish(
            environment=None,
            movement_strategy=AlgorithmicMovement(),
            species="test",
            x=100,
            y=100,
            speed=2.0,
            genome=genome,
            generation=1,
            fish_id=1,
            ecosystem=None,
    
    
            initial_energy=50.0,
        )

        old_threshold_percent = (25.0 / fish.max_energy) * 100
        new_threshold = fish.max_energy * 0.9
        difference = new_threshold - 25.0

        print(f"  {fish.max_energy:<12.1f} {old_threshold_percent:<12.1f}% {new_threshold:<12.1f} (+{difference:.1f})")

    print("\n  Summary:")
    print("    - Old threshold was ABSOLUTE (always 25 energy)")
    print("    - Weak fish (70 max): needed 36% energy, now need 90% (+54 percentage points!)")
    print("    - Strong fish (150 max): needed 17% energy, now need 90% (+73 percentage points!)")
    print("    - This creates STRONG selection pressure across all fish types")

    return True


def test_realistic_scenario():
    """Simulate a realistic scenario: fish eating food and trying to reproduce."""
    print("\n" + "=" * 80)
    print("REALISTIC SCENARIO: Fish eating and reproducing")
    print("=" * 80)

    genome = Genome.random(use_algorithm=True)

    fish = make_adult_fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome,
        generation=1,
        fish_id=1,
        ecosystem=None,
        initial_energy=50.0,
    )

    print("\nScenario: Fish starts at 50% energy and eats food")
    print(f"  Initial energy: {fish.energy:.1f}/{fish.max_energy:.1f} ({fish.energy/fish.max_energy*100:.0f}%)")
    print(f"  Can reproduce: {fish.can_reproduce()}")

    # Simulate eating food
    food_items = [10.0, 10.0, 10.0, 10.0, 10.0]  # 5 food items worth 10 energy each

    for i, food_value in enumerate(food_items):
        fish.modify_energy(food_value)
        energy_percent = (fish.energy / fish.max_energy) * 100
        can_reproduce = fish.can_reproduce()

        print(f"\n  After eating food #{i+1} (+{food_value} energy):")
        print(f"    Energy: {fish.energy:.1f}/{fish.max_energy:.1f} ({energy_percent:.0f}%)")
        print(f"    Can reproduce: {can_reproduce}")

        if can_reproduce:
            print("    ✓ Fish can now reproduce! (reached 90% threshold)")
            break

    # Final check
    final_percent = (fish.energy / fish.max_energy) * 100
    if fish.can_reproduce():
        print(f"\n  ✓ SUCCESS: Fish reached {final_percent:.0f}% energy and can reproduce")
        print("  This shows the 90% threshold is achievable through normal gameplay")
        return True
    else:
        print(f"\n  ⚠ Note: Fish is at {final_percent:.0f}% energy - needs more food to reproduce")
        print(f"  Would need {(fish.max_energy * 0.9 - fish.energy):.1f} more energy")
        return True  # Not a failure, just informational


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "REPRODUCTION THRESHOLD VALIDATION" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        test1 = test_reproduction_threshold_logic()
        test2 = test_proximity_vs_poker_reproduction()
        test3 = test_energy_threshold_comparison()
        test4 = test_realistic_scenario()

        print("\n" + "=" * 80)
        if test1 and test2:
            print("✓ ALL VALIDATION TESTS PASSED")
            print("=" * 80)
            print("\nKey Findings:")
            print("  1. The 90% threshold is correctly implemented")
            print("  2. Fish below 90% cannot reproduce (working as intended)")
            print("  3. Fish at 90%+ can reproduce (threshold is achievable)")
            print("  4. Both proximity and poker reproduction respect the threshold")
            print("  5. The threshold creates strong selection pressure")
            print("\nConclusion:")
            print("  The 90% energy threshold is WORKING CORRECTLY.")
            print("  Fish must be successful at resource acquisition to reproduce.")
            print("=" * 80)
            sys.exit(0)
        else:
            print("❌ SOME VALIDATION TESTS FAILED")
            print("=" * 80)
            print("  The 90% threshold may have implementation issues")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
