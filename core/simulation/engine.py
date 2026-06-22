"""Pure simulation engine - the slim orchestrator.

This module provides the core simulation loop without any embedded logic.
It coordinates systems and managers but doesn't contain business logic inline.

Design Decisions:
-----------------
1. The engine is a COORDINATOR, not a DOER. It owns managers and systems
   but doesn't contain business logic inline.

2. Entity management is delegated to EntityManager.
   System management is delegated to SystemRegistry.
   Stats calculation is delegated to StatsCalculator.

3. The update() method runs phases in order via the EnginePipeline.
   Phase bodies live in PhaseExecutor; the engine keeps thin ``_phase_*``
   facades so the pipeline and tests keep a single entry point.

4. Executive logic is delegated to focused collaborators:
   - SystemCoordinator: per-phase system execution
   - PhaseExecutor: phase bodies + current-phase tracking
   - MutationTransaction + MutationExecutor: queued entity mutations and
     their commit points between phases
   - FrameAggregator: per-frame spawn/removal/energy-delta outputs
   - engine_setup: SystemPack-driven assembly sequence
"""

from __future__ import annotations

import logging
import os
import random
import time
import uuid
from typing import TYPE_CHECKING, Any

import core.simulation.diagnostics as diagnostics
import core.simulation.headless_runner as headless_runner
from core.agents_wrapper import AgentsWrapper
from core.config.simulation_config import SimulationConfig
from core.entity_factory import create_initial_population
from core.services.stats.calculator import StatsCalculator
from core.simulation.coordinator import SystemCoordinator
from core.simulation.engine_setup import setup_engine
from core.simulation.entity_manager import EntityManager
from core.simulation.event_managers import SoccerEventManager
from core.simulation.frame_aggregator import FrameAggregator, FrameOutputs
from core.simulation.mutation import MutationTransaction
from core.simulation.mutation_executor import MutationExecutor
from core.simulation.phase_executor import PhaseExecutor
from core.simulation.phase_hooks import NoOpPhaseHooks, PhaseHooks
from core.simulation.system_registry import SystemRegistry
from core.systems.base import BaseSystem
from core.systems.food_spawning import SpawnRateConfig
from core.time_system import TimeSystem

if TYPE_CHECKING:
    from core import entities, environment
    from core.collision_system import CollisionSystem
    from core.ecosystem import EcosystemManager
    from core.plant_manager import PlantManager
    from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
    from core.poker.integration.poker_system import PokerSystem
    from core.reproduction.reproduction_service import ReproductionService
    from core.reproduction.reproduction_system import ReproductionSystem
    from core.root_spots import RootSpotManager
    from core.simulation.pipeline import EnginePipeline
    from core.systems.entity_lifecycle import EntityLifecycleSystem
    from core.systems.food_spawning import FoodSpawningSystem
    from core.systems.poker_proximity import PokerProximitySystem
    from core.systems.soccer_system import SoccerSystem
    from core.update_phases import UpdatePhase
    from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest
    from core.worlds.identity import EntityIdentityProvider
    from core.worlds.system_pack import SystemPack

logger = logging.getLogger(__name__)


