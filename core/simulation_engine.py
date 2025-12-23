"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without any visualization code.
"""

import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

from core import entities, environment, movement_strategy
from core.algorithms.registry import get_algorithm_index
from core.config.ecosystem import (
    CRITICAL_POPULATION_THRESHOLD,
    EMERGENCY_SPAWN_COOLDOWN,
    MAX_POPULATION,
    SPAWN_MARGIN_PIXELS,
    TOTAL_ALGORITHM_COUNT,
    TOTAL_SPECIES_COUNT,
)
from core.config.display import (
    FILES,
    FRAME_RATE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEPARATOR_WIDTH,
)
from core.config.server import PLANTS_ENABLED
from core.config.poker import (
    MAX_POKER_EVENTS,
    POKER_EVENT_MAX_AGE_FRAMES,
)
from core.ecosystem import EcosystemManager
from core.entities.plant import Plant, PlantNectar
from core.entity_factory import create_initial_population
from core.events import EnergyChangedEvent
from core.poker_interaction import PokerInteraction
from core.genetics import Genome
from core.genetics import PlantGenome
from core.plant_manager import PlantManager
from core.poker.evaluation.benchmark_eval import BenchmarkEvalConfig
from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
from core.root_spots import RootSpotManager
from core.services.stats_calculator import StatsCalculator
from core.simulation_stats_exporter import SimulationStatsExporter
from core.simulators.base_simulator import BaseSimulator
from core.systems.base import BaseSystem
from core.systems.food_spawning import SpawnRateConfig
from core.simulation_runtime import (
    SimulationContext,
    SimulationRuntime,
    SimulationRuntimeConfig,
    SystemRegistry,
)
from core.update_phases import PHASE_DESCRIPTIONS, UpdatePhase

logger = logging.getLogger(__name__)


# Map simulation phases to their descriptions for documentation
SIMULATION_PHASES = {
    UpdatePhase.FRAME_START: "Reset counters, check paused state",
    UpdatePhase.TIME_UPDATE: "Advance day/night cycle, get time modifiers",
    UpdatePhase.ENVIRONMENT: "Update ecosystem stats, detection modifiers",
    UpdatePhase.ENTITY_ACT: "Update all entities (movement, energy, spawning)",
    UpdatePhase.LIFECYCLE: "Process deaths, add/remove entities",
    UpdatePhase.SPAWN: "Auto-spawn food, emergency fish spawning",
    UpdatePhase.COLLISION: "Handle fish-food collisions",
    UpdatePhase.INTERACTION: "Handle poker games between fish",
    UpdatePhase.REPRODUCTION: "Handle mating and reproduction",
    UpdatePhase.FRAME_END: "Update stats, rebuild caches",
}


class AgentsWrapper:
    """Wrapper to provide a group-like API for managing entities.

    The wrapper can be initialized with either a raw list of entities
    (for simple, isolated tests) or a SimulationEngine instance to
    ensure adds/removals stay in sync with spatial grids and caches.
    """

    def __init__(self, entities_or_engine: Any):
        # Support both legacy list usage and engine-aware management
        if hasattr(entities_or_engine, "add_entity") and hasattr(
            entities_or_engine, "entities_list"
        ):
            self._engine = entities_or_engine
            self._entities = entities_or_engine.entities_list
        else:
            self._engine = None
            self._entities = entities_or_engine

    def add(self, *entities):
        """Add entities to the list or engine-aware collection."""
        for entity in entities:
            if entity in self._entities:
                if hasattr(entity, "add_internal"):
                    entity.add_internal(self)
                continue

            if self._engine is not None:
                self._engine.add_entity(entity)
            else:
                self._entities.append(entity)
            if hasattr(entity, "add_internal"):
                entity.add_internal(self)

    def remove(self, *entities):
        """Remove entities from the list or engine-aware collection."""
        for entity in entities:
            if entity not in self._entities:
                continue
            if self._engine is not None:
                self._engine.remove_entity(entity)
            else:
                self._entities.remove(entity)

    def empty(self):
        """Remove all entities from the collection."""
        for entity in list(self._entities):
            self.remove(entity)

    def __contains__(self, entity):
        """Check if entity is in the collection."""
        return entity in self._entities

    def __iter__(self):
        """Iterate over entities."""
        return iter(self._entities)

    def __len__(self):
        """Get number of entities."""
        return len(self._entities)


class SimulationEngine(BaseSimulator):
    """A headless simulation engine for the fish tank ecosystem.

    This class runs the simulation without any visualization,
    allowing for faster-than-realtime execution and stats-only reporting.

    Attributes:
        entities_list: All entities in the simulation
        environment: Environment for entity queries
        ecosystem: Ecosystem manager for population tracking
        time_system: Day/night cycle manager
        frame_count: Total frames elapsed
        paused: Whether simulation is paused
        start_time: Real-world start time
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
        enable_poker_benchmarks: Optional[bool] = None,
        runtime: Optional[SimulationRuntime] = None,
        config: Optional[Any] = None,
    ) -> None:
        """Initialize the simulation engine.

        Args:
            headless: If True, run without any visualization
            rng: Shared random number generator for deterministic runs
            enable_poker_benchmarks: If True, enable periodic benchmark evaluations
        """
        super().__init__()
        # Prefer headless/benchmark toggles from provided config when explicit args are not given.
        cfg_headless = headless
        if cfg_headless is None and config is not None:
            cfg_headless = getattr(config, "headless", None)

        cfg_enable_benchmarks = enable_poker_benchmarks
        if cfg_enable_benchmarks is None and config is not None:
            cfg_enable_benchmarks = getattr(
                getattr(config, "poker", None), "enable_periodic_benchmarks", None
            )
        if cfg_enable_benchmarks is None:
            cfg_enable_benchmarks = False

        if runtime is None:
            runtime_config = SimulationRuntimeConfig(
                headless=cfg_headless if cfg_headless is not None else True,
                rng=rng,
                seed=seed,
                enable_poker_benchmarks=cfg_enable_benchmarks,
            )
            self.runtime = SimulationRuntime(runtime_config)
        else:
            self.runtime = runtime

        def _cfg(path: List[str], default: Any) -> Any:
            target = config
            for part in path:
                if target is None or not hasattr(target, part):
                    return default
                target = getattr(target, part)
            return target

        # Derived configuration values (fall back to module defaults if no config provided)
        self._display_width = _cfg(["display", "screen_width"], SCREEN_WIDTH)
        self._display_height = _cfg(["display", "screen_height"], SCREEN_HEIGHT)
        self._separator_width = _cfg(["display", "separator_width"], SEPARATOR_WIDTH)
        self._frame_rate = _cfg(["display", "frame_rate"], FRAME_RATE)
        self._files = _cfg(["display", "files"], FILES)
        self._plants_enabled = _cfg(["server", "plants_enabled"], PLANTS_ENABLED)
        self._max_population = _cfg(["ecosystem", "max_population"], MAX_POPULATION)
        self._critical_population_threshold = _cfg(
            ["ecosystem", "critical_population_threshold"], CRITICAL_POPULATION_THRESHOLD
        )
        self._emergency_spawn_cooldown = _cfg(
            ["ecosystem", "emergency_spawn_cooldown"], EMERGENCY_SPAWN_COOLDOWN
        )
        self._spawn_margin_pixels = _cfg(["ecosystem", "spawn_margin_pixels"], SPAWN_MARGIN_PIXELS)
        self._total_algorithm_count = _cfg(["ecosystem", "total_algorithm_count"], TOTAL_ALGORITHM_COUNT)
        self._total_species_count = _cfg(["ecosystem", "total_species_count"], TOTAL_SPECIES_COUNT)
        self.poker_max_events = _cfg(["poker", "max_poker_events"], MAX_POKER_EVENTS)
        self.poker_event_max_age_frames = _cfg(
            ["poker", "poker_event_max_age_frames"], POKER_EVENT_MAX_AGE_FRAMES
        )

        food_cfg = _cfg(["food"], None)
        self.food_spawn_config = _cfg(["food", "spawn_rate_config"], None)
        if self.food_spawn_config is None:
            self.food_spawn_config = SpawnRateConfig()
        self.auto_food_enabled = getattr(food_cfg, "auto_food_enabled", None) if food_cfg else None

        # Resolve RNG once so the context and engine share the same deterministic source.
        resolved_rng, resolved_seed = self.runtime.resolve_rng()
        self.seed = resolved_seed
        self.headless = self.runtime.config.headless
        self.entities_list: List[entities.Agent] = []
        self.agents = AgentsWrapper(self)
        self.context: SimulationContext = self.runtime.build_context(
            lambda: self.entities_list, rng=resolved_rng
        )
        self.rng: random.Random = self.context.rng
        self.environment: Optional[environment.Environment] = None
        self.time_system = None
        self.start_time: float = time.time()
        self.last_emergency_spawn_frame: int = (
            -self._emergency_spawn_cooldown
        )  # Allow immediate first spawn

        # Event bus for decoupled communication between components
        self.event_bus = self.context.event_bus

        # Systems - all extend BaseSystem for consistent interface (created in setup)
        self.collision_system = None
        self.reproduction_system = None
        self.poker_system = None
        self.poker_events = None
        self.lifecycle_system = None
        self._system_registry: Optional[SystemRegistry] = None

        # System Registry - maintains execution order and provides uniform management
        # Systems are registered in setup() once all dependencies are ready
        self._systems: List[BaseSystem] = []

        # Performance: Object pool for Food entities (uses engine's rng for deterministic behavior)
        self.food_pool = self.context.food_pool

        # Performance: Centralized cache management for entity type lists
        self._cache_manager = self.context.cache_manager

        # Fractal plant system (initialized in setup())
        self.plant_manager: Optional[PlantManager] = None

        # Periodic poker benchmark evaluation
        self.benchmark_evaluator: Optional[PeriodicBenchmarkEvaluator] = None
        if self.runtime.config.enable_poker_benchmarks:
            self.benchmark_evaluator = PeriodicBenchmarkEvaluator(
                BenchmarkEvalConfig()
            )

        # Services
        self.stats_calculator = StatsCalculator(self)

        # Telemetry
        self.stats_exporter = SimulationStatsExporter(self)

        # Phase tracking for debugging and monitoring
        self._current_phase: Optional[UpdatePhase] = None
        self._phase_debug_enabled: bool = bool(_cfg(["enable_phase_debug"], False))

    @property
    def root_spot_manager(self) -> Optional[RootSpotManager]:
        """Backward-compatible access to root spot manager via PlantManager."""
        if self.plant_manager is None:
            return None
        return self.plant_manager.root_spot_manager

    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize core systems through the runtime registry
        self._system_registry = self.runtime.create_registry(self, self.context)
        self._systems = self._system_registry.systems.copy()

        # Initialize managers
        self.environment = environment.Environment(
            self.entities_list,
            self._display_width,
            self._display_height,
            self.time_system,
            rng=self.context.rng,
        )
        self.ecosystem = EcosystemManager(max_population=self._max_population)

        # Initialize plant management system
        if self._plants_enabled:
            self.plant_manager = PlantManager(
                environment=self.environment,
                ecosystem=self.ecosystem,
                entity_adder=self,
                rng=self.rng,
            )

        # Wire up event bus subscriptions
        self._setup_event_subscriptions()

        self.create_initial_entities()

        # Create initial fractal plants
        if self.plant_manager is not None:
            self._block_root_spots_with_obstacles()
            self.plant_manager.create_initial_plants(self.entities_list)

    # =========================================================================
    # System Registry Methods
    # =========================================================================

    def get_systems(self) -> List[BaseSystem]:
        """Get all registered systems.

        Returns:
            List of registered systems in execution order
        """
        return self._systems.copy()

    def get_system(self, name: str) -> Optional[BaseSystem]:
        """Get a system by name.

        Args:
            name: The name of the system to retrieve

        Returns:
            The system if found, None otherwise
        """
        for system in self._systems:
            if system.name == name:
                return system
        return None

    def get_systems_debug_info(self) -> Dict[str, Any]:
        """Get debug information from all registered systems.

        Returns:
            Dictionary mapping system names to their debug info
        """
        return {
            system.name: system.get_debug_info()
            for system in self._systems
        }

    def get_current_phase(self) -> Optional[UpdatePhase]:
        """Get the current update phase (None if not in update loop).

        Useful for debugging to understand what phase the simulation is in.

        Returns:
            Current UpdatePhase or None if not updating
        """
        return self._current_phase

    def get_phase_description(self, phase: Optional[UpdatePhase] = None) -> str:
        """Get a human-readable description of a phase.

        Args:
            phase: The phase to describe (defaults to current phase)

        Returns:
            Description string for the phase
        """
        if phase is None:
            phase = self._current_phase
        if phase is None:
            return "Not in update loop"
        return SIMULATION_PHASES.get(phase, PHASE_DESCRIPTIONS.get(phase, phase.name))

    def set_system_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a system by name.

        Args:
            name: The name of the system
            enabled: Whether the system should be enabled

        Returns:
            True if system was found and updated, False otherwise
        """
        system = self.get_system(name)
        if system is not None:
            system.enabled = enabled
            return True
        return False

    # =========================================================================
    # Event Bus Methods
    # =========================================================================

    def _setup_event_subscriptions(self) -> None:
        """Set up event bus subscriptions for the engine.

        This wires up the event-driven architecture by subscribing
        to events emitted by entities and systems.
        """
        # Energy tracking - forward to ecosystem
        self.event_bus.subscribe(EnergyChangedEvent, self._on_energy_changed)

    def _on_energy_changed(self, event: EnergyChangedEvent) -> None:
        """Handle energy change events.

        Args:
            event: The energy change event
        """
        if self.ecosystem is not None and event.amount < 0:
            # Record energy burns to ecosystem
            self.ecosystem.record_energy_burn(event.source, abs(event.amount))

    def emit_event(self, event) -> None:
        """Emit an event to the engine's event bus.

        This is the public API for systems and entities to emit events.

        Args:
            event: The event to emit
        """
        self.event_bus.emit(event)

    def get_event_bus_stats(self) -> Dict[str, Any]:
        """Get statistics about the event bus.

        Returns:
            Dictionary with event bus statistics
        """
        return self.event_bus.get_stats()

    # =========================================================================
    # Entity Management
    # =========================================================================

    def create_initial_entities(self) -> None:
        """Create initial entities in the fish tank with multiple species."""
        if self.environment is None or self.ecosystem is None:
            return

        # Use centralized factory function for initial population
        population = create_initial_population(
            self.environment, self.ecosystem, self._display_width, self._display_height, rng=self.rng
        )
        for entity in population:
            self.agents.add(entity)

    def _block_root_spots_with_obstacles(self) -> None:
        """Prevent plants from spawning where static obstacles live."""
        if self.plant_manager is None:
            return
        for entity in self.entities_list:
            self.plant_manager.block_spots_for_entity(entity)

    def sprout_new_plant(
        self, parent_genome: PlantGenome, parent_x: float, parent_y: float
    ) -> bool:
        """Sprout a new fractal plant from a parent genome.

        Delegates to PlantManager for actual implementation.

        Args:
            parent_genome: The genome to inherit from (with mutations)
            parent_x: X position of parent plant
            parent_y: Y position of parent plant

        Returns:
            True if successfully sprouted, False if no space
        """
        if self.plant_manager is None:
            return False
        result = self.plant_manager.sprout_new_plant(
            parent_genome, parent_x, parent_y, self.entities_list
        )
        return result.is_ok()

    # Implement abstract methods from BaseSimulator
    def get_all_entities(self) -> List[entities.Agent]:
        """Get all entities in the simulation."""
        return self.entities_list

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation.
        
        For Fish entities, this respects population limits (max_population).
        Babies are not added if the tank is at carrying capacity.
        """
        # Check population limit for fish
        if isinstance(entity, entities.Fish):
            fish_count = sum(1 for e in self.entities_list if isinstance(e, entities.Fish))
            if self.ecosystem and fish_count >= self.ecosystem.max_population:
                # At max population - reject this fish
                # The energy invested in this baby is lost (population pressure)
                return
                
        if hasattr(entity, "add_internal"):
            entity.add_internal(self.agents)
        self.entities_list.append(entity)
        # Add to spatial grid incrementally
        if self.environment:
            self.environment.add_agent_to_grid(entity)
        # Prevent future plants from spawning under blocking obstacles
        if self.root_spot_manager:
            self.root_spot_manager.block_spots_for_entity(entity, padding=10.0)
        # Invalidate cached lists
        self._cache_manager.invalidate_entity_caches("entity added")

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation."""
        if entity in self.entities_list:
            # Ensure fractal plant root spots are released even when removed externally
            if isinstance(entity, Plant):
                entity.die()
            self.entities_list.remove(entity)
            # Remove from spatial grid incrementally
            if self.environment:
                self.environment.remove_agent_from_grid(entity)
            # Return Food to pool for reuse
            if isinstance(entity, entities.Food):
                self.food_pool.release(entity)
            # Invalidate cached lists
            self._cache_manager.invalidate_entity_caches("entity removed")

    def get_fish_list(self) -> List[entities.Fish]:
        """Get cached list of all fish in the simulation.

        Returns:
            List of Fish entities, cached to avoid repeated filtering
        """
        return self._cache_manager.get_fish()

    def get_food_list(self) -> List[entities.Food]:
        """Get cached list of all food in the simulation.

        Returns:
            List of Food entities, cached to avoid repeated filtering
        """
        return self._cache_manager.get_food()

    def _rebuild_caches(self) -> None:
        """Rebuild all cached entity lists if needed."""
        self._cache_manager.rebuild_if_needed()

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
        super().handle_poker_result(poker)
        self.poker_system.handle_poker_result(poker)

    def handle_mixed_poker_games(self) -> None:
        """Delegate mixed poker games to the poker system."""
        self.poker_system.handle_mixed_poker_games()

    def update(self) -> None:
        """Update the state of the simulation.

        The update loop executes in well-defined phases (see UpdatePhase enum):
        1. FRAME_START: Reset counters, increment frame
        2. TIME_UPDATE: Advance day/night cycle
        3. ENVIRONMENT: Update ecosystem and detection modifiers
        4. ENTITY_ACT: Update all entities
        5. LIFECYCLE: Process deaths, add/remove entities
        6. SPAWN: Auto-spawn food
        7. COLLISION: Handle collisions
        8. REPRODUCTION: Handle mating
        9. FRAME_END: Update stats, rebuild caches

        Performance optimizations:
        - Type-specific entity lists avoid repeated isinstance() checks
        - Batch spatial grid updates at end of frame
        - Pre-fetch entity type classes to avoid repeated attribute access
        """
        if self.paused:
            return

        if self._system_registry and self._system_registry.should_run_registered_systems:
            self._current_phase = UpdatePhase.FRAME_START
            self.frame_count += 1
            self._system_registry.run_registered_systems(self.frame_count)
            self._current_phase = None
            return

        # ===== PHASE: FRAME_START =====
        self._current_phase = UpdatePhase.FRAME_START
        self.frame_count += 1

        # Update lifecycle system first to reset per-frame counters
        self.lifecycle_system.update(self.frame_count)

        # Enforce the invariant: at most one Plant per RootSpot.
        # Delegates to PlantManager which tracks its own interval.
        if self.plant_manager is not None:
            self.plant_manager.reconcile_plants(self.entities_list, self.frame_count)

        # ===== PHASE: TIME_UPDATE =====
        self._current_phase = UpdatePhase.TIME_UPDATE
        self.time_system.update(self.frame_count)
        time_modifier = self.time_system.get_activity_modifier()
        time_of_day = self.time_system.get_time_of_day()

        # ===== PHASE: ENVIRONMENT =====
        self._current_phase = UpdatePhase.ENVIRONMENT
        # Advance ecosystem frame early so any energy/events recorded during this frame
        # are attributed to the correct frame number.
        ecosystem = self.ecosystem
        if ecosystem is not None:
            ecosystem.update(self.frame_count)

        # Performance: Update cached detection modifier once per frame
        if self.environment is not None:
            self.environment.update_detection_modifier()

        # ===== PHASE: ENTITY_ACT =====
        self._current_phase = UpdatePhase.ENTITY_ACT
        new_entities: List[entities.Agent] = []
        entities_to_remove: List[entities.Agent] = []

        # Performance: Pre-fetch type references to avoid repeated module lookups
        Fish = entities.Fish
        Food = entities.Food
        LiveFood = entities.LiveFood

        # Performance: Cache fish_count lookup once
        fish_count = len(self.get_fish_list()) if ecosystem is not None else 0

        # Performance: Iterate a copy but use type ID comparison when possible
        for entity in list(self.entities_list):

            # Standardized update call
            result = entity.update(self.frame_count, time_modifier, time_of_day)

            # Handle spawned entities (reproduction, food drops, nectar)
            if result.spawned_entities:
                for spawned in result.spawned_entities:
                    # Special handling for Fish reproduction (population cap)
                    if isinstance(spawned, Fish):
                        if ecosystem is not None and ecosystem.can_reproduce(fish_count):
                            spawned.register_birth()
                            new_entities.append(spawned)
                            fish_count += 1
                            self.lifecycle_system.record_birth()
                    else:
                        # Plants, Food, Nectar - just add them
                        new_entities.append(spawned)

            # Handle events (if any)
            # Currently we don't have events implementation fully wired in SimulationEngine
            # but this is where we would process result.events

            # Handle death
            if entity.is_dead():
                if isinstance(entity, Fish):
                    self.record_fish_death(entity)
                elif isinstance(entity, Plant):
                    entity.die()  # Release root spot
                    entities_to_remove.append(entity)
                    logger.debug(f"Plant #{entity.plant_id} died at age {entity.age}")
                elif isinstance(entity, PlantNectar):
                     # Nectar consumed or invalid
                     entities_to_remove.append(entity)

            # Handle removal conditions for Food
            elif isinstance(entity, Food):
                 if isinstance(entity, LiveFood):
                     if entity.is_expired():
                         entities_to_remove.append(entity)
                 else:
                     # Standard food sinks
                     env_height = (
                         getattr(self.environment, "height", None) or self._display_height
                     )
                     if entity.pos.y >= env_height - entity.height:
                         entities_to_remove.append(entity)

            self.keep_entity_on_screen(entity)

        # ===== PHASE: LIFECYCLE =====
        self._current_phase = UpdatePhase.LIFECYCLE
        # Batch entity removals (more efficient than removing during iteration)
        for entity in entities_to_remove:
            self.remove_entity(entity)

        # Clean up dying fish whose death effect timer has expired
        self.cleanup_dying_fish()

        for new_entity in new_entities:
            self.add_entity(new_entity)

        # ===== PHASE: SPAWN =====
        self._current_phase = UpdatePhase.SPAWN
        # Delegate to food spawning system (respects AUTO_FOOD_ENABLED internally)
        self.food_spawning_system.update(self.frame_count)

        # Performance: Update spatial grid incrementally for entities that moved
        # This is O(k) where k = moved entities, not O(n)
        if self.environment is not None:
            update_position = self.environment.update_agent_position
            for entity in self.entities_list:
                update_position(entity)

        # ===== PHASE: COLLISION =====
        self._current_phase = UpdatePhase.COLLISION
        # Uses spatial grid for efficiency
        self.handle_collisions()

        # ===== PHASE: REPRODUCTION =====
        self._current_phase = UpdatePhase.REPRODUCTION
        # Mate finding (Legacy/Poker based reproduction handling)
        self.handle_reproduction()

        if ecosystem is not None:
            # Auto-spawn fish based on population level (more likely at low populations).
            # Do this BEFORE taking the energy snapshot so the snapshot matches true end-of-frame state.
            fish_list = self.get_fish_list()
            fish_count = len(fish_list)
            if fish_count < self._max_population:
                frames_since_last_spawn = self.frame_count - self.last_emergency_spawn_frame
                if frames_since_last_spawn >= self._emergency_spawn_cooldown:
                    if fish_count < self._critical_population_threshold:
                        spawn_probability = 1.0
                    else:
                        population_ratio = (fish_count - self._critical_population_threshold) / (
                            self._max_population - self._critical_population_threshold
                        )
                        spawn_probability = (1.0 - population_ratio) ** 2 * 0.3

                    if self.rng.random() < spawn_probability:
                        self.spawn_emergency_fish()
                        self.last_emergency_spawn_frame = self.frame_count
                        fish_list = self.get_fish_list()
                        if fish_count < CRITICAL_POPULATION_THRESHOLD:
                            # Only log at INFO level when population is critically low
                            logger.info(f"Emergency fish spawned! fish_count now: {len(fish_list)}")

            # Update population stats based on end-of-frame state (including emergency spawns)
            ecosystem.update_population_stats(fish_list)

            # Cleanup dead fish stats periodically (every ~30s) to prevent memory leaks
            if self.frame_count % 1000 == 0:
                alive_ids = {f.fish_id for f in fish_list}
                ecosystem.cleanup_dead_fish(alive_ids)

            # Record energy snapshot for delta calculations (end-of-frame fish energy)
            # Include overflow_energy_bank since it's still fish energy, just stored differently
            total_fish_energy = sum(
                f.energy + f._reproduction_component.overflow_energy_bank
                for f in fish_list
            )
            ecosystem.record_energy_snapshot(total_fish_energy, len(fish_list))

        # ===== PHASE: FRAME_END =====
        self._current_phase = UpdatePhase.FRAME_END

        # Periodic poker benchmark evaluation
        if self.benchmark_evaluator is not None:
            fish_list = self.get_fish_list()
            self.benchmark_evaluator.maybe_run(self.frame_count, fish_list)

        # Rebuild caches at end of frame if dirty
        if self._cache_manager.is_dirty:
            self._rebuild_caches()

        # Clear phase tracking at end of frame
        self._current_phase = None


    def spawn_emergency_fish(self) -> None:
        """Spawn a new fish when population drops below critical threshold.

        This emergency spawning helps maintain genetic diversity and
        prevents population extinction.
        """
        if self.environment is None or self.ecosystem is None:
            return

        # With composable behaviors (1,152+ combinations), random spawns are naturally diverse
        # No need for explicit diversity tracking - each random genome will have unique sub-behaviors
        genome = Genome.random(use_algorithm=True, rng=self.rng)

        # Random spawn position (avoid edges)
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds
        margin = self._spawn_margin_pixels
        x = self.rng.randint(int(min_x) + margin, int(max_x) - margin)
        y = self.rng.randint(int(min_y) + margin, int(max_y) - margin)

        # Create the new fish
        new_fish = entities.Fish(
            self.environment,
            movement_strategy.AlgorithmicMovement(),
            self._files["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,  # Reset generation for emergency spawns
            ecosystem=self.ecosystem,
        )
        new_fish.register_birth()
        self.lifecycle_system.record_emergency_spawn()

        self.add_entity(new_fish)

    def _add_poker_event_to_history(
        self,
        winner_id: int,
        loser_id: int,
        winner_hand: str,
        loser_hand: str,
        energy_transferred: float,
        message: str,
    ) -> None:
        """Helper method that delegates to the poker system."""

        self.poker_system._add_poker_event_to_history(
            winner_id,
            loser_id,
            winner_hand,
            loser_hand,
            energy_transferred,
            message,
        )

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Delegate event creation to the poker system."""

        self.poker_system.add_poker_event(poker)

    def get_recent_poker_events(
        self, max_age_frames: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        age = max_age_frames or self.poker_event_max_age_frames
        return self.poker_system.get_recent_poker_events(age)

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Delegates to StatsCalculator service for cleaner separation of concerns.

        Returns:
            Dictionary with simulation stats
        """
        return self.stats_calculator.get_stats()

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive simulation statistics to JSON file for LLM analysis."""

        self.stats_exporter.export_stats_json(filename)

    def print_stats(self) -> None:
        """Print current simulation statistics to console."""
        stats = self.get_stats()

        logger.info("")
        logger.info("=" * self._separator_width)
        logger.info(f"Frame: {stats.get('frame_count', 0)}")
        logger.info(f"Time: {stats.get('time_string', 'N/A')}")
        logger.info(f"Real Time: {stats.get('elapsed_real_time', 0):.1f}s")
        logger.info(f"Simulation Speed: {stats.get('simulation_speed', 0):.2f}x")
        logger.info("-" * self._separator_width)
        max_pop = self.ecosystem.max_population if self.ecosystem else "N/A"
        logger.info(f"Population: {stats.get('total_population', 0)}/{max_pop}")
        logger.info(f"Generation: {stats.get('current_generation', 0)}")
        logger.info(f"Total Births: {stats.get('total_births', 0)}")
        logger.info(f"Total Deaths: {stats.get('total_deaths', 0)}")
        logger.info(f"Capacity: {stats.get('capacity_usage', 'N/A')}")
        logger.info("-" * self._separator_width)
        logger.info(f"Fish: {stats.get('fish_count', 0)}")
        logger.info(f"Food: {stats.get('food_count', 0)}")
        logger.info(f"Plants: {stats.get('plant_count', 0)}")

        # Death causes
        death_causes = stats.get("death_causes", {})
        if death_causes:
            logger.info("-" * self._separator_width)
            logger.info("Death Causes:")
            for cause, count in death_causes.items():
                logger.info(f"  {cause}: {count}")

        # Reproduction stats
        repro_stats = stats.get("reproduction_stats", {})
        if repro_stats:
            logger.info("-" * self._separator_width)
            logger.info("Reproduction Stats:")
            logger.info(f"  Total Reproductions: {repro_stats.get('total_reproductions', 0)}")
            logger.info(f"  Mating Attempts: {repro_stats.get('total_mating_attempts', 0)}")
            logger.info(f"  Failed Attempts: {repro_stats.get('total_failed_attempts', 0)}")
            logger.info(f"  Success Rate: {repro_stats.get('success_rate_pct', 'N/A')}")
            logger.info(f"  Currently Pregnant: {repro_stats.get('current_pregnant_fish', 0)}")
            logger.info(f"  Total Offspring: {repro_stats.get('total_offspring', 0)}")

        # Genetic diversity stats
        diversity_stats = stats.get("diversity_stats", {})
        if diversity_stats:
            logger.info("-" * self._separator_width)
            logger.info("Genetic Diversity:")
            logger.info(
                f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/{self._total_algorithm_count}"
            )
            logger.info(
                f"  Unique Species: {diversity_stats.get('unique_species', 0)}/{self._total_species_count}"
            )
            logger.info(f"  Diversity Score: {diversity_stats.get('diversity_score_pct', 'N/A')}")
            logger.info(f"  Color Variance: {diversity_stats.get('color_variance', 0):.4f}")
            logger.info(f"  Speed Variance: {diversity_stats.get('speed_variance', 0):.4f}")
            logger.info(f"  Size Variance: {diversity_stats.get('size_variance', 0):.4f}")
            logger.info(f"  Vision Variance: {diversity_stats.get('vision_variance', 0):.4f}")

        logger.info("=" * self._separator_width)

    def run_headless(
        self,
        max_frames: int = 10000,
        stats_interval: int = 300,
        export_json: Optional[str] = None,
    ) -> None:
        """Run the simulation in headless mode without visualization.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames
            export_json: Optional filename to export JSON stats for LLM analysis
        """
        logger.info("=" * self._separator_width)
        logger.info("HEADLESS FISH TANK SIMULATION")
        logger.info("=" * self._separator_width)
        logger.info(
            f"Running for {max_frames} frames ({max_frames / self._frame_rate:.1f} seconds of sim time)"
        )
        logger.info(f"Stats will be printed every {stats_interval} frames")
        if export_json:
            logger.info(f"Stats will be exported to: {export_json}")
        logger.info("=" * self._separator_width)

        self.setup()

        for frame in range(max_frames):
            self.update()

            # Print stats periodically
            if frame > 0 and frame % stats_interval == 0:
                self.print_stats()

        # Print final stats
        logger.info("")
        logger.info("=" * self._separator_width)
        logger.info("SIMULATION COMPLETE - Final Statistics")
        logger.info("=" * self._separator_width)
        self.print_stats()

        # Generate algorithm performance report if available
        if self.ecosystem is not None:
            logger.info("")
            logger.info("=" * self._separator_width)
            logger.info("GENERATING ALGORITHM PERFORMANCE REPORT...")
            logger.info("=" * self._separator_width)
            report = self.ecosystem.get_algorithm_performance_report()
            logger.info(f"{report}")

            # Save to file
            os.makedirs("logs", exist_ok=True)
            report_path = os.path.join("logs", "algorithm_performance_report.txt")
            with open(report_path, "w") as f:
                f.write(report)
            logger.info("")
            logger.info(f"Report saved to: {report_path}")

            # Export JSON stats if requested
            if export_json:
                logger.info("")
                logger.info("=" * self._separator_width)
                logger.info("EXPORTING JSON STATISTICS FOR LLM ANALYSIS...")
                logger.info("=" * self._separator_width)
                self.export_stats_json(export_json)

    def run_collect_stats(self, max_frames: int = 100) -> Dict[str, Any]:
        """Run the engine for `max_frames` frames and return final stats.

        This convenience method is designed for unit tests and deterministic
        runs where the caller wants the resulting stats as a dictionary.
        """
        self.setup()
        for _ in range(max_frames):
            self.update()
        return self.get_stats()

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
        super().__init__(headless=True)
        self.max_frames = max_frames
        self.stats_interval = stats_interval if stats_interval > 0 else max_frames + 1

    def run(self) -> None:
        """Run the simulation for the configured number of frames."""
        self.run_headless(max_frames=self.max_frames, stats_interval=self.stats_interval)
