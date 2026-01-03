"""Tank world mode pack implementation.

This pack encapsulates the specific systems, environment, and entity seeding
logic for the standard fish tank simulation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core import environment
from core.config.simulation_config import SimulationConfig
from core.worlds.system_pack import EnvironmentLike, SystemPack
from core.worlds.tank.identity import TankEntityIdentityProvider

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class TankPack(SystemPack):
    """System pack for the standard Fish Tank simulation."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self._identity_provider = TankEntityIdentityProvider()

    @property
    def mode_id(self) -> str:
        return "tank"

    def get_identity_provider(self):
        """Return the Tank identity provider."""
        return self._identity_provider

    def build_core_systems(self, engine: SimulationEngine) -> dict[str, Any]:
        """Build Tank-specific core systems."""
        from core.collision_system import CollisionSystem
        from core.poker_system import PokerSystem
        from core.reproduction_service import ReproductionService
        from core.reproduction_system import ReproductionSystem
        from core.systems.entity_lifecycle import EntityLifecycleSystem
        from core.systems.poker_proximity import PokerProximitySystem

        systems = {}
        systems["lifecycle_system"] = EntityLifecycleSystem(engine)
        systems["collision_system"] = CollisionSystem(engine)
        
        # Wiring service manually before system to resolve circular dependency
        service = ReproductionService(engine)
        engine.reproduction_service = service
        systems["reproduction_service"] = service
        systems["reproduction_system"] = ReproductionSystem(engine)

        poker = PokerSystem(engine, max_events=self.config.poker.max_poker_events)
        poker.enabled = self.config.server.poker_activity_enabled
        systems["poker_system"] = poker
        systems["poker_events"] = poker.poker_events
        systems["poker_proximity_system"] = PokerProximitySystem(engine)

        if self.config.poker.enable_periodic_benchmarks:
            from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator

            systems["benchmark_evaluator"] = PeriodicBenchmarkEvaluator(
                self.config.poker.benchmark_config
            )

        return systems

    def build_environment(self, engine: SimulationEngine) -> EnvironmentLike:
        """Create the Tank environment with EventBus and GenomeCodePool."""
        from core.events import EventBus
        from core.sim.events import AteFood, EnergyBurned, Moved, PokerGamePlayed

        # 1. Initialize EventBus for domain events
        engine.event_bus = EventBus()

        # 2. Subscribe EnergyLedger queue to energy events
        engine.event_bus.subscribe(AteFood, engine._queue_sim_event)
        engine.event_bus.subscribe(Moved, engine._queue_sim_event)
        engine.event_bus.subscribe(EnergyBurned, engine._queue_sim_event)
        engine.event_bus.subscribe(PokerGamePlayed, engine._queue_sim_event)

        display = self.config.display

        # 3. Create standard Tank environment
        # Note: Not passing code_pool so Environment creates GenomeCodePool
        env = environment.Environment(
            engine._entity_manager.entities_list,
            display.screen_width,
            display.screen_height,
            engine.time_system,
            rng=engine.rng,
            event_bus=engine.event_bus,
            # Don't pass code_pool - let Environment create GenomeCodePool
            simulation_config=self.config,
        )
        env.set_spawn_requester(engine.request_spawn)
        env.set_remove_requester(engine.request_remove)

        # 4. Expose code_pool on engine for backward compatibility
        engine.code_pool = env.code_pool

        return env

    def register_systems(self, engine: SimulationEngine) -> None:
        """Register Tank-specific systems in the correct order."""
        from core.ecosystem import EcosystemManager
        from core.plant_manager import PlantManager
        from core.systems.food_spawning import FoodSpawningSystem

        eco_config = self.config.ecosystem

        # 1. Initialize EcosystemManager
        engine.ecosystem = EcosystemManager(
            max_population=eco_config.max_population,
            event_bus=engine.event_bus,
        )

        # 2. Initialize PlantManager
        if self.config.server.plants_enabled:
            engine.plant_manager = PlantManager(
                environment=engine.environment,
                ecosystem=engine.ecosystem,
                entity_adder=engine,
                rng=engine.rng,
            )

        # 3. Initialize FoodSpawningSystem
        engine.food_spawning_system = FoodSpawningSystem(
            engine,
            rng=engine.rng,
            spawn_rate_config=engine._build_spawn_rate_config(),
            auto_food_enabled=self.config.food.auto_food_enabled,
            display_config=self.config.display,
        )

        # 4. Register systems in execution order
        engine._system_registry.register(engine.lifecycle_system)
        engine._system_registry.register(engine.time_system)
        engine._system_registry.register(engine.food_spawning_system)
        engine._system_registry.register(engine.collision_system)
        engine._system_registry.register(engine.poker_proximity_system)
        engine._system_registry.register(engine.reproduction_system)
        engine._system_registry.register(engine.poker_system)

    def seed_entities(self, engine: SimulationEngine) -> None:
        """Create initial entities for the Tank."""
        # 1. Create initial biological population (fish)
        engine.create_initial_entities()

        # 2. Create initial fractal plants
        if engine.plant_manager is not None:
            engine._block_root_spots_with_obstacles()
            engine.plant_manager.create_initial_plants(engine._entity_manager.entities_list)
            engine._apply_entity_mutations("setup_plants")

    def get_metadata(self) -> dict[str, Any]:
        """Return Tank-specific metadata."""
        return {
            "world_type": "tank",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }

    def get_pipeline(self):
        """Return None to use the default pipeline.

        Tank uses the canonical default pipeline that exactly reproduces
        the hard-coded phase order originally in SimulationEngine.update().
        """
        return None
