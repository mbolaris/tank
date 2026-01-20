"""Reproduction credit gating for soccer rewards."""

from __future__ import annotations

import random

from core.agents.components.reproduction_component import ReproductionComponent
from core.config.simulation_config import SimulationConfig
from core.entities import LifeStage
from core.reproduction_service import ReproductionService


class _DummyTrait:
    def __init__(self, value: float) -> None:
        self.value = value


class _DummyBehavioral:
    def __init__(self, chance: float) -> None:
        self.asexual_reproduction_chance = _DummyTrait(chance)


class _DummyGenome:
    def __init__(self, chance: float) -> None:
        self.behavioral = _DummyBehavioral(chance)


class _DummyLifecycle:
    def __init__(self) -> None:
        self.life_stage = LifeStage.ADULT


class _DummyEnv:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng


class _DummyFish:
    def __init__(self, rng: random.Random) -> None:
        self.environment = _DummyEnv(rng)
        self.energy = 100.0
        self.max_energy = 100.0
        self._reproduction_component = ReproductionComponent()
        self._lifecycle_component = _DummyLifecycle()
        self.genome = _DummyGenome(1.0)

    def _create_asexual_offspring(self):
        return _DummyBaby()


class _DummyBaby:
    def register_birth(self) -> None:
        return None


class _DummyEngine:
    def __init__(self, fish_list: list[_DummyFish]) -> None:
        self._fish_list = list(fish_list)
        self.rng = random.Random(1)
        self.config = SimulationConfig.headless_fast()
        self.config.soccer.enabled = True
        self.config.soccer.repro_reward_mode = "credits"
        self.config.soccer.repro_credit_required = 1.0
        self.ecosystem = None
        self.lifecycle_system = None
        self.spawned: list[object] = []

    def get_fish_list(self):
        return list(self._fish_list)

    def request_spawn(self, entity, **_):
        self.spawned.append(entity)
        return True


def test_reproduction_requires_credits() -> None:
    rng = random.Random(7)
    fish = _DummyFish(rng)
    engine = _DummyEngine([fish])
    service = ReproductionService(engine)

    service.update_frame(1)
    assert engine.spawned == []

    fish._reproduction_component.repro_credits = 1.0
    service.update_frame(2)
    assert len(engine.spawned) == 1
    assert fish._reproduction_component.repro_credits == 0.0
