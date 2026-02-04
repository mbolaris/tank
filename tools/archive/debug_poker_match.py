import logging
import random
import sys
from typing import Any, cast

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_poker")


# Mock classes to avoid full engine setup
class MockWorld:
    def __init__(self):
        self.rng = random.Random(42)


class MockGenome:
    def __init__(self):
        self.aggression = 0.5
        self.bluff_frequency = 0.5
        self.risk_tolerance = 0.5
        self.strategy_type = None
        self.base_energy_rate = 1.0
        self.growth_efficiency = 1.0
        self.color_hue = 0.5
        self.color_saturation = 0.5

    def to_dict(self):
        return {}


class MockPlant:
    def __init__(self, energy=100.0):
        self.plant_id = random.randint(1000, 9999)
        self.energy = energy
        self.max_energy = 200.0
        self.genome: Any = MockGenome()
        self.environment = MockWorld()
        self.poker_cooldown = 0
        self.poker_wins = 0
        self.poker_losses = 0
        self.poker_effect_state = None
        self.is_dead = lambda: False
        self.size = 1.0

    def get_poker_id(self):
        return self.plant_id + 100000

    def get_poker_aggression(self):
        return self.genome.aggression

    def get_poker_strategy(self):
        from core.plant_poker_strategy import PlantPokerStrategyAdapter

        return PlantPokerStrategyAdapter(self.genome)

    def gain_energy(self, amount):
        self.energy += amount

    def lose_energy(self, amount):
        self.energy -= amount

    def modify_energy(self, amount):
        # Support for generic interface
        if amount > 0:
            self.gain_energy(amount)
        else:
            self.lose_energy(abs(amount))


class MockFish:
    def __init__(self, energy=100.0):
        self.fish_id = random.randint(1, 999)
        self.energy = energy
        self.max_energy = 200.0
        self.environment = MockWorld()
        self.poker_cooldown = 0
        self.poker_stats = None
        self.visual_state = type("VisualState", (), {"poker_effect_state": None})()
        self.genome = "mock_genome"  # Added to satisfy duck-typing check
        self.size = 1.0

    def get_poker_id(self):
        return self.fish_id

    def get_poker_aggression(self):
        return 0.5

    def get_poker_strategy(self):
        # Fish use simple aggression strategy if None returned
        return None

    def modify_energy(self, amount):
        self.energy += amount

    def set_poker_effect(self, status, amount, target_id=None, target_type=None):
        pass


def run_simulation():
    from core.mixed_poker.interaction import MixedPokerInteraction

    plant_wins = 0
    fish_wins = 0
    total_games = 100

    print(f"Simulating {total_games} poker games between Plant and Fish...")

    for i in range(total_games):
        plant = MockPlant()
        fish = MockFish()

        # Give them different strategies potentially?
        # Make plant aggressive
        plant.genome.aggression = 0.9
        plant.genome.risk_tolerance = 0.9

        interaction = MixedPokerInteraction(
            [cast(Any, fish), cast(Any, plant)],
            rng=random.Random(i),
        )

        if interaction.play_poker():
            assert interaction.result is not None
            if interaction.result.winner_type == "plant":
                plant_wins += 1
                # print(f"Game {i}: Plant Won! Pot: {interaction.result.total_pot:.1f}")
            elif interaction.result.winner_type == "fish":
                fish_wins += 1
            else:
                # Tie
                pass

    print("\nResults:")
    print(f"Plant Wins: {plant_wins}")
    print(f"Fish Wins: {fish_wins}")
    print(f"Plant Win Rate: {plant_wins/total_games*100:.1f}%")


if __name__ == "__main__":
    # Add project root to path
    import os

    sys.path.append(os.getcwd())

    try:
        run_simulation()
    except Exception:
        logger.exception("Simulation failed")
