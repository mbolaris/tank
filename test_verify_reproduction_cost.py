#!/usr/bin/env python
"""Verify that reproduction energy cost is being applied correctly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.algorithms.energy_management import EnergyConserver
from core.config.fish import POST_POKER_PARENT_ENERGY_CONTRIBUTION
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
        # Minimal reproduction manager stub expected by fish behavior
        class _StubReproductionManager:
            def record_reproduction(self, algorithm_id: int, is_asexual: bool = False):
                return None

            def update_pregnant_count(self, count: int):
                return None
            def record_reproduction_attempt(self, success: bool) -> None:
                return None

        self.reproduction_manager = _StubReproductionManager()

    def get_next_fish_id(self):
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, fish_id, generation, parent_ids=None, algorithm_id=None, color=None):
        pass

    def record_reproduction(self, algo_id):
        # Accept optional keyword to match EcosystemManager.record_reproduction
        return None

    def record_poker_outcome(self, **kwargs):
        pass

    def record_poker_energy_gain(self, amount: float) -> None:
        # Minimal mock behavior: just accept the call and ignore
        # This mirrors EcosystemManager.record_poker_energy_gain which delegates
        # to record_energy_gain; tests only need the method to exist.
        return None


# Monkey-patch should_offer_post_poker_reproduction to log when it's called
original_should_offer = None

def logging_should_offer(fish, opponent, is_winner, energy_gained=0.0):
    """Wrapper that logs energy checks."""
    result = original_should_offer(fish, opponent, is_winner, energy_gained)
    role = "WINNER" if is_winner else "LOSER"
    energy_pct = (fish.energy / fish.max_energy * 100) if fish.max_energy > 0 else 0
    _threshold_pct = 90.0
    print(f"  [{role}] Fish #{fish.fish_id}: {fish.energy:.1f}/{fish.max_energy:.1f} ({energy_pct:.1f}%) → {result}")
    return result


def test_reproduction_energy_cost():
    """Test that reproduction energy cost is applied after check."""
    print("="*70)
    print("REPRODUCTION ENERGY COST VERIFICATION")
    print("="*70)

    # Patch the function
    global original_should_offer
    from core import fish_poker
    original_should_offer = fish_poker.should_offer_post_poker_reproduction
    fish_poker.should_offer_post_poker_reproduction = logging_should_offer

    try:
        env = MockEnvironment()
        ecosystem = MockEcosystem()

        genome1 = Genome.random(use_algorithm=True)
        genome2 = Genome.random(use_algorithm=True)

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
            initial_energy=50.0
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
            initial_energy=50.0
        )

        # Set to 95% of max_energy
        fish1.energy = fish1.max_energy * 0.95
        fish2.energy = fish2.max_energy * 0.95

        fish1._lifecycle_component.age = 100
        fish2._lifecycle_component.age = 100
        fish1._lifecycle_component.current_stage = LifeStage.ADULT
        fish2._lifecycle_component.current_stage = LifeStage.ADULT
        fish1.reproduction_cooldown = 0
        fish2.reproduction_cooldown = 0

        env.agents = [fish1, fish2]

        print("\nBEFORE POKER:")
        print(f"  Fish #1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
        print(f"  Fish #2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

        # Play poker
        print("\nPLAYING POKER...")
        poker = PokerInteraction(fish1, fish2)
        _success = poker.play_poker()

        print("\nAFTER POKER:")
        print(f"  Fish #1: {fish1.energy:.1f} / {fish1.max_energy:.1f} ({fish1.energy/fish1.max_energy*100:.1f}%)")
        print(f"  Fish #2: {fish2.energy:.1f} / {fish2.max_energy:.1f} ({fish2.energy/fish2.max_energy*100:.1f}%)")

        if poker.result and poker.result.reproduction_occurred:
            print("\n✓ REPRODUCTION OCCURRED!")
            print(f"  Expected energy cost per parent: {POST_POKER_PARENT_ENERGY_CONTRIBUTION * 100}% of current energy")
            print(f"  Offspring energy: {poker.result.offspring.energy:.1f}")
        else:
            print("\n❌ No reproduction occurred")

    finally:
        # Restore original function
        fish_poker.should_offer_post_poker_reproduction = original_should_offer


if __name__ == "__main__":
    test_reproduction_energy_cost()
