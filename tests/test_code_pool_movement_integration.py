import random
from typing import Tuple

import pytest

from core.code_pool import CodePool
from core.entities.fish import Fish
from core.environment import Environment
from core.genetics.trait import GeneticTrait
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement


class StubBehavior:
    def __init__(self, vx: float, vy: float) -> None:
        self._vx = vx
        self._vy = vy

    def execute(self, fish: Fish) -> Tuple[float, float]:
        return self._vx, self._vy


def _make_fish(env: Environment, behavior: StubBehavior) -> Fish:
    movement = AlgorithmicMovement()
    fish = Fish(
        environment=env,
        movement_strategy=movement,
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    fish.genome.behavioral.behavior = GeneticTrait(behavior)
    fish.vel = Vector2(0, 0)
    return fish


def test_code_policy_movement_overrides_composable_behavior():
    rng = random.Random(42)
    pool = CodePool()
    pool.register("fixed_policy", lambda obs, rng: (0.0, 1.0))

    env = Environment(width=800, height=600, rng=rng, code_pool=pool)
    fish = _make_fish(env, StubBehavior(-1.0, 0.0))
    fish.genome.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    fish.genome.behavioral.code_policy_component_id = GeneticTrait("fixed_policy")

    fish.movement_strategy.move(fish)

    assert fish.vel.y > 0.0
    assert fish.vel.x == pytest.approx(0.0)


def test_code_policy_fallbacks_when_pool_missing():
    rng = random.Random(7)
    env = Environment(width=800, height=600, rng=rng)
    fish = _make_fish(env, StubBehavior(1.0, 0.0))
    fish.genome.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    fish.genome.behavioral.code_policy_component_id = GeneticTrait("missing_policy")

    fish.movement_strategy.move(fish)

    assert fish.vel.x > 0.0


def test_code_policy_fallbacks_when_component_missing():
    rng = random.Random(11)
    pool = CodePool()
    env = Environment(width=800, height=600, rng=rng, code_pool=pool)
    fish = _make_fish(env, StubBehavior(1.0, 0.0))
    fish.genome.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    fish.genome.behavioral.code_policy_component_id = GeneticTrait("missing_policy")

    fish.movement_strategy.move(fish)

    assert fish.vel.x > 0.0
