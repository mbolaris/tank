"""Multi-generation evolution smoke test.

This test focuses on the end-to-end reproduction pipeline so we can be
confident the core code supports actual life evolution without needing the
full simulation stack. It intentionally uses lightweight engine/environment
stubs so it stays fast while still exercising the real fish and reproduction
components.

Note: All reproduction is now instant (no pregnancy timer). Babies are created
immediately when reproduction conditions are met.
"""

import random
from types import SimpleNamespace
from typing import List

from core.algorithms.energy_management import EnergyConserver
from core.entities import Fish, LifeStage
from core.fish.reproduction_component import ReproductionComponent
from core.reproduction_system import ReproductionSystem
from core.telemetry.events import BirthEvent, ReproductionEvent


class MiniEcosystem:
    """Minimal ecosystem tracker for reproduction tests."""

    def __init__(self) -> None:
        self._next_fish_id = 1
        self.births = []
        self.reproductions = 0
        self.recent_death_rate = 0.0

    def generate_new_fish_id(self) -> int:
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, fish_id, generation, parent_ids=None, algorithm_id=None, color=None):
        self.births.append((fish_id, generation, parent_ids, algorithm_id))

    def record_reproduction(self, algo_id, is_asexual: bool = False):
        self.reproductions += 1

    def record_death(self, *_args, **_kwargs):  # pragma: no cover - not used in this test
        return None

    def record_energy_burn(self, source: str, amount: float) -> None:
        """Stub for energy burn tracking."""
        pass

    def record_energy_gain(self, source: str, amount: float) -> None:
        """Stub for energy gain tracking."""
        pass

    def record_event(self, event) -> None:
        if isinstance(event, BirthEvent):
            self.record_birth(
                event.fish_id,
                event.generation,
                parent_ids=event.parent_ids,
                algorithm_id=event.algorithm_id,
                color=event.color_hex,
            )
            return
        if isinstance(event, ReproductionEvent):
            self.record_reproduction(event.algorithm_id, is_asexual=event.is_asexual)


class MiniEnvironment:
    """Simple environment stub exposing only what Fish requires."""

    def __init__(self, width: int = 200, height: int = 200, seed: int = 42):
        self.width = width
        self.height = height
        self.agents: List[Fish] = []
        self._rng = random.Random(seed)

    @property
    def rng(self) -> random.Random:
        """Deterministic RNG for test reproducibility."""
        return self._rng

    def get_bounds(self):
        return (0.0, 0.0), (float(self.width), float(self.height))

    def nearby_agents_by_type(self, agent: Fish, radius: float, agent_class):
        """Return all other fish; spatial math is unnecessary for this test."""
        return [
            other for other in self.agents if other is not agent and isinstance(other, agent_class)
        ]

    def add_entity(self, entity):
        """Add an entity to the environment."""
        if entity not in self.agents:
            self.agents.append(entity)


class MiniEngine:
    """Engine stub that supports the ReproductionSystem API."""

    def __init__(self, env: MiniEnvironment):
        self.entities_list: List[Fish] = []
        self.environment = env
        self.rng = env.rng
        self.ecosystem = None
        self.config = SimpleNamespace(
            ecosystem=SimpleNamespace(
                emergency_spawn_cooldown=1000,
                critical_population_threshold=1,
                max_population=100,
                spawn_margin_pixels=0,
            ),
            display=SimpleNamespace(
                files={"schooling_fish": ["test_fish"]},
            ),
        )
        from core.reproduction_service import ReproductionService

        self.reproduction_service = ReproductionService(self)
        self.reproduction_system = ReproductionSystem(self)

    def get_all_entities(self):
        return self.entities_list

    def add_entity(self, entity):
        if entity not in self.entities_list:
            self.entities_list.append(entity)
            self.environment.agents = self.entities_list


# Helper utilities ---------------------------------------------------------


