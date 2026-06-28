"""Standard proximity mating through ReproductionService."""

from __future__ import annotations

import random
from typing import cast

from core.config.fish import (
    ENERGY_MAX_DEFAULT,
    FISH_BABY_SIZE,
    STANDARD_MATING_PARENT_ENERGY_CONTRIBUTION,
)
from core.config.simulation_config import SimulationConfig
from core.entities import Fish, LifeStage
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement
from core.reproduction.reproduction_service import ReproductionService
from core.world import World


class _MiniEcosystem:
    def __init__(self) -> None:
        self._next_fish_id = 1
        self.reproductions: list[bool] = []
        self.mating_attempts: list[bool] = []
        self.births = 0

    def generate_new_fish_id(self) -> int:
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, *_args, **_kwargs) -> None:
        self.births += 1

    def record_reproduction(self, _algorithm_id: int, is_asexual: bool = False) -> None:
        self.reproductions.append(is_asexual)

    def record_mating_attempt(self, success: bool) -> None:
        self.mating_attempts.append(success)

    def record_energy_burn(self, _source: str, _amount: float) -> None:
        return None

    def record_energy_gain(self, _source: str, _amount: float) -> None:
        return None


class _MiniEnvironment:
    def __init__(self) -> None:
        self.width = 300
        self.height = 200
        self.rng = random.Random(42)

    def get_bounds(self):
        return (0.0, 0.0), (float(self.width), float(self.height))

    def list_policy_component_ids(self, _kind: str) -> list[str]:
        return []


class _EntityManager:
    def __init__(self, fish: list[Fish]) -> None:
        self._fish = fish

    def get_fish(self) -> list[Fish]:
        return list(self._fish)


class _LifecycleSystem:
    def __init__(self) -> None:
        self.births = 0

    def record_birth(self) -> None:
        self.births += 1


class _MiniEngine:
    def __init__(self, fish: list[Fish], env: _MiniEnvironment) -> None:
        self.entity_manager = _EntityManager(fish)
        self.environment = env
        self.rng = env.rng
        self.ecosystem = None
        self.lifecycle_system = _LifecycleSystem()
        self.config = SimulationConfig.headless_fast()
        self.spawned: list[Fish] = []
        self.spawn_reasons: list[str] = []

    def request_spawn(self, entity: Fish, *, reason: str) -> bool:
        self.spawned.append(entity)
        self.spawn_reasons.append(reason)
        return True


def _adult_fish(
    env: _MiniEnvironment,
    ecosystem: _MiniEcosystem,
    *,
    x: float,
    y: float,
    energy_ratio: float,
) -> Fish:
    genome = Genome.random(use_algorithm=True, rng=env.rng)
    genome.physical.size_modifier.value = 1.0
    fish = Fish(
        environment=cast(World, env),
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=x,
        y=y,
        speed=2.0,
        genome=genome,
        generation=2,
        ecosystem=cast("object", ecosystem),
        initial_energy=ENERGY_MAX_DEFAULT * energy_ratio,
    )
    fish.force_life_stage(LifeStage.ADULT)
    fish.energy = fish.max_energy * energy_ratio
    fish._reproduction_component.reproduction_cooldown = 0
    fish.genome.behavioral.asexual_reproduction_chance.value = 1.0
    return fish


def test_proximity_mating_spawns_sexual_offspring_before_cloning() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()
    parent = _adult_fish(env, ecosystem, x=80, y=80, energy_ratio=1.0)
    mate = _adult_fish(env, ecosystem, x=100, y=80, energy_ratio=1.0)
    engine = _MiniEngine([parent, mate], env)
    service = ReproductionService(cast("SimpleNamespace", engine))

    parent_energy_before = parent.energy
    mate_energy_before = mate.energy

    assert parent.try_mate(mate)
    stats = service.update_frame(1)

    assert stats.proximity_sexual == 1
    assert stats.trait_asexual == 0
    assert len(engine.spawned) == 1
    assert engine.spawn_reasons == ["proximity_mating"]
    assert engine.lifecycle_system.births == 1
    assert service.get_debug_info()["proximity_reproductions"] == 1

    baby = engine.spawned[0]
    expected_contribution = (
        ENERGY_MAX_DEFAULT
        * FISH_BABY_SIZE
        * baby.genome.physical.size_modifier.value
        * STANDARD_MATING_PARENT_ENERGY_CONTRIBUTION
    )
    assert parent.energy == parent_energy_before - expected_contribution
    assert mate.energy == mate_energy_before - expected_contribution
    assert baby.generation == 3
    assert baby.parent_id == parent.fish_id
    assert False in ecosystem.reproductions
    assert ecosystem.mating_attempts == [True]


def test_proximity_mating_requires_local_parent_energy() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()
    parent = _adult_fish(env, ecosystem, x=80, y=80, energy_ratio=0.49)
    mate = _adult_fish(env, ecosystem, x=100, y=80, energy_ratio=1.0)
    parent.genome.behavioral.asexual_reproduction_chance.value = 0.0
    mate.genome.behavioral.asexual_reproduction_chance.value = 0.0
    engine = _MiniEngine([parent, mate], env)
    service = ReproductionService(cast("SimpleNamespace", engine))

    assert not parent.try_mate(mate)
    stats = service.update_frame(1)

    assert stats.proximity_sexual == 0
    assert engine.spawned == []
