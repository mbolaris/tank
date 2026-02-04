"""Pure simulation engine - the slim orchestrator.

This module provides the core simulation loop without any embedded logic.
It coordinates systems and managers but delegates all actual work.

Design Decisions:
-----------------
1. The engine is a COORDINATOR, not a DOER. It owns managers and systems
   but doesn't contain business logic inline.

2. Entity management is delegated to EntityManager.
   System management is delegated to SystemRegistry.
   Stats calculation is delegated to StatsCalculator.

3. The update() method runs phases in order, delegating to systems.
   Phase order is explicit and documented in UpdatePhase.

4. Executive logic (Systems wiring and mutation handling) is delegated to
   SystemCoordinator and MutationTransaction.
"""

from __future__ import annotations

import logging
import os
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from core.config.simulation_config import SimulationConfig
from core.simulation import diagnostics
from core.simulation.coordinator import SystemCoordinator
from core.simulation.entity_manager import EntityManager
from core.simulation.mutation import MutationTransaction
from core.simulation.system_registry import SystemRegistry
from core.systems.base import BaseSystem
from core.time_system import TimeSystem
from core.update_phases import PHASE_DESCRIPTIONS, UpdatePhase

if TYPE_CHECKING:
    from core import entities, environment
    from core.collision_system import CollisionSystem
    from core.ecosystem import EcosystemManager
    from core.minigames.soccer.evaluator import SoccerMinigameOutcome
    from core.plant_manager import PlantManager
    from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
    from core.poker_interaction import PokerInteraction
    from core.poker_system import PokerSystem
    from core.reproduction_service import ReproductionService
    from core.reproduction_system import ReproductionSystem
    from core.root_spots import RootSpotManager
    from core.systems.entity_lifecycle import EntityLifecycleSystem
    from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig
    from core.systems.poker_proximity import PokerProximitySystem
    from core.systems.soccer_system import SoccerSystem
    from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest
    from core.worlds.system_pack import SystemPack

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameOutputs:
    spawns: list[SpawnRequest]
    removals: list[RemovalRequest]
    energy_deltas: list[EnergyDeltaRecord]


class PackableEngine(Protocol):
    """Minimal interface that a SystemPack expects from the engine."""

    config: SimulationConfig
    rng: random.Random
    event_bus: Any
    genome_code_pool: Any
    environment: environment.Environment | None
    ecosystem: EcosystemManager | None
    plant_manager: PlantManager | None
    food_spawning_system: FoodSpawningSystem | None
    time_system: TimeSystem
    lifecycle_system: EntityLifecycleSystem
    collision_system: CollisionSystem
    reproduction_system: ReproductionSystem
    poker_system: PokerSystem
    poker_proximity_system: PokerProximitySystem
    soccer_system: SoccerSystem | None

    def request_spawn(self, entity: Any, **kwargs: Any) -> bool: ...

    def request_remove(self, entity: Any, **kwargs: Any) -> bool: ...

    def _apply_entity_mutations(self, stage: str) -> None: ...

    def create_initial_entities(self) -> None: ...

    def _block_root_spots_with_obstacles(self) -> None: ...

    def _build_spawn_rate_config(self) -> SpawnRateConfig: ...


