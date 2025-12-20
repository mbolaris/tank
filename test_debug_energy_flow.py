#!/usr/bin/env python
"""Debug energy flow during poker to understand why reproduction fails."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.algorithms.energy_management import EnergyConserver
from core.entities import Fish, LifeStage
from core.fish_poker import PokerInteraction
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

    def get_next_fish_id(self):
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, fish_id, generation, parent_ids=None, algorithm_id=None, color=None):
        pass

    def record_reproduction(self, algo_id):
        pass

    def record_poker_outcome(self, **kwargs):
        pass


def test_energy_flow():
    """Trace energy through a poker game."""
    print("="*70)
    print("ENERGY FLOW DEBUG TEST")
    print("="*70)

    env = MockEnvironment()
    ecosystem = MockEcosystem()

    genome1 = Genome.random(use_algorithm=True)
    genome2 = Genome.random(use_algorithm=True)

    # Create fish with HIGH energy (near max)
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
        initial_energy=100.0  # Start at max
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
        initial_energy=100.0  # Start at max
    )

    fish1._lifecycle_component.age = 100
    fish2._lifecycle_component.age = 100
    fish1._lifecycle_component.current_stage = LifeStage.ADULT
    fish2._lifecycle_component.current_stage = LifeStage.ADULT
    fish1.reproduction_cooldown = 0
    fish2.reproduction_cooldown = 0

    env.agents = [fish1, fish2]

    print("\nBEFORE POKER:")
    print(f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
    print(f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

    # Play poker
    poker = PokerInteraction(fish1, fish2)
    _success = poker.play_poker()

    print("\nAFTER POKER:")
    print(f"  Fish 1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
    print(f"  Fish 2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

    if poker.result:
        print("\nPOKER RESULT:")
        print(f"  Winner: Fish #{poker.result.winner_id}")
        print(f"  Energy transferred: {poker.result.energy_transferred:.1f}")
        print(f"  Winner actual gain: {poker.result.winner_actual_gain:.1f}")
        print(f"  Reproduction occurred: {poker.result.reproduction_occurred}")

        winner_fish = fish1 if poker.result.winner_id == fish1.fish_id else fish2
        loser_fish = fish2 if poker.result.winner_id == fish1.fish_id else fish1

        print("\nREPRODUCTION CHECK:")
        print(f"  Winner energy: {winner_fish.energy:.1f} / {winner_fish.max_energy:.1f} ({winner_fish.energy/winner_fish.max_energy*100:.1f}%)")
        print(f"  Loser energy: {loser_fish.energy:.1f} / {loser_fish.max_energy:.1f} ({loser_fish.energy/loser_fish.max_energy*100:.1f}%)")
        print(f"  Winner 90% threshold: {winner_fish.max_energy * 0.9:.1f}")
        print(f"  Loser 90% threshold: {loser_fish.max_energy * 0.9:.1f}")
        print(f"  Winner above threshold: {winner_fish.energy >= winner_fish.max_energy * 0.9}")
        print(f"  Loser above threshold: {loser_fish.energy >= loser_fish.max_energy * 0.9}")

        if poker.result.reproduction_occurred:
            print("\n✓ REPRODUCTION OCCURRED!")
            print(f"  Offspring: Fish #{poker.result.offspring.fish_id}")
        else:
            print("\n❌ REPRODUCTION FAILED")
            print("  Likely reason: One or both fish below 90% energy threshold")


if __name__ == "__main__":
    test_energy_flow()
