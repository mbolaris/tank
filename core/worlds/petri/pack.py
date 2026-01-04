"""Petri world mode pack implementation.

This pack provides the Petri Dish simulation mode, which reuses
Tank-like simulation logic with mode-specific metadata for top-down
microbe visualization.

ARCHITECTURE NOTE: PetriPack inherits from the neutral TankLikePackBase
rather than TankPack. This clean boundary enables Petri to diverge
independently without creating tangled import chains through Tank.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
from core.worlds.petri.dish import PetriDish
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.tank_like_pack_base import TankLikePackBase

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine
    from core.worlds.identity import EntityIdentityProvider

from core.worlds.petri.petri_actions import register_petri_action_translator
from core.worlds.petri.movement_observations import (
    register_petri_movement_observation_builder,
)


class PetriPack(TankLikePackBase):
    """System pack for the Petri Dish simulation.

    Inherits shared Tank-like wiring from TankLikePackBase and provides
    Petri-specific mode_id, metadata, and identity provider.

    Currently uses the same entity types and identity scheme as Tank,
    but can diverge independently for Petri-specific features.
    """

    def __init__(self, config: SimulationConfig):
        super().__init__(config)
        # Use shared Tank-like identity provider from shared namespace
        self._identity_provider = TankLikeEntityIdentityProvider()
        
        # Compute dish geometry from screen dimensions
        display = config.display
        rim_margin = 2.0
        radius = (min(display.screen_width, display.screen_height) / 2) - rim_margin
        self.dish = PetriDish(
            cx=display.screen_width / 2,
            cy=display.screen_height / 2,
            r=radius,
        )

    @property
    def mode_id(self) -> str:
        return "petri"

    def register_contracts(self, engine: "SimulationEngine") -> None:
        """Register Petri-specific contracts."""
        register_petri_action_translator("petri")
        register_petri_movement_observation_builder("petri")

    def get_identity_provider(self) -> "EntityIdentityProvider":
        """Return the Petri identity provider."""
        return self._identity_provider

    def get_metadata(self) -> dict[str, Any]:
        """Return Petri-specific metadata."""
        return {
            "world_type": "petri",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }

    def build_environment(self, engine: "SimulationEngine") -> "EnvironmentLike":
        """Create the Petri environment with circular physics."""
        from core.events import EventBus
        from core.sim.events import AteFood, EnergyBurned, Moved, PokerGamePlayed
        from core.worlds.petri.environment import PetriEnvironment

        # 1. Initialize EventBus for domain events
        engine.event_bus = EventBus()

        # 2. Subscribe EnergyLedger queue to energy events
        engine.event_bus.subscribe(AteFood, engine._queue_sim_event)
        engine.event_bus.subscribe(Moved, engine._queue_sim_event)
        engine.event_bus.subscribe(EnergyBurned, engine._queue_sim_event)
        engine.event_bus.subscribe(PokerGamePlayed, engine._queue_sim_event)

        display = self.config.display

        # 3. Create PetriEnvironment with dish geometry
        env = PetriEnvironment(
            engine._entity_manager.entities_list,
            display.screen_width,
            display.screen_height,
            engine.time_system,
            rng=engine.rng,
            event_bus=engine.event_bus,
            simulation_config=self.config,
            dish=self.dish,
        )
        env.set_spawn_requester(engine.request_spawn)
        env.set_remove_requester(engine.request_remove)

        # 4. Expose code_pool on engine for backward compatibility
        engine.code_pool = env.code_pool

        # 5. Set world type for contract awareness
        env.world_type = self.mode_id

        return env

    def register_systems(self, engine: "SimulationEngine") -> None:
        """Register Petri-specific systems."""
        from core.ecosystem import EcosystemManager
        from core.plant_manager import PlantManager
        from core.worlds.petri.root_spots import CircularRootSpotManager
        from core.worlds.petri.systems import PetriFoodSpawningSystem

        eco_config = self.config.ecosystem

        # 1. Initialize EcosystemManager
        engine.ecosystem = EcosystemManager(
            max_population=eco_config.max_population,
            event_bus=engine.event_bus,
        )

        # 2. Initialize PlantManager with CircularRootSpotManager
        # In Petri mode, we use circular spots
        if self.config.server.plants_enabled:
            # Calculate spot count based on circumference? 
            # Or just use config default. Standard screen with ~20 spots.
            # 2 * pi * R / spacing?
            # Let's stick to config default count for now or hardcode reasonable number.
            # But RootSpotManager takes just screen dims usually. 
            # CircularRootSpotManager will handle initialization logic if we just pass it.
            # But PlantManager needs an INSTANCE.
            
            root_spot_manager = CircularRootSpotManager(
                dish=self.dish,
                rng=engine.rng,
            )
            
            engine.plant_manager = PlantManager(
                environment=engine.environment,
                ecosystem=engine.ecosystem,
                entity_adder=engine,
                rng=engine.rng,
                root_spot_manager=root_spot_manager,
            )

        # 3. Initialize PetriFoodSpawningSystem
        engine.food_spawning_system = PetriFoodSpawningSystem(
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

    # NOTE: We do NOT override seed_entities because:
    # 1. The parent class's implementation correctly creates fish via engine.create_initial_entities()
    # 2. Our circular boundary physics (PetriEnvironment.resolve_boundary_collision) will
    #    push any fish spawned outside the dish back inside on subsequent frames.
    # 3. The circular dish geometry is cosmetic and enforced by physics, not spawn positions.
