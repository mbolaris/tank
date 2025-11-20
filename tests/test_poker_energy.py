#!/usr/bin/env python3
"""Test poker energy transfer to ensure loser loses energy and winner gains less."""

import sys

sys.path.insert(0, "/home/user/tank")

from core.algorithms import GreedyFoodSeeker
from core.entities import Fish
from core.fish_poker import PokerInteraction
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement


def test_poker_energy_transfer():
    """Test that poker energy transfer is correct: winner gains less than loser loses."""
    print("=" * 80)
    print("POKER ENERGY TRANSFER TEST")
    print("=" * 80)

    # Create two test fish with known energy levels
    initial_energy_fish1 = 100.0
    initial_energy_fish2 = 100.0

    genome1 = Genome.random(use_algorithm=True)
    genome1.behavior_algorithm = GreedyFoodSeeker()
    genome1.aggression = 0.5  # Medium aggression

    genome2 = Genome.random(use_algorithm=True)
    genome2.behavior_algorithm = GreedyFoodSeeker()
    genome2.aggression = 0.5  # Medium aggression

    fish1 = Fish(
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
        screen_width=800,
        screen_height=600,
        initial_energy=initial_energy_fish1,
    )

    fish2 = Fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=150,
        y=150,
        speed=2.0,
        genome=genome2,
        generation=1,
        fish_id=2,
        ecosystem=None,
        screen_width=800,
        screen_height=600,
        initial_energy=initial_energy_fish2,
    )

    print("\nInitial State:")
    print(
        f"  Fish 1 (ID={fish1.fish_id}): {initial_energy_fish1:.2f} energy, size={fish1.size:.3f}"
    )
    print(
        f"  Fish 2 (ID={fish2.fish_id}): {initial_energy_fish2:.2f} energy, size={fish2.size:.3f}"
    )
    print(f"  Total energy: {initial_energy_fish1 + initial_energy_fish2:.2f}")

    # Play poker
    poker = PokerInteraction(fish1, fish2)
    success = poker.play_poker()

    if not success:
        print("\n❌ Poker game failed to play")
        return False

    # Get final energies
    final_energy_fish1 = fish1.energy
    final_energy_fish2 = fish2.energy
    total_final = final_energy_fish1 + final_energy_fish2
    total_initial = initial_energy_fish1 + initial_energy_fish2

    print("\nFinal State:")
    print(f"  Fish 1 (ID={fish1.fish_id}): {final_energy_fish1:.2f} energy")
    print(f"  Fish 2 (ID={fish2.fish_id}): {final_energy_fish2:.2f} energy")
    print(f"  Total energy: {total_final:.2f}")

    # Calculate energy changes
    delta_fish1 = final_energy_fish1 - initial_energy_fish1
    delta_fish2 = final_energy_fish2 - initial_energy_fish2
    total_delta = total_final - total_initial

    print("\nEnergy Changes:")
    print(f"  Fish 1: {delta_fish1:+.2f}")
    print(f"  Fish 2: {delta_fish2:+.2f}")
    print(f"  Total change: {total_delta:.2f}")

    # Determine winner and loser
    if poker.result.winner_id == fish1.fish_id:
        winner_delta = delta_fish1
        loser_delta = delta_fish2
        winner_name = "Fish 1"
    elif poker.result.winner_id == fish2.fish_id:
        winner_delta = delta_fish2
        loser_delta = delta_fish1
        winner_name = "Fish 2"
    else:
        # Tie
        print("\nResult: TIE")
        print("  Both fish should have same energy as before")
        assert abs(delta_fish1) < 0.01, f"Fish 1 energy changed on tie: {delta_fish1}"
        assert abs(delta_fish2) < 0.01, f"Fish 2 energy changed on tie: {delta_fish2}"
        print("\n✓ Tie handled correctly!")
        return True

    print(f"\nResult: {winner_name} WINS")
    print(
        f"  Winner's hand: {poker.result.hand1 if poker.result.winner_id == fish1.fish_id else poker.result.hand2}"
    )
    print(
        f"  Loser's hand: {poker.result.hand2 if poker.result.winner_id == fish1.fish_id else poker.result.hand1}"
    )
    print(f"  Energy transferred (reported): {poker.result.energy_transferred:.2f}")
    print(f"  Final pot: {poker.result.final_pot:.2f}")

    print("\nEnergy Analysis:")
    print(f"  Winner gained: {winner_delta:+.2f}")
    print(f"  Loser lost: {loser_delta:+.2f}")
    print(f"  House cut (calculated): {total_delta:.2f}")

    # Key assertions
    print(f"\n{'='*80}")
    print("ASSERTIONS:")
    print(f"{'='*80}")

    # 1. Loser should have lost energy
    print("\n1. Loser should have LOST energy:")
    print(f"   Loser's delta: {loser_delta:.2f}")
    assert loser_delta < -0.01, f"❌ FAIL: Loser did not lose energy! Delta: {loser_delta}"
    print(f"   ✓ PASS: Loser lost {abs(loser_delta):.2f} energy")

    # 2. Winner should have gained energy
    print("\n2. Winner should have GAINED energy:")
    print(f"   Winner's delta: {winner_delta:.2f}")
    assert winner_delta > 0.01, f"❌ FAIL: Winner did not gain energy! Delta: {winner_delta}"
    print(f"   ✓ PASS: Winner gained {winner_delta:.2f} energy")

    # 3. Winner should gain LESS than loser lost (due to house cut)
    print("\n3. Winner should gain LESS than loser lost (house cut):")
    print(f"   Winner gained: {winner_delta:.2f}")
    print(f"   Loser lost: {abs(loser_delta):.2f}")
    print(f"   Difference: {abs(loser_delta) - winner_delta:.2f}")

    if abs(winner_delta + loser_delta) < 0.01:
        print("   ❌ FAIL: Winner gained EXACTLY what loser lost!")
        print("   This means energy is conserved, but it shouldn't be!")
        print("   There should be a house cut that removes energy from the system.")
        return False
    else:
        house_cut = abs(total_delta)
        house_cut_percentage = (house_cut / abs(loser_delta) * 100) if abs(loser_delta) > 0 else 0
        print(
            f"   ✓ PASS: House cut of {house_cut:.2f} energy ({house_cut_percentage:.1f}% of loser's loss)"
        )

    # 4. Total energy should decrease (house cut)
    print("\n4. Total energy should DECREASE (house cut removes energy):")
    print(f"   Initial total: {total_initial:.2f}")
    print(f"   Final total: {total_final:.2f}")
    print(f"   Decrease: {abs(total_delta):.2f}")
    assert total_delta < -0.01, "❌ FAIL: Total energy did not decrease!"
    print("   ✓ PASS: Energy was removed from system via house cut")

    print(f"\n{'='*80}")
    print("✓ ALL POKER ENERGY TRANSFER TESTS PASSED!")
    print(f"{'='*80}")
    print("\nSummary:")
    print(f"  • Loser lost: {abs(loser_delta):.2f} energy")
    print(f"  • Winner gained: {winner_delta:.2f} energy")
    print(f"  • House took: {abs(total_delta):.2f} energy")
    print(f"  • Winner gained {(winner_delta / abs(loser_delta) * 100):.1f}% of loser's loss")

    return True


