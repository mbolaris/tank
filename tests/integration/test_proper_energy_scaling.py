#!/usr/bin/env python
"""Test poker reproduction with properly scaled energy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.entities import Fish, LifeStage
from core.environment import Environment
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement
from core.poker_interaction import PokerInteraction


def test_with_scaled_energy():
    """Test with energy properly scaled to fish's max_energy."""
    print("=" * 70)
    print("PROPERLY SCALED ENERGY TEST")
    print("=" * 70)

    env = Environment(agents=[], width=800, height=600)

    genome1 = Genome.random(use_algorithm=True)
    genome2 = Genome.random(use_algorithm=True)

    # Create fish but DON'T set initial energy yet
    fish1 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome1,
        generation=1,
        fish_id=1,
        initial_energy=50.0,  # Placeholder
    )

    fish2 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=120,
        y=100,
        speed=2.0,
        genome=genome2,
        generation=1,
        fish_id=2,
        initial_energy=50.0,  # Placeholder
    )

    # NOW set energy to 95% of their actual max_energy
    fish1.energy = fish1.max_energy * 0.95
    fish2.energy = fish2.max_energy * 0.95

    fish1.age = 100
    fish2.age = 100
    fish1.force_life_stage(LifeStage.ADULT)
    fish2.force_life_stage(LifeStage.ADULT)
    fish1._reproduction_component.reproduction_cooldown = 0
    fish2._reproduction_component.reproduction_cooldown = 0

    env.agents = [fish1, fish2]

    print("\nBEFORE POKER:")
    print(
        f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)"
    )
    print(
        f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)"
    )

    # Play poker
    poker = PokerInteraction([fish1, fish2])
    _success = poker.play_poker()

    print("\nAFTER POKER:")
    print(
        f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)"
    )
    print(
        f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)"
    )

    if poker.result:
        print("\nPOKER RESULT:")
        print(f"  Winner: Fish #{poker.result.winner_id}")
        print(f"  Energy transferred: {poker.result.energy_transferred:.1f}")
        print(f"  Total pot: {poker.result.total_pot:.1f}")
        print(f"  House cut: {poker.result.house_cut:.1f}")

        winner_fish = fish1 if poker.result.winner_id == fish1.fish_id else fish2
        loser_fish = fish2 if poker.result.winner_id == fish1.fish_id else fish1

        print("\nREPRODUCTION CHECK:")
        print(
            f"  Winner: {winner_fish.energy:.1f} / {winner_fish.max_energy:.1f} ({winner_fish.energy/winner_fish.max_energy*100:.1f}%)"
        )
        print(
            f"  Loser: {loser_fish.energy:.1f} / {loser_fish.max_energy:.1f} ({loser_fish.energy/loser_fish.max_energy*100:.1f}%)"
        )
        print(f"  Winner above 90%: {winner_fish.energy >= winner_fish.max_energy * 0.9}")
        print(f"  Loser above 90%: {loser_fish.energy >= loser_fish.max_energy * 0.9}")

        # Check if reproduction would be triggered using the new API
        from core.poker_interaction import should_trigger_reproduction

        can_reproduce = should_trigger_reproduction(winner_fish, loser_fish)

        if can_reproduce:
            print("\n✓✓✓ SUCCESS! REPRODUCTION CONDITIONS MET!")
        else:
            print("\n❌ REPRODUCTION CONDITIONS NOT MET")

            # Analyze why
            if loser_fish.energy < loser_fish.max_energy * 0.9:
                deficit = (loser_fish.max_energy * 0.9) - loser_fish.energy
                print(f"  Loser is {deficit:.1f} energy short of 90% threshold")
                print(f"  Loser lost {poker.result.energy_transferred:.1f} energy in poker")
                print(
                    f"  This dropped them from 95% to {loser_fish.energy/loser_fish.max_energy*100:.1f}%"
                )


if __name__ == "__main__":
    test_with_scaled_energy()