class SimulationEngine:
    """A headless simulation engine for the fish tank ecosystem.

    Refactored to delegate logic to SystemCoordinator and MutationTransaction.
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
        *,
        headless: bool | None = None,
        rng: random.Random | None = None,
        seed: int | None = None,
        enable_poker_benchmarks: bool | None = None,
    ) -> None:
        """Initialize the simulation engine."""
        self.frame_count: int = 0
        self.paused: bool = False
        self.config = config or SimulationConfig.production(headless=True)
        if headless is not None:
            self.config = self.config.with_overrides(headless=headless)
        if enable_poker_benchmarks is not None:
            poker_config = self.config.poker
            poker_config.enable_periodic_benchmarks = enable_poker_benchmarks
            self.config.poker = poker_config
        self.config.validate()
        self.headless = self.config.headless

        # RNG handling
        if rng is not None:
            self.rng: random.Random = rng
            self.seed = seed
        elif seed is not None:
            self.rng = random.Random(seed)
            self.seed = seed
        else:
            self.rng = random.Random()
            self.seed = None

        self.run_id: str = str(uuid.uuid4())
        logger.info(f"SimulationEngine initialized with run_id={self.run_id}")

        # Visualization hint
        self.view_mode: str = "side"

        # Optional wiring points populated by SystemPacks (typed for mypy)
        self.event_bus: Any | None = None
        self.genome_code_pool: Any | None = None

        # Components (delegated to managers)
        self._entity_manager = EntityManager(
            rng=self.rng,
            get_environment=lambda: self.environment,
            get_ecosystem=lambda: self.ecosystem,
            get_root_spot_manager=lambda: self.root_spot_manager,
        )

        from core.agents_wrapper import AgentsWrapper

        self.agents = AgentsWrapper(self)
        self._system_registry = SystemRegistry()

        # New modular components
        self.coordinator = SystemCoordinator()
        self.mutations = MutationTransaction()

        # Core state
        self.environment: environment.Environment | None = None
        self.ecosystem: EcosystemManager | None = None
        self.time_system: TimeSystem = TimeSystem(self)
        self.start_time: float = time.time()

        # Services
        from core.services.stats.calculator import StatsCalculator

        self.stats_calculator = StatsCalculator(self)

        # Systems - these will be optionally initialized by the SystemPack in setup()
        # but we keep them as Optional attributes for type safety.
        # Note: They are also registered with self.coordinator in setup()
        self.collision_system: CollisionSystem | None = None
        self.reproduction_service: ReproductionService | None = None
        self.reproduction_system: ReproductionSystem | None = None
        self.poker_system: PokerSystem | None = None
        self.soccer_system: SoccerSystem | None = None
        self.lifecycle_system: EntityLifecycleSystem | None = None
        self.poker_proximity_system: PokerProximitySystem | None = None
        self.food_spawning_system: FoodSpawningSystem | None = None
        self.plant_manager: PlantManager | None = None
        self.poker_events: deque[Any] = deque(maxlen=self.config.poker.max_poker_events)
        self._soccer_events: deque[Any] = deque(maxlen=self.config.soccer.max_events)
        self._soccer_league_live: dict[str, Any] | None = None

        # Periodic poker benchmark evaluation
        self.benchmark_evaluator: PeriodicBenchmarkEvaluator | None = None

        # Phase tracking for debugging
        self._current_phase: UpdatePhase | None = None
        # Enable via config OR env var (for tests to force invariant checking)
        self._phase_debug_enabled: bool = (
            self.config.enable_phase_debug
            or os.environ.get("TANK_ENFORCE_MUTATION_INVARIANTS", "0") == "1"
        )

        # Delta log (reset every frame)

        self._frame_spawns: list[SpawnRequest] = []
        self._frame_removals: list[RemovalRequest] = []
        self._frame_energy_deltas: list[EnergyDeltaRecord] = []

        # Pipeline (set during setup())
        from core.simulation.pipeline import EnginePipeline

        self.pipeline: EnginePipeline | None = None

        # Identity provider for stable delta IDs (set during setup())
        from core.worlds.identity import EntityIdentityProvider

        self._identity_provider: EntityIdentityProvider | None = None

        # Phase hooks for mode-specific entity handling (set during setup())
        from core.simulation.phase_hooks import NoOpPhaseHooks, PhaseHooks

        self._phase_hooks: PhaseHooks = NoOpPhaseHooks()
        self.coordinator.set_phase_hooks(self._phase_hooks)

    def drain_frame_outputs(self) -> FrameOutputs:
        """Return this frame's outputs and clear internal buffers."""
        outputs = FrameOutputs(
            spawns=list(self._frame_spawns),
            removals=list(self._frame_removals),
            energy_deltas=list(self._frame_energy_deltas),
        )
        self._frame_spawns.clear()
        self._frame_removals.clear()
        self._frame_energy_deltas.clear()
        return outputs

    # =========================================================================
    # Compatibility Properties
    # =========================================================================

    @property
    def entities_list(self) -> list[entities.Agent]:
        """All entities in the simulation (delegates to EntityManager)."""
        return self._entity_manager.entities_list

    @property
    def food_pool(self):
        """Food object pool (delegates to EntityManager)."""
        return self._entity_manager.food_pool

    @property
    def root_spot_manager(self) -> RootSpotManager | None:
        """Access to root spot manager via PlantManager."""
        if self.plant_manager is None:
            return None
        return self.plant_manager.root_spot_manager

    def get_fish_list(self) -> list[entities.Fish]:
        """Get list of all fish (compatibility method)."""
        return self._entity_manager.get_fish()

    def get_food_list(self) -> list[entities.Food]:
        """Get list of all food (compatibility method)."""
        return self._entity_manager.get_food()

    def cleanup_dying_fish(self) -> None:
        """Remove dying fish (compatibility method)."""
        if self.lifecycle_system:
            self.lifecycle_system.cleanup_dying_fish()

    def record_fish_death(self, fish: entities.Fish, cause: str | None = None) -> None:
        """Record fish death (compatibility method)."""
        if self.lifecycle_system:
            self.lifecycle_system.record_fish_death(fish, cause)

    # Expose mutation queue for tests that access private member
    @property
    def _entity_mutations(self):
        return self.mutations._queue

    # =========================================================================
    # Setup
    # =========================================================================

    def setup(self, pack: SystemPack | None = None) -> None:
        """Setup the simulation using the provided SystemPack."""
        # Fallback to TankPack if no pack provided
        if pack is None:
            from core.worlds.tank.pack import TankPack

            pack = TankPack(self.config)

        # 1. Let the pack build core systems (wiring them into self for compatibility)
        systems = pack.build_core_systems(self)
        for attr, system in systems.items():
            setattr(self, attr, system)

        # Wire systems into coordinator
        self.coordinator.collision_system = self.collision_system
        self.coordinator.reproduction_service = self.reproduction_service
        self.coordinator.reproduction_system = self.reproduction_system
        self.coordinator.poker_system = self.poker_system
        self.coordinator.lifecycle_system = self.lifecycle_system
        self.coordinator.poker_proximity_system = self.poker_proximity_system
        self.coordinator.food_spawning_system = self.food_spawning_system
        self.coordinator.plant_manager = self.plant_manager

        # 2. Let the pack build the environment
        from core.environment import Environment

        self.environment = cast(Environment, pack.build_environment(self))

        # Wire up energy delta recorder for immediate tracking
        if self.environment and hasattr(self.environment, "set_energy_delta_recorder"):
            self.environment.set_energy_delta_recorder(self._create_energy_recorder())

        # 3. Let the pack register systems
        pack.register_systems(self)
        if hasattr(pack, "register_contracts"):
            pack.register_contracts(self)
        self._validate_system_phase_declarations()
        self._assert_required_systems()

        # 4. Wire up the pipeline (pack can override or use default)
        from core.simulation.pipeline import default_pipeline

        custom_pipeline = pack.get_pipeline() if hasattr(pack, "get_pipeline") else None
        self.pipeline = custom_pipeline if custom_pipeline is not None else default_pipeline()

        # 5. Let the pack seed entities
        pack.seed_entities(self)

        # 6. Store identity provider from pack
        if hasattr(pack, "get_identity_provider"):
            self._identity_provider = pack.get_identity_provider()

        # 7. Store phase hooks from pack
        from core.simulation.phase_hooks import NoOpPhaseHooks

        if hasattr(pack, "get_phase_hooks"):
            hooks = pack.get_phase_hooks()
            self._phase_hooks = hooks if hooks is not None else NoOpPhaseHooks()
        else:
            self._phase_hooks = NoOpPhaseHooks()

        # Update coordinator hooks
        self.coordinator.set_phase_hooks(self._phase_hooks)

        # 8. Finalize setup: apply any queued mutations
        self._apply_entity_mutations("setup_finalize", record_outputs=False)
        if self._entity_manager.is_dirty:
            self._rebuild_caches()

    def _assert_required_systems(self) -> None:
        """Fail fast if core systems were not wired by the SystemPack."""
        required = {
            "lifecycle_system": self.lifecycle_system,
            "collision_system": self.collision_system,
            "poker_proximity_system": self.poker_proximity_system,
            "poker_system": self.poker_system,
            "reproduction_system": self.reproduction_system,
        }
        missing = [name for name, system in required.items() if system is None]
        if missing:
            raise AssertionError(f"SystemPack did not initialize required systems: {missing}")

    def _build_spawn_rate_config(self) -> SpawnRateConfig:
        """Translate SimulationConfig food settings into SpawnRateConfig."""
        from core.systems.food_spawning import SpawnRateConfig

        food_cfg = self.config.food
        return SpawnRateConfig(
            base_rate=food_cfg.spawn_rate,
            ultra_low_energy_threshold=food_cfg.ultra_low_energy_threshold,
            low_energy_threshold=food_cfg.low_energy_threshold,
            high_energy_threshold_1=food_cfg.high_energy_threshold_1,
            high_energy_threshold_2=food_cfg.high_energy_threshold_2,
            high_pop_threshold_1=food_cfg.high_pop_threshold_1,
            high_pop_threshold_2=food_cfg.high_pop_threshold_2,
            live_food_chance=food_cfg.live_food_chance,
        )

    def _validate_system_phase_declarations(self) -> None:
        """Verify phase metadata matches the explicit phase loop."""
        phase_map: dict[UpdatePhase, list[Any]] = {
            UpdatePhase.FRAME_START: [self.lifecycle_system],
            UpdatePhase.TIME_UPDATE: [self.time_system],
            UpdatePhase.SPAWN: [self.food_spawning_system],
            UpdatePhase.COLLISION: [self.collision_system],
            UpdatePhase.INTERACTION: [self.poker_proximity_system, self.poker_system],
            UpdatePhase.REPRODUCTION: [self.reproduction_system],
        }

        executed_systems = set()
        for phase, systems in phase_map.items():
            for system in systems:
                if system is None:
                    continue
                executed_systems.add(system)
                declared_phase = system.phase
                if declared_phase is None:
                    continue
                if declared_phase != phase:
                    logger.warning(
                        "System %s declares phase %s but runs in %s",
                        system.name,
                        declared_phase.name,
                        phase.name,
                    )

        for system in self._system_registry.get_all():
            declared_phase = system.phase
            if declared_phase is None:
                continue
            if system not in executed_systems:
                logger.warning(
                    "System %s declares phase %s but is not scheduled in the explicit phase loop",
                    system.name,
                    declared_phase.name,
                )

    # =========================================================================
    # System Registry Methods (delegate to SystemRegistry)
    # =========================================================================

    def get_systems(self) -> list[BaseSystem]:
        """Get all registered systems in execution order."""
        return self._system_registry.get_all()

    @property
    def _systems(self) -> list[BaseSystem]:
        """Access to systems list."""
        return self._system_registry.get_all()

    def get_system(self, name: str) -> BaseSystem | None:
        """Get a system by name."""
        return self._system_registry.get(name)

    def get_systems_debug_info(self) -> dict[str, Any]:
        """Get debug information from all registered systems."""
        return self._system_registry.get_debug_info()

    def set_system_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a system by name."""
        return self._system_registry.set_enabled(name, enabled)

    # =========================================================================
    # Phase Tracking
    # =========================================================================

    def get_current_phase(self) -> UpdatePhase | None:
        """Get the current update phase (None if not in update loop)."""
        return self._current_phase

    def get_phase_description(self, phase: UpdatePhase | None = None) -> str:
        """Get a human-readable description of a phase."""
        if phase is None:
            phase = self._current_phase
        if phase is None:
            return "Not in update loop"
        return PHASE_DESCRIPTIONS.get(phase, phase.name)

    # =========================================================================
    # Entity Management (delegate to EntityManager)
    # =========================================================================

    def create_initial_entities(self) -> None:
        """Create initial entities in the simulation."""
        if self.environment is None or self.ecosystem is None:
            return

        from core.entity_factory import create_initial_population

        display = self.config.display
        population = create_initial_population(
            self.environment,
            self.ecosystem,
            display_config=display,
            ecosystem_config=self.config.ecosystem,
            rng=self.rng,
        )
        for entity in population:
            self.agents.add(entity)

    def _block_root_spots_with_obstacles(self) -> None:
        """Prevent plants from spawning where static obstacles live."""
        if self.plant_manager is None:
            return
        for entity in self._entity_manager.entities_list:
            self.plant_manager.block_spots_for_entity(entity)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_all_entities(self) -> list[entities.Agent]:
        """Get all entities in the simulation."""
        return self._entity_manager.entities_list

    def _add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation (INTERNAL USE ONLY)."""
        if hasattr(entity, "add_internal"):
            entity.add_internal(self.agents)
        self._entity_manager.add(entity)

    def _remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation (INTERNAL USE ONLY)."""
        self._entity_manager.remove(entity)

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation (PRIVILEGED API)."""
        if self._current_phase is not None:
            raise RuntimeError(
                f"Unsafe call to add_entity during phase {self._current_phase}. "
                "Use request_spawn() instead."
            )
        self._add_entity(entity)

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation (PRIVILEGED API)."""
        if self._current_phase is not None:
            raise RuntimeError(
                f"Unsafe call to remove_entity during phase {self._current_phase}. "
                "Use request_remove() instead."
            )
        self._remove_entity(entity)

    def request_spawn(
        self,
        entity: entities.Agent,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Queue a spawn request to be applied by the engine."""
        return self.mutations.request_spawn(entity, reason=reason, metadata=metadata)

    def request_remove(
        self,
        entity: entities.Agent,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Queue a removal request to be applied by the engine."""
        return self.mutations.request_remove(entity, reason=reason, metadata=metadata)

    def is_pending_removal(self, entity: entities.Agent) -> bool:
        """Check if an entity is queued for removal."""
        return self.mutations.is_pending_removal(entity)

    def _apply_entity_mutations(self, stage: str, *, record_outputs: bool = True) -> None:
        """Apply queued spawns/removals at a safe point in the frame."""
        # Use MutationTransaction to commit changes
        self.mutations.commit(
            self._entity_manager,
            self._frame_spawns if record_outputs else None,
            self._frame_removals if record_outputs else None,
            self._identity_provider,
            pre_add_callback=lambda e: (
                e.add_internal(self.agents) if hasattr(e, "add_internal") else None
            ),
        )

    def _rebuild_caches(self) -> None:
        """Trigger cache rebuilds on environment and entity manager."""
        if self.environment:
            self.environment.rebuild_spatial_grid()
        self._entity_manager.rebuild_caches_if_needed()

    # =========================================================================
    # Update Loop (Coordinated via SystemCoordinator)
    # =========================================================================

    def update(self) -> None:
        """Update the state of the simulation.

        This method coordinates the phases of the simulation update loop
        using the configured Pipeline and SystemCoordinator.
        """
        if self.pipeline is None:
            return  # Should not happen if setup() was called

        # Delegate execution to the pipeline
        self.pipeline.run(self)

    # -------------------------------------------------------------------------
    # Phase Implementations (Called by Pipeline, Delegated to Coordinator)
    # -------------------------------------------------------------------------

    def _phase_frame_start(self) -> None:
        """FRAME_START: Reset counters, increment frame."""
        self._current_phase = UpdatePhase.FRAME_START
        self.frame_count += 1

        # Clear frame output buffers from previous frame
        self._frame_spawns.clear()
        self._frame_removals.clear()
        self._frame_energy_deltas.clear()

        self.coordinator.run_frame_start(
            self.frame_count, self.lifecycle_system, self.plant_manager, self._entity_manager
        )
        self._apply_entity_mutations("frame_start")

    def _phase_time_update(self) -> tuple[float, float]:
        """TIME_UPDATE: Advance day/night cycle and store time values."""
        self._current_phase = UpdatePhase.TIME_UPDATE

        time_modifier = 1.0
        time_of_day = 0.5
        if self.time_system:
            self.time_system.update(self.frame_count)
            time_modifier = self.time_system.get_activity_modifier()
            time_of_day = self.time_system.get_time_of_day()

        self._apply_entity_mutations("time_update")
        return time_modifier, time_of_day

    def _phase_environment(self) -> None:
        """ENVIRONMENT: Update ecosystem and detection modifiers."""
        self._current_phase = UpdatePhase.ENVIRONMENT
        self.coordinator.run_environment(self.ecosystem, self.environment, self.frame_count)
        self._apply_entity_mutations("environment")

    def _phase_entity_act(
        self,
        time_modifier: float,
        time_of_day: float,
    ) -> tuple[list[entities.Agent], list[entities.Agent]]:
        """ENTITY_ACT: Update all entities, collect spawns/deaths."""
        self._current_phase = UpdatePhase.ENTITY_ACT

        new_entities, entities_to_remove = self.coordinator.run_entity_act(
            self._entity_manager,
            self.frame_count,
            time_modifier,
            time_of_day,
            self._phase_hooks,
            self,
        )
        return new_entities, entities_to_remove

    def _phase_lifecycle(
        self,
        new_entities: list[entities.Agent],
        entities_to_remove: list[entities.Agent],
    ) -> None:
        """LIFECYCLE: Process deaths, add/remove entities."""
        self._current_phase = UpdatePhase.LIFECYCLE

        self.coordinator.run_lifecycle(self, new_entities, entities_to_remove, self._phase_hooks)

        self._apply_entity_mutations("lifecycle")

    def _phase_spawn(self) -> None:
        """SPAWN: Auto-spawn food and update spatial positions."""
        self._current_phase = UpdatePhase.SPAWN
        self.coordinator.run_spawn(self.food_spawning_system, self.frame_count)
        self._apply_entity_mutations("spawn")

        # Update spatial grid for moved entities
        if self.environment is not None:
            update_position = self.environment.update_agent_position
            for entity in self._entity_manager.entities_list:
                update_position(entity)

    def _phase_collision(self) -> None:
        """COLLISION: Handle physical collisions between entities."""
        self._current_phase = UpdatePhase.COLLISION
        self.coordinator.run_collision(self.collision_system, self.frame_count)
        self._apply_entity_mutations("collision")

    def _phase_interaction(self) -> None:
        """INTERACTION: Handle social interactions between entities."""
        self._current_phase = UpdatePhase.INTERACTION
        self.coordinator.run_interaction(
            self.poker_proximity_system, self.poker_system, self.frame_count, self
        )
        self._apply_entity_mutations("interaction")

    def handle_mixed_poker_games(self) -> None:
        """Called by coordinator via simple delegation from poker system usually,
        but kept here for API compatibility if needed."""
        if self.poker_system:
            self.poker_system.handle_mixed_poker_games()

    def _phase_reproduction(self) -> None:
        """REPRODUCTION: Handle mating and emergency spawns."""
        self._current_phase = UpdatePhase.REPRODUCTION

        # ReproductionSystem now handles both mating and emergency spawns
        self.handle_reproduction()
        self._apply_entity_mutations("reproduction")

        if self._phase_hooks:
            self._phase_hooks.on_reproduction_complete(self)

    def handle_reproduction(self) -> None:
        """Orchestrate reproduction logic."""
        # Delegated to coordinator's reproduction system logic essentially
        if self.reproduction_system:
            self.reproduction_system.update(self.frame_count)

    def _phase_frame_end(self) -> None:
        """FRAME_END: Update stats, rebuild caches."""
        self._current_phase = UpdatePhase.FRAME_END

        if self._phase_hooks:
            self._phase_hooks.on_frame_end(self)

        # Prune stale identity mappings
        if self._identity_provider is not None and hasattr(
            self._identity_provider, "prune_stale_ids"
        ):
            current_entity_ids = {id(e) for e in self._entity_manager.entities_list}
            self._identity_provider.prune_stale_ids(current_entity_ids)

        if self._entity_manager.is_dirty:
            self._rebuild_caches()

        if self._phase_debug_enabled:
            pending_spawns = self.mutations.pending_spawn_count()
            pending_removals = self.mutations.pending_removal_count()
            if pending_spawns or pending_removals:
                raise RuntimeError(
                    "End-of-frame invariant violated: pending entity mutations remain "
                    f"(spawns={pending_spawns}, removals={pending_removals})"
                )

        self._current_phase = None

    # =========================================================================
    # Identity Provider Helpers
    # =========================================================================

    def _get_entity_identity(self, entity: Any) -> tuple[str, str]:
        """Return (entity_type, stable_id) using the identity provider when available."""
        if self._identity_provider is None:
            return entity.__class__.__name__.lower(), str(id(entity))
        provider = self._identity_provider
        if hasattr(provider, "type_name") and hasattr(provider, "stable_id"):
            return provider.type_name(entity), provider.stable_id(entity)
        return provider.get_identity(entity)

    def _create_energy_recorder(self):
        """Create a recorder callback for energy delta tracking.

        Returns a function that can be passed to environment.set_energy_delta_recorder().
        The recorder forwards energy deltas to _frame_energy_deltas using the identity provider.
        """
        from core.worlds.contracts import EnergyDeltaRecord

        def recorder(entity: Any, delta: float, source: str, meta: dict[str, Any]) -> None:
            entity_type, stable_id = self._get_entity_identity(entity)
            record = EnergyDeltaRecord(
                entity_id=stable_id,
                stable_id=stable_id,
                entity_type=entity_type,
                delta=delta,
                source=source,
                metadata=meta or {},
            )
            self._frame_energy_deltas.append(record)

        return recorder

    # =========================================================================
    # Poker Events
    # =========================================================================

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Delegate event creation to the poker system."""
        if self.poker_system:
            self.poker_system.add_poker_event(poker)

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle poker result (compatibility method)."""
        if self.poker_system:
            self.poker_system.handle_poker_result(poker)

    def sprout_new_plant(self, parent_genome: Any, parent_x: float, parent_y: float) -> Any:
        """Delegate plant sprouting to plant manager."""
        if not self.plant_manager:
            return None
        return self.plant_manager.sprout_new_plant(
            parent_genome, parent_x, parent_y, self._entity_manager.entities_list
        )

    def get_recent_poker_events(self, max_age_frames: int | None = None) -> list[dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        if not self.poker_system:
            return []
        max_age = max_age_frames or self.config.poker.poker_event_max_age_frames
        return self.poker_system.get_recent_poker_events(max_age)

    def add_plant_poker_event(
        self,
        fish_id: int,
        plant_id: int,
        fish_won: bool,
        fish_hand: str,
        plant_hand: str,
        energy_transferred: float,
    ) -> None:
        """Delegate plant poker events to the poker system."""
        if self.poker_system:
            self.poker_system.add_plant_poker_event(
                fish_id,
                plant_id,
                fish_won,
                fish_hand,
                plant_hand,
                energy_transferred,
            )

    # =========================================================================
    # Soccer Events
    # =========================================================================

    def add_soccer_event(self, outcome: SoccerMinigameOutcome) -> None:
        """Record a soccer minigame outcome for UI/event streams."""

        def stringify_keys(values: dict[Any, Any]) -> dict[str, Any]:
            return {str(key): value for key, value in values.items()}

        event = {
            "frame": self.frame_count,
            "match_id": outcome.match_id,
            "match_counter": outcome.match_counter,
            "winner_team": outcome.winner_team,
            "score_left": outcome.score_left,
            "score_right": outcome.score_right,
            "frames": outcome.frames,
            "seed": outcome.seed,
            "selection_seed": outcome.selection_seed,
            "message": outcome.message,
            "rewarded": stringify_keys(dict(outcome.rewarded)),
            "entry_fees": stringify_keys(dict(outcome.entry_fees)),
            "energy_deltas": stringify_keys(dict(outcome.energy_deltas)),
            "repro_credit_deltas": stringify_keys(dict(outcome.repro_credit_deltas)),
            "teams": {
                "left": list(outcome.teams.get("left", [])),
                "right": list(outcome.teams.get("right", [])),
            },
            "last_goal": outcome.last_goal,
            "skipped": outcome.skipped,
            "skip_reason": outcome.skip_reason,
        }
        self._soccer_events.append(event)

    def get_recent_soccer_events(self, max_age_frames: int | None = None) -> list[dict[str, Any]]:
        """Get recent soccer events (within max_age_frames)."""
        max_age = max_age_frames or self.config.soccer.event_max_age_frames
        return [
            event for event in self._soccer_events if self.frame_count - event["frame"] < max_age
        ]

    def set_soccer_league_live_state(self, state: dict[str, Any] | None) -> None:
        """Store the latest league match state for rendering."""
        self._soccer_league_live = state

    def get_soccer_league_live_state(self) -> dict[str, Any] | None:
        """Return the latest league match state for rendering."""
        return self._soccer_league_live

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self, include_distributions: bool = True) -> dict[str, Any]:
        """Get current simulation statistics."""
        return self.stats_calculator.get_stats(include_distributions=include_distributions)

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive simulation statistics to JSON file."""
        diagnostics.export_stats_json(self, filename, self.start_time)

    def print_stats(self) -> None:
        """Print current simulation statistics to console."""
        diagnostics.print_simulation_stats(self, self.start_time)

    # =========================================================================
    # Run Methods
    # =========================================================================

    def run_headless(
        self,
        max_frames: int = 10000,
        stats_interval: int = 300,
        export_json: str | None = None,
    ) -> None:
        """Run the simulation in headless mode without visualization."""
        sep = self.config.display.separator_width
        logger.info("=" * sep)
        logger.info("HEADLESS FISH TANK SIMULATION")
        logger.info("=" * sep)
        logger.info(
            f"Running for {max_frames} frames ({max_frames / self.config.display.frame_rate:.1f} seconds of sim time)"
        )
        logger.info(f"Stats will be printed every {stats_interval} frames")
        if export_json:
            logger.info(f"Stats will be exported to: {export_json}")
        logger.info("=" * sep)

        self.setup()

        for frame in range(max_frames):
            self.update()

            if frame > 0 and frame % stats_interval == 0:
                self.print_stats()

        logger.info("")
        logger.info("=" * sep)
        logger.info("SIMULATION COMPLETE - Final Statistics")
        logger.info("=" * sep)
        self.print_stats()

        if self.ecosystem is not None:
            logger.info("")
            logger.info("=" * sep)
            logger.info("GENERATING ALGORITHM PERFORMANCE REPORT...")
            logger.info("=" * sep)
            report = self.ecosystem.get_algorithm_performance_report()
            logger.info(f"{report}")

            os.makedirs("logs", exist_ok=True)
            report_path = os.path.join("logs", "algorithm_performance_report.txt")
            with open(report_path, "w") as f:
                f.write(report)
            logger.info("")
            logger.info(f"Report saved to: {report_path}")

            if export_json:
                logger.info("")
                logger.info("=" * sep)
                logger.info("EXPORTING JSON STATISTICS FOR LLM ANALYSIS...")
                logger.info("=" * sep)
                self.export_stats_json(export_json)

    def run_collect_stats(self, max_frames: int = 100) -> dict[str, Any]:
        """Run the engine for `max_frames` frames and return final stats."""
        self.setup()
        for _ in range(max_frames):
            self.update()
        return self.get_stats()


class HeadlessSimulator(SimulationEngine):
    """Wrapper class for CI/testing with simplified interface."""

    def __init__(self, max_frames: int = 100, stats_interval: int = 0) -> None:
        """Initialize the headless simulator."""
        super().__init__(config=SimulationConfig.headless_fast())
        self.max_frames = max_frames
        self.stats_interval = stats_interval if stats_interval > 0 else max_frames + 1

    def run(self) -> None:
        """Run the simulation for the configured number of frames."""
        self.run_headless(max_frames=self.max_frames, stats_interval=self.stats_interval)