def test_multiple_poker_games():
    """Run multiple poker games to ensure consistency."""
    print("\n" + "=" * 80)
    print("MULTIPLE POKER GAMES TEST")
    print("=" * 80)

    results = []

    for i in range(10):
        print(f"\nGame {i+1}:")

        initial_energy = 100.0

        genome1 = Genome.random(use_algorithm=True)
        genome2 = Genome.random(use_algorithm=True)

        fish1 = Fish(
            environment=None,
            movement_strategy=AlgorithmicMovement(),
            species="test",
            x=100,
            y=100,
            speed=2.0,
            genome=genome1,
            generation=1,
            fish_id=i * 2 + 1,
            ecosystem=None,
            screen_width=800,
            screen_height=600,
            initial_energy=initial_energy,
        )

        fish2 = Fish(
            environment=None,
            movement_strategy=AlgorithmicMovement(),
            species="test",
            x=150,
            y=150,
            speed=2.0,
            genome=genome2,
            generation=1,
            fish_id=i * 2 + 2,
            ecosystem=None,
            screen_width=800,
            screen_height=600,
            initial_energy=initial_energy,
        )

        poker = PokerInteraction(fish1, fish2)
        success = poker.play_poker()

        if not success:
            print("  Game failed")
            continue

        total_initial = initial_energy * 2
        total_final = fish1.energy + fish2.energy
        total_delta = total_final - total_initial

        if poker.result.winner_id != -1:
            winner_delta = (
                fish1.energy - initial_energy
                if poker.result.winner_id == fish1.fish_id
                else fish2.energy - initial_energy
            )
            loser_delta = (
                fish2.energy - initial_energy
                if poker.result.winner_id == fish1.fish_id
                else fish1.energy - initial_energy
            )

            print(
                f"  Winner gained: {winner_delta:+.2f}, Loser lost: {loser_delta:+.2f}, "
                f"House cut: {abs(total_delta):.2f}"
            )
            print(
                f"  Pot: {poker.result.final_pot:.2f}, Reported transfer: {poker.result.energy_transferred:.2f}"
            )

            # Check that winner != loser
            if abs(winner_delta + loser_delta) < 0.01:
                print("  ❌ FAIL: Winner gained exactly what loser lost!")
                results.append(False)
            else:
                print("  ✓ PASS: House cut working")
                results.append(True)
        else:
            print("  Tie")
            results.append(True)

    print(f"\n{'='*80}")
    successful = sum(results)
    total = len(results)
    print(f"Results: {successful}/{total} games had proper energy transfer")

    if successful == total:
        print("✓ ALL GAMES PASSED!")
        return True
    else:
        print("❌ SOME GAMES FAILED!")
        return False


