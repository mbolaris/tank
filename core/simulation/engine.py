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



Why not use PhaseRunner yet?
----------------------------
The PhaseRunner in update_phases.py is designed for systems that declare
their own phase via @runs_in_phase. Currently, most of our update logic
is still inline in update() rather than in phase-aware systems.

A future refactoring could:
1. Move all inline phase logic into proper System classes
2. Have each System declare its phase
3. Use PhaseRunner to execute them automatically

For now, we keep the explicit phase logic in update() for clarity.
"""

from __future__ import annotations

import logging
import os
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from core.config.simulation_config import SimulationConfig
from core.simulation import diagnostics
from core.simulation.entity_manager import EntityManager
from core.simulation.entity_mutation_queue import EntityMutationQueue
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
    from core.systems.entity_lifecycle import EntityLifecycleSystem
    from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig
    from core.systems.poker_proximity import PokerProximitySystem
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

    def request_spawn(self, entity: Any, **kwargs: Any) -> bool: ...

    def request_remove(self, entity: Any, **kwargs: Any) -> bool: ...

    def _apply_entity_mutations(self, stage: str) -> None: ...

    def create_initial_entities(self) -> None: ...

    def _block_root_spots_with_obstacles(self) -> None: ...

    def _build_spawn_rate_config(self) -> SpawnRateConfig: ...


class SimulationEngine:
    """A headless simulation engine for the fish tank ecosystem.

    This class orchestrates the simulation by coordinating managers and systems.
    It does NOT contain business logic - that lives in the systems.

    Architecture:
        SimulationEngine (coordinator)
        ├── EntityManager (entity CRUD)
        ├── SystemRegistry (system lifecycle)
        ├── Systems (CollisionSystem, PokerSystem, etc.)
        ├── Managers (PlantManager, EcosystemManager)
        └── Services (StatsCalculator, StatsExporter)

    Mutation Ownership:
        Systems never mutate entity collections directly. They request
        spawns/removals via the engine's mutation queue, and the engine
        applies those mutations between phases.

    Attributes:
        config: Simulation configuration
        entities_list: All entities (via EntityManager)
        ecosystem: Population and stats tracking
        time_system: Day/night cycle
        frame_count: Total frames elapsed
        paused: Whether simulation is paused
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
        self._entity_mutations = EntityMutationQueue()

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
        self.collision_system: CollisionSystem | None = None
        self.reproduction_service: ReproductionService | None = None
        self.reproduction_system: ReproductionSystem | None = None
        self.poker_system: PokerSystem | None = None
        self.lifecycle_system: EntityLifecycleSystem | None = None
        self.poker_proximity_system: PokerProximitySystem | None = None
        self.food_spawning_system: FoodSpawningSystem | None = None
        self.plant_manager: PlantManager | None = None
        self.poker_events: list[Any] = []
        self._soccer_events: deque = deque(maxlen=self.config.soccer.max_events)
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

    def drain_frame_outputs(self) -> FrameOutputs:
        """Return this frame's outputs and clear internal buffers.

        This is the only supported way for backends to read per-frame spawns/removals/energy deltas.
        """
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

    # =========================================================================
    # Setup
    # =========================================================================

    def setup(self, pack: SystemPack | None = None) -> None:
        """Setup the simulation using the provided SystemPack.

        If no pack is provided, it tries to use the default Tank logic
        (via TankPack).
        """
        # NOTE: Poker cooldowns are now tracked on entities directly (Fish.poker_cooldown)
        # rather than in a global manager, so no per-engine cleanup is needed here.

        # Fallback to TankPack if no pack provided
        if pack is None:
            from core.worlds.tank.pack import TankPack

            pack = TankPack(self.config)

        # 1. Let the pack build core systems (wiring them into self for compatibility)
        systems = pack.build_core_systems(self)
        for attr, system in systems.items():
            setattr(self, attr, system)

        # 2. Let the pack build the environment
        self.environment = pack.build_environment(self)

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

        # 8. Finalize setup: apply any queued mutations from seeding (without recording frame outputs)
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
        phase_map = {
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

    # Also expose via private attribute
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
        """Add an entity to the simulation (INTERNAL USE ONLY).

        This method should only be called by the engine when applying
        queued mutations from _apply_entity_mutations(). External code
        should use request_spawn() to queue spawns for safe processing.
        """
        if hasattr(entity, "add_internal"):
            entity.add_internal(self.agents)
        self._entity_manager.add(entity)

    def _remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation (INTERNAL USE ONLY).

        This method should only be called by the engine when applying
        queued mutations from _apply_entity_mutations(). External code
        should use request_remove() to queue removals for safe processing.
        """
        self._entity_manager.remove(entity)

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation (PRIVILEGED API).

        WARNING: This bypasses the mutation queue. Only use from privileged
        infrastructure code like tank persistence, migration handlers, etc.

        Game systems should use request_spawn() to queue spawns for safe
        processing between phases. Calling this mid-frame can cause subtle bugs.
        """
        if self._current_phase is not None:
            raise RuntimeError(
                f"Unsafe call to add_entity during phase {self._current_phase}. "
                "Use request_spawn() instead."
            )
        self._add_entity(entity)

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation (PRIVILEGED API).

        WARNING: This bypasses the mutation queue. Only use from privileged
        infrastructure code like tank persistence, migration handlers, etc.

        Game systems should use request_remove() to queue removals for safe
        processing between phases. Calling this mid-frame can cause subtle bugs.
        """
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
        return self._entity_mutations.request_spawn(entity, reason=reason, metadata=metadata)

    def request_remove(
        self,
        entity: entities.Agent,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Queue a removal request to be applied by the engine."""
        return self._entity_mutations.request_remove(entity, reason=reason, metadata=metadata)

    def is_pending_removal(self, entity: entities.Agent) -> bool:
        """Check if an entity is queued for removal."""
        return self._entity_mutations.is_pending_removal(entity)

    def _apply_entity_mutations(self, stage: str, *, record_outputs: bool = True) -> None:
        """Apply queued spawns/removals at a safe point in the frame.

        Args:
            stage: Debug label for where the mutations are applied.
            record_outputs: When True, record SpawnRequest/RemovalRequest entries in the
                per-frame delta buffers. When False, apply mutations without touching
                frame outputs (used during setup/seeding).
        """
        from core.worlds.contracts import RemovalRequest, SpawnRequest

        removals = self._entity_mutations.drain_removals()
        for mutation in removals:
            entity = mutation.entity
            if record_outputs:
                # Use identity provider for stable IDs, fall back to class name + id()
                entity_type, entity_id = self._get_entity_identity(entity)
                self._frame_removals.append(
                    RemovalRequest(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        reason=mutation.reason,
                        metadata=mutation.metadata,
                    )
                )
            self._remove_entity(entity)

        spawns = self._entity_mutations.drain_spawns()
        for mutation in spawns:
            entity = mutation.entity
            if record_outputs:
                # Use identity provider for stable IDs, fall back to class name + id()
                entity_type, entity_id = self._get_entity_identity(entity)
                self._frame_spawns.append(
                    SpawnRequest(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        reason=mutation.reason,
                        metadata=mutation.metadata,
                    )
                )
            self._add_entity(entity)

    def get_fish_list(self) -> list[entities.Fish]:
        """Get cached list of all fish in the simulation."""
        return self._entity_manager.get_fish()

    def get_food_list(self) -> list[entities.Food]:
        """Get cached list of all food in the simulation."""
        return self._entity_manager.get_food()

    def get_fish_count(self) -> int:
        """Get the count of fish in the simulation."""
        return len(self.get_fish_list())

    def _rebuild_caches(self) -> None:
        """Rebuild all cached entity lists if needed."""
        self._entity_manager.rebuild_caches_if_needed()

    # =========================================================================
    # Lifecycle Delegation
    # =========================================================================

    def record_fish_death(self, fish: entities.Agent, cause: str | None = None) -> None:
        """Delegate fish death recording to the lifecycle system."""
        self.lifecycle_system.record_fish_death(fish, cause)

    def cleanup_dying_fish(self) -> None:
        """Delegate dying fish cleanup to the lifecycle system."""
        self.lifecycle_system.cleanup_dying_fish()

    # =========================================================================
    # Collision/Reproduction/Poker Delegation
    # =========================================================================

    def check_collision(self, e1: entities.Agent, e2: entities.Agent) -> bool:
        """Delegate collision detection to the collision system."""
        return self.collision_system.check_collision(e1, e2)

    def handle_fish_food_collision(self, fish: entities.Agent, food: entities.Agent) -> None:
        """Delegate fish-food collision handling to the collision system."""
        self.collision_system.handle_fish_food_collision(fish, food)

    def handle_reproduction(self) -> None:
        """Delegate reproduction handling to the reproduction system."""
        self.reproduction_system.update(self.frame_count)

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Delegate poker result processing to the poker system."""
        self.poker_system.handle_poker_result(poker)

    def handle_mixed_poker_games(self) -> None:
        """Delegate mixed poker games to the poker system."""
        self.poker_system.handle_mixed_poker_games()

    # =========================================================================
    # Plant Management
    # =========================================================================

    def sprout_new_plant(
        self, parent_genome: PlantGenome, parent_x: float, parent_y: float
    ) -> bool:
        """Sprout a new fractal plant from a parent genome."""
        if self.plant_manager is None:
            return False
        result = self.plant_manager.sprout_new_plant(
            parent_genome, parent_x, parent_y, self._entity_manager.entities_list
        )
        return result.is_ok()

    # =========================================================================
    # Core Update Loop
    # =========================================================================

    def update(self) -> None:
        """Update the state of the simulation.

        The update loop executes via the configured pipeline, which defines
        the sequence of phases. Different modes can provide custom pipelines
        to modify the update behavior.

        The default pipeline (used by Tank mode) executes phases in this order:
            1. FRAME_START: Reset counters, increment frame
            2. TIME_UPDATE: Advance day/night cycle
            3. ENVIRONMENT: Update ecosystem and detection modifiers
            4. ENTITY_ACT: Update all entities, collect spawns/deaths
            5. LIFECYCLE: Process deaths, add/remove entities
            6. SPAWN: Auto-spawn food
            7. COLLISION: Handle collisions
            8. INTERACTION: Handle social interactions (poker)
            9. REPRODUCTION: Handle mating and emergency spawns
            10. FRAME_END: Update stats, rebuild caches
        """
        if self.paused:
            return

        # Reset frame deltas
        self._frame_spawns.clear()
        self._frame_removals.clear()
        self._frame_energy_deltas.clear()

        # Inject energy delta recorder for this frame
        if self.environment is not None:
            self.environment.set_energy_delta_recorder(self._create_energy_recorder())

        try:
            if self.pipeline is not None:
                self.pipeline.run(self)
            else:
                # Fallback for edge cases where setup() wasn't called
                # (defensive - should not happen in normal use)
                self._phase_frame_start()
                time_modifier, time_of_day = self._phase_time_update()
                self._phase_environment()
                new_entities, entities_to_remove = self._phase_entity_act(
                    time_modifier, time_of_day
                )
                self._phase_lifecycle(new_entities, entities_to_remove)
                self._phase_spawn()
                self._phase_collision()
                self._phase_interaction()
                self._phase_reproduction()
                self._phase_frame_end()
        finally:
            # Clear recorder to prevent state leakage across frames
            if self.environment is not None:
                self.environment.set_energy_delta_recorder(None)

    def _create_energy_recorder(self):
        """Create a recorder callback for the current frame.

        Returns a function that records energy deltas by creating
        EnergyDeltaRecord entries with stable entity IDs.
        """
        from core.worlds.contracts import EnergyDeltaRecord

        def record(entity, delta: float, source: str, meta: dict) -> None:
            # Get stable ID for the entity
            entity_type, stable_id = self._get_entity_identity(entity)
            self._frame_energy_deltas.append(
                EnergyDeltaRecord(
                    entity_id=stable_id,
                    stable_id=stable_id,
                    entity_type=entity_type,
                    delta=delta,
                    source=source,
                    metadata=meta,
                )
            )

        return record

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_frame_start(self) -> None:
        """FRAME_START: Reset counters, increment frame."""
        self._current_phase = UpdatePhase.FRAME_START
        self.frame_count += 1
        self.lifecycle_system.update(self.frame_count)

        # Enforce the invariant: at most one Plant per RootSpot
        if self.plant_manager is not None:
            self.plant_manager.reconcile_plants(
                self._entity_manager.entities_list, self.frame_count
            )
            self.plant_manager.respawn_if_low(self._entity_manager.entities_list, self.frame_count)
        self._apply_entity_mutations("frame_start")

    def _phase_time_update(self) -> tuple:
        """TIME_UPDATE: Advance day/night cycle.

        Returns:
            Tuple of (time_modifier, time_of_day) for use by entity updates
        """
        self._current_phase = UpdatePhase.TIME_UPDATE
        self.time_system.update(self.frame_count)
        return (
            self.time_system.get_activity_modifier(),
            self.time_system.get_time_of_day(),
        )

    def _phase_environment(self) -> None:
        """ENVIRONMENT: Update ecosystem and detection modifiers."""
        self._current_phase = UpdatePhase.ENVIRONMENT
        if self.ecosystem is not None:
            self.ecosystem.update(self.frame_count)

        if self.environment is not None:
            self.environment.update_detection_modifier()

    def _phase_entity_act(self, time_modifier: float, time_of_day: float) -> tuple:
        """ENTITY_ACT: Update all entities, collect spawns/deaths.

        Args:
            time_modifier: Activity modifier from day/night cycle
            time_of_day: Current time of day (0-1)

        Returns:
            Tuple of (new_entities, entities_to_remove)
        """
        self._current_phase = UpdatePhase.ENTITY_ACT
        new_entities: list[entities.Agent] = []
        entities_to_remove: list[entities.Agent] = []

        hooks = self._phase_hooks

        for entity in list(self._entity_manager.entities_list):
            result = entity.update(self.frame_count, time_modifier, time_of_day)

            # Handle spawned entities via phase hooks
            if result.spawned_entities:
                for spawned in result.spawned_entities:
                    decision = hooks.on_entity_spawned(self, spawned, entity)
                    if decision.should_add:
                        new_entities.append(decision.entity)

            # Handle entity death via phase hooks
            if entity.is_dead():
                should_remove = hooks.on_entity_died(self, entity)
                if should_remove:
                    entities_to_remove.append(entity)

            # Note: Food removal (expiry, off-screen) is handled by phase hooks
            # in _phase_lifecycle via on_lifecycle_cleanup()

            # Enforce screen boundaries as a final safety check
            entity.constrain_to_screen()

        return new_entities, entities_to_remove

    def _phase_lifecycle(
        self,
        new_entities: list[entities.Agent],
        entities_to_remove: list[entities.Agent],
    ) -> None:
        """LIFECYCLE: Process deaths, add/remove entities.

        This phase is the SINGLE OWNER of entity removal decisions:
        - Entities marked for removal in entity_act phase
        - Mode-specific cleanup (Food expiry, death animations, etc.)

        Removals/spawns are queued and applied between phases by the engine.
        """
        self._current_phase = UpdatePhase.LIFECYCLE

        # Remove entities collected during entity_act phase
        for entity in entities_to_remove:
            self.request_remove(entity, reason="entity_act")

        # Mode-specific lifecycle cleanup (Food removal, death animations, etc.)
        self._phase_hooks.on_lifecycle_cleanup(self)

        # Add new entities spawned during entity_act
        for new_entity in new_entities:
            self.request_spawn(new_entity, reason="entity_act")

        self._apply_entity_mutations("lifecycle")

    def _phase_spawn(self) -> None:
        """SPAWN: Auto-spawn food and update spatial positions."""
        self._current_phase = UpdatePhase.SPAWN

        if self.food_spawning_system:
            self.food_spawning_system.update(self.frame_count)

        self._apply_entity_mutations("spawn")

        # Update spatial grid for moved entities
        if self.environment is not None:
            update_position = self.environment.update_agent_position
            for entity in self._entity_manager.entities_list:
                update_position(entity)

    def _phase_collision(self) -> None:
        """COLLISION: Handle physical collisions between entities.

        CollisionSystem handles physical collision logic:
        - Fish-Food collisions (eating)
        - Fish-Crab collisions (predation)
        - Food-Crab collisions

        Note: Fish-Fish poker proximity is handled by PokerProximitySystem
        in _phase_interaction().
        """
        self._current_phase = UpdatePhase.COLLISION
        # CollisionSystem._do_update() handles physical collision iteration
        self.collision_system.update(self.frame_count)
        self._apply_entity_mutations("collision")

    def _phase_interaction(self) -> None:
        """INTERACTION: Handle social interactions between entities.

        Systems in this phase:
        - PokerProximitySystem: Detects fish groups and triggers poker games
        - PokerSystem: Processes game outcomes, updates Elo, handles mixed poker
        """
        self._current_phase = UpdatePhase.INTERACTION
        # Fish-fish poker proximity detection
        self.poker_proximity_system.update(self.frame_count)

        # PokerSystem processes game outcomes
        self.poker_system.update(self.frame_count)
        # Mixed poker (fish-plant, plant-plant)
        self.handle_mixed_poker_games()

        self._apply_entity_mutations("interaction")

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

    def _phase_reproduction(self) -> None:
        """REPRODUCTION: Handle mating and emergency spawns.

        Orchestration Note: The engine decides WHEN reproduction runs.
        The business logic and stats recording are handled by phase hooks.
        """
        self._current_phase = UpdatePhase.REPRODUCTION
        # ReproductionSystem now handles both mating and emergency spawns
        self.handle_reproduction()
        self._apply_entity_mutations("reproduction")

        # Mode-specific reproduction stats (fish population, energy, etc.)
        self._phase_hooks.on_reproduction_complete(self)

    def _phase_frame_end(self) -> None:
        """FRAME_END: Update stats, rebuild caches."""
        self._current_phase = UpdatePhase.FRAME_END

        # Mode-specific frame-end processing (benchmarks, etc.)
        self._phase_hooks.on_frame_end(self)

        # Prune stale identity mappings to prevent memory leaks and id() reuse
        # corruption. This removes entries for entities that no longer exist.
        if self._identity_provider is not None and hasattr(
            self._identity_provider, "prune_stale_ids"
        ):
            current_entity_ids = {id(e) for e in self._entity_manager.entities_list}
            self._identity_provider.prune_stale_ids(current_entity_ids)

        if self._entity_manager.is_dirty:
            self._rebuild_caches()

        if self._phase_debug_enabled:
            pending_spawns = self._entity_mutations.pending_spawn_count()
            pending_removals = self._entity_mutations.pending_removal_count()
            if pending_spawns or pending_removals:
                raise RuntimeError(
                    "End-of-frame invariant violated: pending entity mutations remain "
                    f"(spawns={pending_spawns}, removals={pending_removals})"
                )

        self._current_phase = None

    # =========================================================================
    # Emergency Spawning
    # =========================================================================

    # =========================================================================
    # Poker Events
    # =========================================================================

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Delegate event creation to the poker system."""
        self.poker_system.add_poker_event(poker)

    def get_recent_poker_events(self, max_age_frames: int | None = None) -> list[dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
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
    """Wrapper class for CI/testing with simplified interface.

    This class provides a simpler interface for headless testing,
    accepting max_frames in the constructor and providing a simple run() method.
    """

    def __init__(self, max_frames: int = 100, stats_interval: int = 0) -> None:
        """Initialize the headless simulator.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames (0 = no stats during run)
        """
        super().__init__(config=SimulationConfig.headless_fast())
        self.max_frames = max_frames
        self.stats_interval = stats_interval if stats_interval > 0 else max_frames + 1

    def run(self) -> None:
        """Run the simulation for the configured number of frames."""
        self.run_headless(max_frames=self.max_frames, stats_interval=self.stats_interval)
