from __future__ import annotations

import math
from typing import List, Tuple


class _EnvironmentStub:
    def __init__(self) -> None:
        self.added: List[object] = []

    def add_entity(self, entity: object) -> None:
        self.added.append(entity)

    def get_bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return default environment bounds."""
        return ((0.0, 0.0), (500.0, 500.0))


class _ReproductionManagerStub:
    def record_reproduction_attempt(self, success: bool) -> None:
        pass


class _EcosystemStub:
    def __init__(self) -> None:
        self.burns: List[Tuple[str, float]] = []
        self.reproduction_manager = _ReproductionManagerStub()
        self._next_fish_id = 100

    def record_energy_burn(self, category: str, amount: float) -> None:
        self.burns.append((category, float(amount)))

    def record_reproduction_energy(self, *args, **kwargs) -> None:
        """Stub method for recording reproduction energy."""
        pass

    def get_next_fish_id(self) -> int:
        """Return next available fish ID."""
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_reproduction(self, *args, **kwargs) -> None:
        """Stub method for recording reproduction."""
        pass

    def record_birth(self, *args, **kwargs) -> None:
        """Stub method for recording birth."""
        pass

    def record_death(self, *args, **kwargs) -> None:
        """Stub method for recording death."""
        pass

    def record_consumption(self, *args, **kwargs) -> None:
        """Stub method for recording consumption."""
        pass


def _make_fish(env, fish_id: int, ecosystem):
    from core.entities import Fish
    from core.genetics import Genome
    from core.movement_strategy import AlgorithmicMovement

    # use_algorithm=True creates a composable_behavior automatically
    genome = Genome.random(use_algorithm=True)

    return Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100 + fish_id * 10,
        y=100 + fish_id * 10,
        speed=2.0,
        genome=genome,
        generation=1,
        fish_id=fish_id,
        ecosystem=ecosystem,
    )


def _set_adult(fish) -> None:
    from core.constants import LIFE_STAGE_JUVENILE_MAX

    fish._lifecycle_component.age = LIFE_STAGE_JUVENILE_MAX
    fish._lifecycle_component.update_life_stage()


def test_overflow_prefers_reproduction_bank_over_food(simulation_env):
    _unused_env, _agents_wrapper = simulation_env
    env = _EnvironmentStub()
    eco = _EcosystemStub()

    fish = _make_fish(env, fish_id=1, ecosystem=eco)
    _set_adult(fish)
    fish.energy = fish.max_energy

    entities_before = len(env.added)
    fish.modify_energy(50.0)
    entities_after = len(env.added)

    assert math.isclose(fish._reproduction_component.overflow_energy_bank, 50.0, rel_tol=0, abs_tol=1e-9)
    assert any(k == "overflow_reproduction" and math.isclose(v, 50.0, rel_tol=0, abs_tol=1e-9) for k, v in eco.burns)
    assert not any(k == "overflow_food" for k, _v in eco.burns)
    assert entities_after == entities_before


def test_overflow_spills_to_food_when_bank_is_full(simulation_env):
    _unused_env, _agents_wrapper = simulation_env
    env = _EnvironmentStub()
    eco = _EcosystemStub()

    fish = _make_fish(env, fish_id=1, ecosystem=eco)
    _set_adult(fish)
    fish.energy = fish.max_energy

    from core.constants import OVERFLOW_ENERGY_BANK_MULTIPLIER

    max_bank = fish.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
    fish._reproduction_component.overflow_energy_bank = max_bank - 10.0

    entities_before = len(env.added)
    fish.modify_energy(50.0)  # should bank 10, spill 40
    entities_after = len(env.added)

    assert math.isclose(fish._reproduction_component.overflow_energy_bank, max_bank, rel_tol=0, abs_tol=1e-9)
    assert any(k == "overflow_reproduction" and math.isclose(v, 10.0, rel_tol=0, abs_tol=1e-9) for k, v in eco.burns)
    assert any(k == "overflow_food" and math.isclose(v, 40.0, rel_tol=0, abs_tol=1e-6) for k, v in eco.burns)
    assert entities_after == entities_before + 1
