"""Tests for Fair-Start Birth Energy mechanics."""

from __future__ import annotations

from typing import Any, cast

from core.reproduction.reproduction_service import ReproductionService
from tests.test_proximity_mating import (
    _adult_fish,
    _MiniEcosystem,
    _MiniEngine,
    _MiniEnvironment,
)


def test_fair_start_energy_decoupling() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()

    # Create parents with non-default size modifiers (e.g. 2.0 and 0.5)
    parent = _adult_fish(env, ecosystem, x=80, y=80, energy_ratio=1.0)
    parent.genome.physical.size_modifier.value = 2.0
    parent.energy = parent.max_energy

    mate = _adult_fish(env, ecosystem, x=100, y=80, energy_ratio=1.0)
    mate.genome.physical.size_modifier.value = 0.5
    mate.energy = mate.max_energy

    engine = _MiniEngine([parent, mate], env)
    service = ReproductionService(cast(Any, engine))

    parent_energy_before = parent.energy
    mate_energy_before = mate.energy

    assert parent.try_mate(mate)
    stats = service.update_frame(1)

    assert stats.proximity_sexual == 1
    assert len(engine.spawned) == 1
    baby = engine.spawned[0]

    # Standard energy cost is ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * 1.0 = 75.0
    # Parent/mate contribution is 75.0 * 0.5 = 37.5
    expected_contribution = 150.0 * 0.5 * 1.0 * 0.50  # 37.5

    assert parent.energy == parent_energy_before - expected_contribution
    assert mate.energy == mate_energy_before - expected_contribution

    # Baby starting energy must be exactly 75.0 (independent of size modifier)
    assert baby._initial_energy_transferred == 75.0
    assert baby._energy_component.energy == 75.0
