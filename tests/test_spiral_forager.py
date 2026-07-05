"""Targeted branch coverage for the deprecated SpiralForager behavior."""

from __future__ import annotations

import math
import random
from types import SimpleNamespace
from typing import Any

from core.algorithms.food_seeking.spiral import SpiralForager
from core.config.food import FOOD_PURSUIT_RANGE_EXTENDED, PREDATOR_FLEE_DISTANCE_SAFE
from core.entities import Crab
from core.math_utils import Vector2


class _World:
    def __init__(self, *, predator: Any | None = None, food: Any | None = None) -> None:
        self.predator = predator
        self.food = food

    def get_agents_of_type(self, agent_type: type) -> list[Any]:
        if agent_type is Crab and self.predator is not None:
            return [self.predator]
        return []

    def closest_food(self, _fish: Any, _max_distance: float) -> Any | None:
        return self.food


def _fish(*, energy: float = 100.0, max_energy: float = 100.0, world: _World) -> Any:
    return SimpleNamespace(
        pos=Vector2(100.0, 100.0),
        energy=energy,
        max_energy=max_energy,
        environment=world,
    )


def _entity_at(x: float, y: float) -> Any:
    return SimpleNamespace(pos=Vector2(x, y))


def test_spiral_forager_random_instance_uses_supplied_rng() -> None:
    algo = SpiralForager.random_instance(rng=random.Random(0))

    assert isinstance(algo, SpiralForager)
    assert algo.algorithm_id == "spiral_forager"


def test_spiral_forager_flees_close_predator_before_food() -> None:
    predator = _entity_at(100.0 - PREDATOR_FLEE_DISTANCE_SAFE / 2.0, 100.0)
    food = _entity_at(100.0 + 10.0, 100.0)
    fish = _fish(world=_World(predator=predator, food=food))
    algo = SpiralForager(rng=random.Random(1))

    vx, vy = algo.execute(fish)

    assert vx == 1.3
    assert vy == 0.0


def test_spiral_forager_pursues_nearby_food() -> None:
    food = _entity_at(100.0, 100.0 + FOOD_PURSUIT_RANGE_EXTENDED / 2.0)
    fish = _fish(world=_World(food=food))
    algo = SpiralForager(rng=random.Random(2))

    vx, vy = algo.execute(fish)

    assert vx == 0.0
    assert math.isclose(vy, algo.parameters["food_pursuit_speed"])


def test_spiral_forager_desperate_fish_pursues_distant_food_faster() -> None:
    food = _entity_at(100.0, 100.0 + FOOD_PURSUIT_RANGE_EXTENDED * 2.0)
    fish = _fish(energy=20.0, max_energy=100.0, world=_World(food=food))
    algo = SpiralForager(rng=random.Random(3))

    vx, vy = algo.execute(fish)

    assert vx == 0.0
    assert math.isclose(vy, algo.parameters["food_pursuit_speed"] * 1.3)


def test_spiral_forager_search_resets_large_radius() -> None:
    fish = _fish(world=_World())
    algo = SpiralForager(rng=random.Random(4))
    algo.spiral_radius = 150.0

    vx, vy = algo.execute(fish)

    assert algo.spiral_radius == 10.0
    assert math.isclose(vx, math.cos(0.25) * algo.parameters["spiral_speed"])
    assert math.isclose(vy, math.sin(0.25) * algo.parameters["spiral_speed"])
