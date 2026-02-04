import math
from typing import cast

from core.ecosystem import EcosystemManager
from core.entities import Fish
from core.entities.resources import Food
from core.movement_strategy import AlgorithmicMovement
from core.telemetry.events import FoodEatenEvent
from core.world import World


class _EnvStub:
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.width = width
        self.height = height

    def get_bounds(self):
        return (0.0, 0.0), (float(self.width), float(self.height))


def test_fish_eat_without_ecosystem():
    env = _EnvStub()
    fish = Fish(
        environment=cast(World, env),
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        ecosystem=None,
    )
    fish.energy = fish.max_energy * 0.5
    food = Food(environment=cast(World, env), x=110, y=110, food_type="energy")

    before = fish.energy
    fish.eat(food)

    assert fish.energy >= before


def test_ecosystem_records_food_event():
    ecosystem = EcosystemManager()
    ecosystem.record_event(FoodEatenEvent("nectar", algorithm_id=0, energy_gained=5.0))

    assert math.isclose(
        ecosystem.energy_sources.get("nectar", 0.0),
        5.0,
        rel_tol=0,
        abs_tol=1e-9,
    )
