"""Runtime and wiring helpers for the simulation engine.

This module centralizes construction of deterministic simulation context
objects and system registration. It keeps ``SimulationEngine`` focused on
per-frame coordination while allowing tests to inject lightweight system
registries.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Optional

from core.cache_manager import CacheManager
from core.collision_system import CollisionSystem
from core.config.poker import MAX_POKER_EVENTS
from core.events import EventBus
from core.object_pool import FoodPool
from core.poker_system import PokerSystem
from core.reproduction_system import ReproductionSystem
from core.systems.base import BaseSystem
from core.systems.entity_lifecycle import EntityLifecycleSystem
from core.systems.food_spawning import FoodSpawningSystem
from core.time_system import TimeSystem
from core.update_phases import UpdatePhase


@dataclass
class SimulationRuntimeConfig:
    """Config bundle used by ``SimulationRuntime``."""

    headless: bool = True
    rng: Optional[random.Random] = None
    seed: Optional[int] = None
    enable_poker_benchmarks: bool = False

    def resolve_rng(self) -> tuple[random.Random, Optional[int]]:
        """Return a deterministic RNG based on supplied values."""
        if self.rng is not None:
            return self.rng, None
        if self.seed is not None:
            return random.Random(self.seed), self.seed
        return random.Random(), None


@dataclass
class SimulationContext:
    """Container for deterministic, shared simulation state."""

    rng: random.Random
    event_bus: EventBus
    cache_manager: CacheManager
    food_pool: FoodPool


class SystemRegistry:
    """Registers systems in a consistent order.

    The registry is also used in tests to supply stub systems and short-circuit
    the normal engine update loop.
    """

    def __init__(
        self,
        engine: "SimulationEngine",
        context: SimulationContext,
        config: SimulationRuntimeConfig,
    ) -> None:
        self.engine = engine
        self.context = context
        self.config = config
        self.systems: List[BaseSystem] = []

    def build_default_systems(self) -> None:
        """Create and register the default simulation systems."""
        self.engine.lifecycle_system = EntityLifecycleSystem(self.engine, context=self.context)
        self.engine.time_system = TimeSystem(self.engine, context=self.context)
        self.engine.food_spawning_system = FoodSpawningSystem(
            self.engine,
            context=self.context,
            rng=self.context.rng,
            config=getattr(self.engine, "food_spawn_config", None),
            auto_food_enabled=getattr(self.engine, "auto_food_enabled", None),
            screen_width=getattr(self.engine, "_display_width", None),
            screen_height=getattr(self.engine, "_display_height", None),
        )
        self.engine.collision_system = CollisionSystem(self.engine, context=self.context)
        self.engine.reproduction_system = ReproductionSystem(self.engine, context=self.context)
        max_events = getattr(self.engine, "poker_max_events", MAX_POKER_EVENTS)
        self.engine.poker_system = PokerSystem(self.engine, max_events=max_events, context=self.context)
        self.engine.poker_events = self.engine.poker_system.poker_events

        self.systems = [
            self.engine.lifecycle_system,
            self.engine.time_system,
            self.engine.food_spawning_system,
            self.engine.collision_system,
            self.engine.reproduction_system,
            self.engine.poker_system,
        ]

    @property
    def should_run_registered_systems(self) -> bool:
        """Return True when the registry wants to drive system execution."""
        return False

    def run_registered_systems(self, frame: int) -> None:
        """Run systems in the order they were registered."""
        for system in self.systems:
            system.update(frame)

    def get_systems_in_phase(self, phase: UpdatePhase) -> List[BaseSystem]:
        """Get systems that declare a matching update phase."""
        return [s for s in self.systems if getattr(s, "phase", None) == phase]


class SimulationRuntime:
    """Creates deterministic context and wires systems into the engine."""

    def __init__(
        self,
        config: Optional[SimulationRuntimeConfig] = None,
        registry_factory: Optional[
            Callable[["SimulationEngine", SimulationContext, SimulationRuntimeConfig], SystemRegistry]
        ] = None,
    ) -> None:
        self.config = config or SimulationRuntimeConfig()
        self._registry_factory = registry_factory
        self._resolved_rng: Optional[random.Random] = None
        self._resolved_seed: Optional[int] = None

    def resolve_rng(self, override: Optional[random.Random] = None) -> tuple[random.Random, Optional[int]]:
        """Resolve and cache the RNG/seed for consistent reuse.

        Args:
            override: Optional RNG to force as the shared instance.

        Returns:
            Tuple of (rng, seed_used)
        """
        if override is not None:
            self._resolved_rng = override
            self._resolved_seed = None
            return override, None

        if self._resolved_rng is None:
            self._resolved_rng, self._resolved_seed = self.config.resolve_rng()

        return self._resolved_rng, self._resolved_seed

    def build_context(self, entity_provider, rng: Optional[random.Random] = None) -> SimulationContext:
        resolved_rng, _ = self.resolve_rng(override=rng)
        cache_manager = CacheManager(entity_provider)
        return SimulationContext(
            rng=resolved_rng,
            event_bus=EventBus(),
            cache_manager=cache_manager,
            food_pool=FoodPool(rng=resolved_rng),
        )

    def create_registry(
        self,
        engine: "SimulationEngine",
        context: SimulationContext,
    ) -> SystemRegistry:
        if self._registry_factory:
            return self._registry_factory(engine, context, self.config)
        registry = SystemRegistry(engine, context, self.config)
        registry.build_default_systems()
        return registry