class SimulationEngine:
    """A headless simulation engine for the fish tank ecosystem.

    Refactored to delegate logic to SystemCoordinator, PhaseExecutor,
    MutationExecutor, and FrameAggregator.
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

        self.agents = AgentsWrapper(self)
        self._system_registry = SystemRegistry()

        # New modular components
        self.coordinator = SystemCoordinator()
        self.mutations = MutationTransaction()
        self.frame_aggregator = FrameAggregator()
        self.mutation_executor = MutationExecutor(
            transaction=self.mutations,
            entity_manager=self._entity_manager,
            aggregator=self.frame_aggregator,
            pre_add_callback=lambda e: (
                e.add_internal(self.agents) if hasattr(e, "add_internal") else None
            ),
        )
        self.phase_executor = PhaseExecutor(self)

        # Core state
        self.environment: environment.Environment | None = None
        self.ecosystem: EcosystemManager | None = None
        self.time_system: TimeSystem = TimeSystem(self)
        self.start_time: float = time.time()

        # Services
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

        # Soccer event management (extracted from engine)
        self._soccer_events_mgr = SoccerEventManager(
            max_events=self.config.soccer.max_events,
            frame_provider=lambda: self.frame_count,
        )

        # Periodic poker benchmark evaluation
        self.benchmark_evaluator: PeriodicBenchmarkEvaluator | None = None

        # Phase debug flag for invariant enforcement.
        # Enable via config OR env var (for tests to force invariant checking)
        self._phase_debug_enabled: bool = (
            self.config.enable_phase_debug
            or os.environ.get("TANK_ENFORCE_MUTATION_INVARIANTS", "0") == "1"
        )

        # Pipeline (set during setup())
        self.pipeline: EnginePipeline | None = None

        # Identity provider for stable delta IDs (set during setup())
        self._identity_provider: EntityIdentityProvider | None = None

        # Phase hooks for mode-specific entity handling (set during setup())
        self._phase_hooks: PhaseHooks = NoOpPhaseHooks()
        self.coordinator.set_phase_hooks(self._phase_hooks)

    def drain_frame_outputs(self) -> FrameOutputs:
        """Return this frame's outputs and clear internal buffers."""
        return self.frame_aggregator.drain()

    # =========================================================================
    # Compatibility Properties
    # =========================================================================

    @property
    def entities_list(self) -> list[entities.Entity]:
        """All entities in the simulation (delegates to EntityManager)."""
        return self._entity_manager.entities_list

    @property
    def food_pool(self):
        """Food object pool (delegates to EntityManager)."""
        return self._entity_manager.food_pool

    @property
    def entity_manager(self) -> EntityManager:
        """Public access to entity storage and cached typed views."""
        return self._entity_manager

    @property
    def root_spot_manager(self) -> RootSpotManager | None:
        """Access to root spot manager via PlantManager."""
        if self.plant_manager is None:
            return None
        return self.plant_manager.root_spot_manager

    @property
    def _frame_spawns(self) -> list[SpawnRequest]:
        """This frame's spawn records (delegates to FrameAggregator)."""
        return self.frame_aggregator.spawns

    @property
    def _frame_removals(self) -> list[RemovalRequest]:
        """This frame's removal records (delegates to FrameAggregator)."""
        return self.frame_aggregator.removals

    @property
    def _frame_energy_deltas(self) -> list[EnergyDeltaRecord]:
        """This frame's energy delta records (delegates to FrameAggregator)."""
        return self.frame_aggregator.energy_deltas

    @_frame_energy_deltas.setter
    def _frame_energy_deltas(self, value: list[EnergyDeltaRecord]) -> None:
        self.frame_aggregator.energy_deltas = value

    @property
    def _current_phase(self) -> UpdatePhase | None:
        """The currently executing update phase (delegates to PhaseExecutor)."""
        return self.phase_executor.current_phase

    @_current_phase.setter
    def _current_phase(self, phase: UpdatePhase | None) -> None:
        self.phase_executor.current_phase = phase

    # Expose mutation queue for tests that access private member
    @property
    def _entity_mutations(self):
        return self.mutations._queue

    # =========================================================================
    # Setup (assembly sequence lives in core.simulation.engine_setup)
    # =========================================================================

    def setup(self, pack: SystemPack | None = None) -> None:
        """Setup the simulation using the provided SystemPack."""
        setup_engine(self, pack)

    def _build_spawn_rate_config(self) -> SpawnRateConfig:
        """Translate SimulationConfig food settings into SpawnRateConfig."""
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
    # Phase Tracking (delegates to PhaseExecutor)
    # =========================================================================

    def get_current_phase(self) -> UpdatePhase | None:
        """Get the current update phase (None if not in update loop)."""
        return self.phase_executor.current_phase

    def get_phase_description(self, phase: UpdatePhase | None = None) -> str:
        """Get a human-readable description of a phase."""
        return self.phase_executor.describe_phase(phase)

    # =========================================================================
    # Entity Management (delegate to EntityManager)
    # =========================================================================

    def create_initial_entities(self) -> None:
        """Create initial entities in the simulation."""
        if self.environment is None or self.ecosystem is None:
            return

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

    def get_all_entities(self) -> list[entities.Entity]:
        """Get all entities in the simulation."""
        return self._entity_manager.entities_list

    def _add_entity(self, entity: entities.Entity) -> None:
        """Add an entity to the simulation (INTERNAL USE ONLY)."""
        if hasattr(entity, "add_internal"):
            entity.add_internal(self.agents)
        self._entity_manager.add(entity)

    def _remove_entity(self, entity: entities.Entity) -> None:
        """Remove an entity from the simulation (INTERNAL USE ONLY)."""
        self._entity_manager.remove(entity)

    def add_entity(self, entity: entities.Entity) -> None:
        """Add an entity to the simulation (PRIVILEGED API)."""
        if self._current_phase is not None:
            raise RuntimeError(
                f"Unsafe call to add_entity during phase {self._current_phase}. "
                "Use request_spawn() instead."
            )
        self._add_entity(entity)

    def remove_entity(self, entity: entities.Entity) -> None:
        """Remove an entity from the simulation (PRIVILEGED API)."""
        if self._current_phase is not None:
            raise RuntimeError(
                f"Unsafe call to remove_entity during phase {self._current_phase}. "
                "Use request_remove() instead."
            )
        self._remove_entity(entity)

    def request_spawn(
        self,
        entity: entities.Entity,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Queue a spawn request to be applied by the engine."""
        return self.mutations.request_spawn(entity, reason=reason, metadata=metadata)

    def request_remove(
        self,
        entity: entities.Entity,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Queue a removal request to be applied by the engine."""
        return self.mutations.request_remove(entity, reason=reason, metadata=metadata)

    def is_pending_removal(self, entity: entities.Entity) -> bool:
        """Check if an entity is queued for removal."""
        return self.mutations.is_pending_removal(entity)

    def _apply_entity_mutations(self, stage: str, *, record_outputs: bool = True) -> None:
        """Apply queued spawns/removals at a safe point in the frame.

        Delegates to MutationExecutor, which commits the mutation queue using
        the identity_provider for stable entity IDs.
        """
        self.mutation_executor.apply(
            stage,
            identity_provider=self._identity_provider,
            record_outputs=record_outputs,
        )

    def _rebuild_caches(self) -> None:
        """Trigger cache rebuilds on environment and entity manager."""
        if self.environment:
            self.environment.rebuild_spatial_grid()
        self._entity_manager.rebuild_caches_if_needed()

    # =========================================================================
    # Update Loop (phase bodies live in PhaseExecutor)
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
    # Phase Facades (called by Pipeline and tests; bodies in PhaseExecutor)
    # -------------------------------------------------------------------------

    def _phase_frame_start(self) -> None:
        """FRAME_START: Reset counters, increment frame."""
        self.phase_executor.frame_start()

    def _phase_time_update(self) -> tuple[float, float]:
        """TIME_UPDATE: Advance day/night cycle and store time values."""
        return self.phase_executor.time_update()

    def _phase_environment(self) -> None:
        """ENVIRONMENT: Update ecosystem and detection modifiers."""
        self.phase_executor.environment()

    def _phase_entity_act(
        self,
        time_modifier: float,
        time_of_day: float,
    ) -> tuple[list[entities.Agent], list[entities.Agent]]:
        """ENTITY_ACT: Update all entities, collect spawns/deaths."""
        return self.phase_executor.entity_act(time_modifier, time_of_day)

    def _phase_lifecycle(
        self,
        new_entities: list[entities.Agent],
        entities_to_remove: list[entities.Agent],
    ) -> None:
        """LIFECYCLE: Process deaths, add/remove entities."""
        self.phase_executor.lifecycle(new_entities, entities_to_remove)

    def _phase_spawn(self) -> None:
        """SPAWN: Auto-spawn food and update spatial positions."""
        self.phase_executor.spawn()

    def _phase_collision(self) -> None:
        """COLLISION: Handle physical collisions between entities."""
        self.phase_executor.collision()

    def _phase_interaction(self) -> None:
        """INTERACTION: Handle social interactions between entities."""
        self.phase_executor.interaction()

    def _phase_reproduction(self) -> None:
        """REPRODUCTION: Handle mating and emergency spawns."""
        self.phase_executor.reproduction()

    def _phase_frame_end(self) -> None:
        """FRAME_END: Update stats, rebuild caches."""
        self.phase_executor.frame_end()

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
        The recorder forwards energy deltas to the FrameAggregator, resolving
        stable IDs via _get_entity_identity (the identity provider).
        """
        return self.frame_aggregator.create_energy_recorder(self._get_entity_identity)

    # =========================================================================
    # Plant Sprouting
    # =========================================================================

    def sprout_new_plant(self, parent_genome: Any, parent_x: float, parent_y: float) -> Any:
        """Delegate plant sprouting to plant manager."""
        if not self.plant_manager:
            return None
        return self.plant_manager.sprout_new_plant(
            parent_genome, parent_x, parent_y, self._entity_manager.entities_list
        )

    # =========================================================================
    # Soccer Events
    # =========================================================================

    @property
    def soccer_events(self) -> SoccerEventManager:
        """The soccer minigame event stream (owns recent outcomes + league state).

        Callers record/read soccer events through this manager rather than via
        soccer-specific engine methods, keeping minigame surface off the engine
        (ADR-011).
        """
        return self._soccer_events_mgr

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
        headless_runner.run_headless(
            self,
            max_frames=max_frames,
            stats_interval=stats_interval,
            export_json=export_json,
        )

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