def _make_adult_fish(
    env: MiniEnvironment, ecosystem: MiniEcosystem, *, generation: int = 0
) -> Fish:
    fish = Fish(
        environment=env,
        movement_strategy=EnergyConserver(),
        species="test_fish",
        x=50,
        y=50,
        speed=2.0,
        generation=generation,
        ecosystem=ecosystem,
        initial_energy=None,
    )
    # Fast-forward to a reproducing adult with plenty of energy
    fish._lifecycle_component.force_life_stage(LifeStage.ADULT)
    fish._lifecycle_component.age = 200
    # Must also update size to adult size for proper max_energy
    fish._lifecycle_component.size = 1.0  # Adult size
    fish.energy = fish.max_energy
    fish._reproduction_component.reproduction_cooldown = 0
    # Bank enough overflow energy for reproduction (requires 75+ energy for a baby)
    fish._reproduction_component.bank_overflow_energy(80.0, max_bank=fish.max_energy)
    return fish


def _trigger_instant_reproductions(fish_list, env):
    """Trigger asexual reproduction via trait check and collect newborns.

    Since reproduction is now instant, we just call update_reproduction()
    which checks if conditions are met and creates baby immediately.
    """
    newborns = []
    for fish in list(fish_list):
        # Ensure fish is eligible: adult, full energy, has banked overflow
        if fish._lifecycle_component.life_stage != LifeStage.ADULT:
            continue
        if fish.energy < fish.max_energy:
            continue
        if fish._reproduction_component.reproduction_cooldown > 0:
            continue
        if fish._reproduction_component.overflow_energy_bank <= 0:
            continue

        # Call update_reproduction which will trigger instant birth
        baby = fish.update_reproduction()
        if baby is not None:
            baby.register_birth()
            newborns.append(baby)
            fish_list.append(baby)
            env.add_entity(baby)
    return newborns


# Tests --------------------------------------------------------------------


def test_multi_generation_reproduction(monkeypatch):
    """A baby and then a grandbaby should be produced in quick succession."""

    # Force deterministic mating acceptance and offspring placement
    monkeypatch.setattr(random, "random", lambda: 0.0)

    env = MiniEnvironment()
    ecosystem = MiniEcosystem()
    engine = MiniEngine(env)

    # Start with two ready-to-mate adults
    parent_a = _make_adult_fish(env, ecosystem)
    parent_b = _make_adult_fish(env, ecosystem)
    engine.add_entity(parent_a)
    engine.add_entity(parent_b)

    # Generation 1 → 2: Instant reproduction (no pregnancy timer)
    first_generation = _trigger_instant_reproductions(engine.entities_list, env)

    assert first_generation, "Initial parents should produce at least one offspring"
    baby = first_generation[0]
    assert baby.generation == parent_a.generation + 1
    assert ecosystem.births, "Births should be recorded in the ecosystem"

    # Prepare the baby for rapid reproduction with the second parent
    parent_a.energy = parent_a.max_energy * 0.1  # Keep first parent out of the next mating round
    parent_a._reproduction_component.reproduction_cooldown = (
        ReproductionComponent.REPRODUCTION_COOLDOWN
    )

    baby._lifecycle_component.force_life_stage(LifeStage.ADULT)
    baby._lifecycle_component.age = 200
    baby.energy = baby.max_energy
    baby._reproduction_component.reproduction_cooldown = 0
    baby._reproduction_component.bank_overflow_energy(
        baby.max_energy * 0.5, max_bank=baby.max_energy
    )

    parent_b._reproduction_component.reproduction_cooldown = (
        ReproductionComponent.REPRODUCTION_COOLDOWN
    )
    parent_b.energy = parent_b.max_energy * 0.1

    helper = _make_adult_fish(env, ecosystem, generation=baby.generation)
    engine.add_entity(helper)

    # Make sure the baby drives the next reproduction cycle
    engine.entities_list = [baby, helper, parent_a, parent_b]
    env.agents = engine.entities_list

    # Generation 2 → 3: Instant reproduction
    second_generation = _trigger_instant_reproductions(engine.entities_list, env)

    assert second_generation, "Second generation fish should also be able to reproduce"
    grandbaby = second_generation[0]
    assert grandbaby.generation == baby.generation + 1

    # We should now have at least five fish: two parents + helper + baby + grandbaby
    # Additional offspring can appear if full-energy fish trigger asexual reproduction
    assert len(engine.entities_list) >= 5
    assert len(ecosystem.births) >= 2, "Multiple births should be tracked during the cycle"
