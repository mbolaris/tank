#!/usr/bin/env python
"""Test poker reproduction with properly scaled energy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.algorithms.energy_management import EnergyConserver
from core.entities import Fish, LifeStage
from core.poker_interaction import PokerInteraction
from core.genetics import Genome


class MockEnvironment:
    def __init__(self):
        self.agents = []
        self.width = 800
        self.height = 600


class MockEcosystem:
    def __init__(self):
        self.frame_count = 0
        self.recent_death_rate = 0.0
        self._next_fish_id = 1

    def generate_new_fish_id(self):
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, fish_id, generation, parent_ids=None, algorithm_id=None, color=None):
        pass

    def record_reproduction(self, algo_id):
        pass

    def record_poker_outcome(self, **kwargs):
        pass


def test_with_scaled_energy():
    """Test with energy properly scaled to fish's max_energy."""
    print("="*70)
    print("PROPERLY SCALED ENERGY TEST")
    print("="*70)

    env = MockEnvironment()
    ecosystem = MockEcosystem()

    genome1 = Genome.random(use_algorithm=True)
    genome2 = Genome.random(use_algorithm=True)

    # Create fish but DON'T set initial energy yet
    fish1 = Fish(
        environment=env,
        movement_strategy=EnergyConserver(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome1,
        generation=1,
        ecosystem=ecosystem,
        initial_energy=50.0  # Placeholder
    )

    fish2 = Fish(
        environment=env,
        movement_strategy=EnergyConserver(),
        species="test",
        x=120,
        y=100,
        speed=2.0,
        genome=genome2,
        generation=1,
        ecosystem=ecosystem,
        initial_energy=50.0  # Placeholder
    )

    # NOW set energy to 95% of their actual max_energy
    fish1.energy = fish1.max_energy * 0.95
    fish2.energy = fish2.max_energy * 0.95

    fish1._lifecycle_component.age = 100
    fish2._lifecycle_component.age = 100
    fish1._lifecycle_component.force_life_stage(LifeStage.ADULT)
    fish2._lifecycle_component.force_life_stage(LifeStage.ADULT)
    fish1._reproduction_component.reproduction_cooldown = 0
    fish2._reproduction_component.reproduction_cooldown = 0

    env.agents = [fish1, fish2]

    print("\nBEFORE POKER:")
    print(f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
    print(f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

    # Play poker
    poker = PokerInteraction([fish1, fish2])
    _success = poker.play_poker()

    print("\nAFTER POKER:")
    print(f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
    print(f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

    if poker.result:
        print("\nPOKER RESULT:")
        print(f"  Winner: Fish #{poker.result.winner_id}")
        print(f"  Energy transferred: {poker.result.energy_transferred:.1f}")
        print(f"  Total pot: {poker.result.total_pot:.1f}")
        print(f"  House cut: {poker.result.house_cut:.1f}")

        winner_fish = fish1 if poker.result.winner_id == fish1.fish_id else fish2
        loser_fish = fish2 if poker.result.winner_id == fish1.fish_id else fish1

        print("\nREPRODUCTION CHECK:")
        print(f"  Winner: {winner_fish.energy:.1f} / {winner_fish.max_energy:.1f} ({winner_fish.energy/winner_fish.max_energy*100:.1f}%)")
        print(f"  Loser: {loser_fish.energy:.1f} / {loser_fish.max_energy:.1f} ({loser_fish.energy/loser_fish.max_energy*100:.1f}%)")
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
                print(f"  This dropped them from 95% to {loser_fish.energy/loser_fish.max_energy*100:.1f}%")


if __name__ == "__main__":
    test_with_scaled_energy()