def test_poker_result_fields():
    """Test that PokerResult.winner_actual_gain matches actual energy changes."""
    print("\n" + "=" * 80)
    print("POKER RESULT FIELDS TEST")
    print("=" * 80)

    from core.algorithms import GreedyFoodSeeker
    from core.entities import Fish
    from core.fish_poker import PokerInteraction
    from core.genetics import Genome
    from core.movement_strategy import AlgorithmicMovement

    initial_energy = 100.0

    genome1 = Genome.random(use_algorithm=True)
    genome1.behavior_algorithm = GreedyFoodSeeker()
    genome1.aggression = 0.5

    genome2 = Genome.random(use_algorithm=True)
    genome2.behavior_algorithm = GreedyFoodSeeker()
    genome2.aggression = 0.5

    fish1 = Fish(
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
        screen_width=800,
        screen_height=600,
        initial_energy=initial_energy,
    )

    fish2 = Fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=150,
        y=150,
        speed=2.0,
        genome=genome2,
        generation=1,
        fish_id=2,
        ecosystem=None,
        screen_width=800,
        screen_height=600,
        initial_energy=initial_energy,
    )

    poker = PokerInteraction(fish1, fish2)
    success = poker.play_poker()

    if not success:
        print("❌ Poker game failed")
        return False

    if poker.result.winner_id == -1:
        print("Game was a tie, skipping")
        return True

    # Calculate actual energy changes
    winner_delta = (
        fish1.energy - initial_energy
        if poker.result.winner_id == fish1.fish_id
        else fish2.energy - initial_energy
    )
    loser_delta = (
        fish2.energy - initial_energy
        if poker.result.winner_id == fish1.fish_id
        else fish1.energy - initial_energy
    )

    print("\nPokerResult fields:")
    print(f"  energy_transferred: {poker.result.energy_transferred:.2f} (loser's loss)")
    print(f"  winner_actual_gain: {poker.result.winner_actual_gain:.2f} (winner's gain)")
    print("\nActual energy changes:")
    print(f"  Winner gained: {winner_delta:.2f}")
    print(f"  Loser lost: {loser_delta:.2f}")

    # Verify winner_actual_gain matches the actual winner delta
    assert (
        abs(poker.result.winner_actual_gain - winner_delta) < 0.01
    ), f"winner_actual_gain ({poker.result.winner_actual_gain:.2f}) doesn't match actual gain ({winner_delta:.2f})"

    # Verify energy_transferred matches the actual loser delta
    assert (
        abs(poker.result.energy_transferred - abs(loser_delta)) < 0.01
    ), f"energy_transferred ({poker.result.energy_transferred:.2f}) doesn't match loser's loss ({abs(loser_delta):.2f})"

    # Verify winner gained less than loser lost
    assert (
        poker.result.winner_actual_gain < poker.result.energy_transferred
    ), "Winner should gain less than loser loses (due to house cut)"

    print("\n✓ ALL FIELD VALIDATIONS PASSED!")
    print("  • winner_actual_gain correctly represents what winner gained")
    print("  • energy_transferred correctly represents what loser lost")
    print("  • winner_actual_gain < energy_transferred (house cut working)")

    return True


if __name__ == "__main__":
    try:
        # Run single game test
        test1_passed = test_poker_energy_transfer()

        # Run multiple games test
        test2_passed = test_multiple_poker_games()

        # Run result fields test
        test3_passed = test_poker_result_fields()

        if test1_passed and test2_passed and test3_passed:
            print("\n" + "=" * 80)
            print("ALL POKER TESTS PASSED! ✓")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("SOME TESTS FAILED! ❌")
            print("=" * 80)
            sys.exit(1)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
