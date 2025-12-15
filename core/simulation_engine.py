"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without any visualization code.
"""

import logging
import os
import random
import time
from statistics import median
from typing import Any, Dict, List, Optional

from core.systems.base import BaseSystem

from core import entities, environment, movement_strategy
from core.algorithms import get_algorithm_index
from core.collision_system import CollisionSystem
from core.constants import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    CRITICAL_POPULATION_THRESHOLD,
    EMERGENCY_SPAWN_COOLDOWN,
    FILES,
    FRACTAL_PLANT_INITIAL_COUNT,
    FRACTAL_PLANT_MATURE_ENERGY,
    FRACTAL_PLANTS_ENABLED,
    FRAME_RATE,
    LIVE_FOOD_SPAWN_CHANCE,
    MAX_DIVERSITY_SPAWN_ATTEMPTS,
    MAX_POKER_EVENTS,
    MAX_POPULATION,
    POKER_EVENT_MAX_AGE_FRAMES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEPARATOR_WIDTH,
    SPAWN_MARGIN_PIXELS,
    TOTAL_ALGORITHM_COUNT,
    FISH_ADULT_SIZE,
)
from core.ecosystem import EcosystemManager
from core.entities.fractal_plant import FractalPlant, PlantNectar
from core.entity_factory import create_initial_population
from core.events import (
    EnergyChangedEvent,
    EntityBornEvent,
    EntityDiedEvent,
    EventBus,
    PokerGameEvent,
)
from core.fish_poker import PokerInteraction
from core.genetics import Genome
from core.object_pool import FoodPool
from core.plant_genetics import PlantGenome
from core.poker.evaluation.benchmark_eval import BenchmarkEvalConfig
from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
from core.poker_system import PokerSystem
from core.reproduction_system import ReproductionSystem
from core.root_spots import RootSpotManager
from core.services.stats_calculator import StatsCalculator
from core.simulation_stats_exporter import SimulationStatsExporter
from core.simulators.base_simulator import BaseSimulator
from core.systems.entity_lifecycle import EntityLifecycleSystem
from core.time_system import TimeSystem
from core.update_phases import UpdatePhase, PhaseContext, PhaseRunner, PHASE_DESCRIPTIONS

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
        headless: bool = True,
        rng: Optional[random.Random] = None,
        enable_poker_benchmarks: bool = False,
    ) -> None:
        """Initialize the simulation engine.

        Args:
            headless: If True, run without any visualization
            rng: Shared random number generator for deterministic runs
            enable_poker_benchmarks: If True, enable periodic benchmark evaluations
        """
        super().__init__()
        self.headless = headless
        self.rng: random.Random = rng or random.Random()
        self.entities_list: List[entities.Agent] = []
        self.agents = AgentsWrapper(self)
        self.environment: Optional[environment.Environment] = None
        self.time_system: TimeSystem = TimeSystem()
        self.start_time: float = time.time()
        self.last_emergency_spawn_frame: int = (
            -EMERGENCY_SPAWN_COOLDOWN
        )  # Allow immediate first spawn

        # Event bus for decoupled communication between components
        self.event_bus = EventBus()

        # Systems - all extend BaseSystem for consistent interface
        self.collision_system = CollisionSystem(self)
        self.reproduction_system = ReproductionSystem(self)
        self.poker_system = PokerSystem(self, max_events=MAX_POKER_EVENTS)
        self.poker_events = self.poker_system.poker_events
        self.lifecycle_system = EntityLifecycleSystem(self)

        # System Registry - maintains execution order and provides uniform management
        # Systems are registered in setup() once all dependencies are ready
        self._systems: List[BaseSystem] = []

        # Performance: Object pool for Food entities
        self.food_pool = FoodPool()

        # Performance: Cached entity type lists to avoid repeated filtering
        self._cached_fish_list: Optional[List[entities.Fish]] = None
        self._cached_food_list: Optional[List[entities.Food]] = None
        self._cache_dirty: bool = True
        # Fractal plant system
        self.root_spot_manager: Optional[RootSpotManager] = None

        # LLM beauty contest variants (kept in deterministic order)
        self._fractal_variants = [
            "cosmic_fern",
            "claude",
            "antigravity",
            "gpt",
            "gpt_codex",
            "sonnet",
            "gemini",
            "lsystem",
        ]

        # Periodic poker benchmark evaluation
        self.benchmark_evaluator: Optional[PeriodicBenchmarkEvaluator] = None
        if enable_poker_benchmarks:
            self.benchmark_evaluator = PeriodicBenchmarkEvaluator(
                BenchmarkEvalConfig()
            )

        # Services
        self.stats_calculator = StatsCalculator(self)

        # Telemetry
        self.stats_exporter = SimulationStatsExporter(self)

        # Phase tracking for debugging and monitoring
        self._current_phase: Optional[UpdatePhase] = None
        self._phase_debug_enabled: bool = False


    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize managers
        self.environment = environment.Environment(self.entities_list, SCREEN_WIDTH, SCREEN_HEIGHT, self.time_system)
        self.ecosystem = EcosystemManager(max_population=MAX_POPULATION)

        # Initialize fractal plant root spot manager
        if FRACTAL_PLANTS_ENABLED:
            self.root_spot_manager = RootSpotManager(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Register systems in execution order
        # Order matters: lifecycle first for per-frame reset, time affects behavior,
        # collisions before reproduction
        self._systems = [
            self.lifecycle_system,
            self.time_system,
            self.collision_system,
            self.reproduction_system,
            self.poker_system,
        ]

        # Wire up event bus subscriptions
        self._setup_event_subscriptions()

        self.create_initial_entities()

        # Create initial fractal plants
        if FRACTAL_PLANTS_ENABLED and self.root_spot_manager is not None:
            self._block_root_spots_with_obstacles()
            self.create_initial_fractal_plants()

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

        # Death events - could be used for logging/stats
        self.event_bus.subscribe(EntityDiedEvent, self._on_entity_died)

        # Birth events - could be used for logging/stats
        self.event_bus.subscribe(EntityBornEvent, self._on_entity_born)

        # Poker events - forward to poker stats
        self.event_bus.subscribe(PokerGameEvent, self._on_poker_game)

    def _on_energy_changed(self, event: EnergyChangedEvent) -> None:
        """Handle energy change events.

        Args:
            event: The energy change event
        """
        if self.ecosystem is not None and event.amount < 0:
            # Record energy burns to ecosystem
            self.ecosystem.record_energy_burn(event.source, abs(event.amount))

    def _on_entity_died(self, event: EntityDiedEvent) -> None:
        """Handle entity death events.

        Args:
            event: The entity death event
        """
        # Currently handled via direct calls, but this enables future
        # decoupling where entities emit events instead of calling
        # ecosystem methods directly
        pass

    def _on_entity_born(self, event: EntityBornEvent) -> None:
        """Handle entity birth events.

        Args:
            event: The entity birth event
        """
        # Currently handled via direct calls, but this enables future
        # decoupling where entities emit events instead of calling
        # ecosystem methods directly
        pass

    def _on_poker_game(self, event: PokerGameEvent) -> None:
        """Handle poker game completion events.

        Args:
            event: The poker game event
        """
        # Could be used to forward to poker stats manager
        # Currently poker system handles this directly
        pass

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
            self.environment, self.ecosystem, SCREEN_WIDTH, SCREEN_HEIGHT, rng=self.rng
        )
        for entity in population:
            self.agents.add(entity)

    def _block_root_spots_with_obstacles(self) -> None:
        """Prevent plants from spawning where static obstacles live."""

        if self.root_spot_manager is None:
            return

        for entity in self.entities_list:
            self.root_spot_manager.block_spots_for_entity(entity, padding=10.0)

    def _get_fractal_variant_counts(self) -> Dict[str, int]:
        """Count how many plants of each LLM variant are present."""

        counts = dict.fromkeys(self._fractal_variants, 0)
        for entity in self.entities_list:
            if isinstance(entity, FractalPlant):
                variant = getattr(entity.genome, "fractal_type", "lsystem")
                if variant not in counts:
                    counts[variant] = 0
                counts[variant] += 1
        return counts

    def _pick_balanced_variant(self, preferred_type: Optional[str] = None) -> str:
        """Pick a fractal variant that keeps the beauty contest balanced.

        The selection prefers underrepresented variants so every LLM gets
        spotlight time, while also making sure the requesting variant
        remains in the candidate pool to stay represented.

        Green lsystem plants get a 50% bias to maintain a verdant tank.
        """

        # 50% chance to pick green lsystem for a more natural look
        if self.rng.random() < 0.5:
            return "lsystem"

        counts = self._get_fractal_variant_counts()
        min_count = min(counts.values()) if counts else 0
        underrepresented = [v for v, c in counts.items() if c == min_count]

        candidates = underrepresented.copy()
        if preferred_type:
            # Ensure the caller's variant is never excluded from contention
            if preferred_type not in candidates:
                candidates.append(preferred_type)

        # Deterministic order for testing but still randomized selection
        return self.rng.choice(candidates)

    def _create_variant_genome(
        self, variant: str, parent_genome: Optional[PlantGenome] = None
    ) -> PlantGenome:
        """Create a genome for the selected variant, honoring lineage when possible."""

        variant_factories = {
            "cosmic_fern": PlantGenome.create_cosmic_fern_variant,
            "claude": PlantGenome.create_claude_variant,
            "antigravity": PlantGenome.create_antigravity_variant,
            "gpt": PlantGenome.create_gpt_variant,
            "gpt_codex": PlantGenome.create_gpt_codex_variant,
            "sonnet": PlantGenome.create_sonnet_variant,
            "gemini": PlantGenome.create_gemini_variant,
            "lsystem": PlantGenome.create_random,
        }

        if parent_genome and variant == parent_genome.fractal_type:
            return PlantGenome.from_parent(
                parent_genome,
                mutation_rate=0.15,
                mutation_strength=0.15,
                rng=self.rng,
            )

        factory = variant_factories.get(variant, PlantGenome.create_random)
        return factory(rng=self.rng)

    def create_initial_fractal_plants(self) -> None:
        """Create initial fractal plants at random root spots."""
        if self.root_spot_manager is None or self.environment is None:
            return

        for _ in range(FRACTAL_PLANT_INITIAL_COUNT):
            # Get a random empty root spot
            spot = self.root_spot_manager.get_random_empty_spot()
            if spot is None:
                break  # No more empty spots

            # LLM Battle: spawn diverse variants for the beauty contest
            # Prefer underrepresented variants so everyone gets spotlight
            variant = self._pick_balanced_variant()
            genome = self._create_variant_genome(variant)

            # Create the plant with full energy (mature)
            plant = FractalPlant(
                environment=self.environment,
                genome=genome,
                root_spot=spot,
                initial_energy=FRACTAL_PLANT_MATURE_ENERGY,
                ecosystem=self.ecosystem,
                screen_width=SCREEN_WIDTH,
                screen_height=SCREEN_HEIGHT,
            )

            # Claim the root spot
            spot.claim(plant)

            # Add to simulation
            self.add_entity(plant)

        logger.info(f"Created {self.root_spot_manager.get_occupied_count()} initial fractal plants")

    def sprout_new_plant(self, parent_genome: PlantGenome, parent_x: float, parent_y: float) -> bool:
        """Sprout a new fractal plant from a parent genome.

        Called when fish consumes plant nectar.

        Args:
            parent_genome: The genome to inherit from (with mutations)
            parent_x: X position of parent plant
            parent_y: Y position of parent plant

        Returns:
            True if successfully sprouted, False if no space
        """
        if self.root_spot_manager is None or self.environment is None:
            return False

        # Find a suitable spot near the parent
        spot = self.root_spot_manager.find_spot_for_sprouting(parent_x, parent_y)
        if spot is None:
            return False  # No available spots

        # Create offspring genome with mutations
        variant = self._pick_balanced_variant(preferred_type=parent_genome.fractal_type)
        offspring_genome = self._create_variant_genome(
            variant, parent_genome=parent_genome
        )

        # Create the new plant
        plant = FractalPlant(
            environment=self.environment,
            genome=offspring_genome,
            root_spot=spot,
            initial_energy=30.0,  # Start with enough energy to mature in reasonable time
            ecosystem=self.ecosystem,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
        )

        # Claim the root spot
        spot.claim(plant)

        # Add to simulation
        self.add_entity(plant)

        logger.debug(f"Sprouted new fractal plant #{plant.plant_id} at ({spot.x:.0f}, {spot.y:.0f})")
        return True

    # Implement abstract methods from BaseSimulator
    def get_all_entities(self) -> List[entities.Agent]:
        """Get all entities in the simulation."""
        return self.entities_list

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation."""
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
        self._cache_dirty = True

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation."""
        if entity in self.entities_list:
            # Ensure fractal plant root spots are released even when removed externally
            if isinstance(entity, FractalPlant):
                entity.die()
            self.entities_list.remove(entity)
            # Remove from spatial grid incrementally
            if self.environment:
                self.environment.remove_agent_from_grid(entity)
            # Return Food to pool for reuse
            if isinstance(entity, entities.Food):
                self.food_pool.release(entity)
            # Invalidate cached lists
            self._cache_dirty = True

    def get_fish_list(self) -> List[entities.Fish]:
        """Get cached list of all fish in the simulation.

        Returns:
            List of Fish entities, cached to avoid repeated filtering
        """
        if self._cache_dirty or self._cached_fish_list is None:
            self._cached_fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]
        return self._cached_fish_list

    def get_food_list(self) -> List[entities.Food]:
        """Get cached list of all food in the simulation.

        Returns:
            List of Food entities, cached to avoid repeated filtering
        """
        if self._cache_dirty or self._cached_food_list is None:
            self._cached_food_list = [e for e in self.entities_list if isinstance(e, entities.Food)]
        return self._cached_food_list

    def _rebuild_caches(self) -> None:
        """Rebuild all cached entity lists."""
        self._cached_fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]
        self._cached_food_list = [e for e in self.entities_list if isinstance(e, entities.Food)]
        self._cache_dirty = False

    def check_collision(self, e1: entities.Agent, e2: entities.Agent) -> bool:
        """Delegate collision detection to the collision system."""
        return self.collision_system.check_collision(e1, e2)

    def handle_fish_food_collision(self, fish: entities.Agent, food: entities.Agent) -> None:
        """Delegate fish-food collision handling to the collision system."""
        self.collision_system.handle_fish_food_collision(fish, food)

    def handle_reproduction(self) -> None:
        """Delegate reproduction handling to the reproduction system."""
        self.reproduction_system.handle_reproduction()

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Delegate poker result processing to the poker system."""
        self.poker_system.handle_poker_result(poker)

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

        # ===== PHASE: FRAME_START =====
        self._current_phase = UpdatePhase.FRAME_START
        self.frame_count += 1

        # Update lifecycle system first to reset per-frame counters
        self.lifecycle_system.update(self.frame_count)

        # ===== PHASE: TIME_UPDATE =====
        self._current_phase = UpdatePhase.TIME_UPDATE
        self.time_system.update()
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
        Plant = entities.Plant
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
                elif isinstance(entity, FractalPlant):
                    entity.die()  # Release root spot
                    entities_to_remove.append(entity)
                    logger.debug(f"FractalPlant #{entity.plant_id} died at age {entity.age}")
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
                     if entity.pos.y >= SCREEN_HEIGHT - entity.height:
                         entities_to_remove.append(entity)
            
            self.keep_entity_on_screen(entity)

        # ===== PHASE: LIFECYCLE =====
        self._current_phase = UpdatePhase.LIFECYCLE
        # Batch entity removals (more efficient than removing during iteration)
        for entity in entities_to_remove:
            self.remove_entity(entity)

        for new_entity in new_entities:
            self.add_entity(new_entity)

        # ===== PHASE: SPAWN =====
        self._current_phase = UpdatePhase.SPAWN
        if self.environment is not None:
            self.spawn_auto_food(self.environment, time_of_day)

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
            if fish_count < MAX_POPULATION:
                frames_since_last_spawn = self.frame_count - self.last_emergency_spawn_frame
                if frames_since_last_spawn >= EMERGENCY_SPAWN_COOLDOWN:
                    if fish_count < CRITICAL_POPULATION_THRESHOLD:
                        spawn_probability = 1.0
                    else:
                        population_ratio = (fish_count - CRITICAL_POPULATION_THRESHOLD) / (
                            MAX_POPULATION - CRITICAL_POPULATION_THRESHOLD
                        )
                        spawn_probability = (1.0 - population_ratio) ** 2 * 0.3

                    if self.rng.random() < spawn_probability:
                        self.spawn_emergency_fish()
                        self.last_emergency_spawn_frame = self.frame_count
                        fish_list = self.get_fish_list()

            # Update population stats based on end-of-frame state (including emergency spawns)
            ecosystem.update_population_stats(fish_list)

            # Cleanup dead fish stats periodically (every ~30s) to prevent memory leaks
            if self.frame_count % 1000 == 0:
                alive_ids = {f.fish_id for f in fish_list}
                ecosystem.cleanup_dead_fish(alive_ids)

            # Record energy snapshot for delta calculations (end-of-frame fish energy)
            total_fish_energy = sum(f.energy for f in fish_list)
            ecosystem.record_energy_snapshot(total_fish_energy, len(fish_list))

        # ===== PHASE: FRAME_END =====
        self._current_phase = UpdatePhase.FRAME_END

        # Periodic poker benchmark evaluation
        if self.benchmark_evaluator is not None:
            fish_list = self.get_fish_list()
            self.benchmark_evaluator.maybe_run(self.frame_count, fish_list)

        # Rebuild caches at end of frame if dirty
        if self._cache_dirty:
            self._rebuild_caches()

        # Clear phase tracking at end of frame
        self._current_phase = None

    def spawn_auto_food(self, environment: "environment.Environment", time_of_day: Optional[float] = None) -> None:
        """Spawn automatic food using object pooling for better performance.

        Override base implementation to use food pool.
        """
        if not AUTO_FOOD_ENABLED:
            return

        # Calculate total energy and population (use cached list)
        fish_list = self.get_fish_list()
        fish_count = len(fish_list)
        total_energy = sum(fish.energy for fish in fish_list)

        # Dynamic spawn rate based on population and energy levels
        spawn_rate = AUTO_FOOD_SPAWN_RATE

        # Priority 1: Emergency feeding when energy is critically low
        if total_energy < AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD:
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 4
        elif total_energy < AUTO_FOOD_LOW_ENERGY_THRESHOLD:
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 3
        # Priority 2: Reduce feeding when energy or population is high
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_2
        ):
            spawn_rate = AUTO_FOOD_SPAWN_RATE * 3
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_1
        ):
            spawn_rate = int(AUTO_FOOD_SPAWN_RATE * 1.67)

        self.auto_food_timer += 1
        if self.auto_food_timer >= spawn_rate:
            self.auto_food_timer = 0

            # Decide whether to spawn live food or regular food
            live_food_roll = self.rng.random()
            live_food_chance = LIVE_FOOD_SPAWN_CHANCE

            # Time-of-day effects: twilight peaks, darker nights slightly boost live food
            if time_of_day is None:
                time_of_day = self.time_system.get_time_of_day()

            is_dawn = 0.15 <= time_of_day < 0.35
            is_day = 0.35 <= time_of_day < 0.65
            is_dusk = 0.65 <= time_of_day < 0.85

            if is_dawn or is_dusk:
                live_food_chance = min(0.95, LIVE_FOOD_SPAWN_CHANCE * 2.2)
            elif self.time_system.is_night():
                live_food_chance = min(0.85, LIVE_FOOD_SPAWN_CHANCE * 1.6)
            elif is_day:
                live_food_chance = max(0.25, LIVE_FOOD_SPAWN_CHANCE * 0.9)

            if live_food_roll < live_food_chance:
                # Spawn live food at random position (not from pool - LiveFood is special)
                food_x = self.rng.randint(0, SCREEN_WIDTH)
                food_y = self.rng.randint(0, SCREEN_HEIGHT)
                food = entities.LiveFood(
                    environment,
                    food_x,
                    food_y,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
            else:
                # Use food pool for regular food (performance optimization)
                x = self.rng.randint(0, SCREEN_WIDTH)
                food = self.food_pool.acquire(
                    environment=environment,
                    x=x,
                    y=0,
                    source_plant=None,
                    allow_stationary_types=False,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
            self.add_entity(food)

    def spawn_emergency_fish(self) -> None:
        """Spawn a new fish when population drops below critical threshold.

        This emergency spawning helps maintain genetic diversity and
        prevents population extinction.
        """
        if self.environment is None or self.ecosystem is None:
            return

        # Get current fish to analyze diversity (use cached list)
        fish_list = self.get_fish_list()

        # If we have existing fish, try to spawn diverse genomes
        # Otherwise, spawn completely random
        if fish_list:
            # Get existing algorithms (as indices)
            existing_algorithms = set()
            existing_species = set()
            for fish in fish_list:
                if hasattr(fish, "genome") and hasattr(fish.genome, "behavior_algorithm"):
                    algo_idx = get_algorithm_index(fish.genome.behavior_algorithm)
                    if algo_idx >= 0:
                        existing_algorithms.add(algo_idx)
                if hasattr(fish, "species"):
                    existing_species.add(fish.species)

            # Create genome with an algorithm not currently in population (if possible)
            # This helps maintain diversity
            genome = Genome.random(use_algorithm=True, rng=self.rng)

            # Try to pick a different algorithm than existing ones (up to MAX_DIVERSITY_SPAWN_ATTEMPTS)
            for _ in range(MAX_DIVERSITY_SPAWN_ATTEMPTS):
                if hasattr(genome, "behavior_algorithm"):
                    algo_idx = get_algorithm_index(genome.behavior_algorithm)
                    if algo_idx >= 0 and algo_idx not in existing_algorithms:
                        break
                genome = Genome.random(use_algorithm=True, rng=self.rng)
        else:
            # No existing fish, spawn completely random
            genome = Genome.random(use_algorithm=True, rng=self.rng)

        # Random spawn position (avoid edges)
        x = self.rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS)
        y = self.rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS)

        # Create the new fish
        new_fish = entities.Fish(
            self.environment,
            movement_strategy.AlgorithmicMovement(),
            FILES["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,  # Reset generation for emergency spawns
            ecosystem=self.ecosystem,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
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
        self, max_age_frames: int = POKER_EVENT_MAX_AGE_FRAMES
    ) -> List[Dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        return self.poker_system.get_recent_poker_events(max_age_frames)

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
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info(f"Frame: {stats.get('frame_count', 0)}")
        logger.info(f"Time: {stats.get('time_string', 'N/A')}")
        logger.info(f"Real Time: {stats.get('elapsed_real_time', 0):.1f}s")
        logger.info(f"Simulation Speed: {stats.get('simulation_speed', 0):.2f}x")
        logger.info("-" * SEPARATOR_WIDTH)
        max_pop = self.ecosystem.max_population if self.ecosystem else "N/A"
        logger.info(f"Population: {stats.get('total_population', 0)}/{max_pop}")
        logger.info(f"Generation: {stats.get('current_generation', 0)}")
        logger.info(f"Total Births: {stats.get('total_births', 0)}")
        logger.info(f"Total Deaths: {stats.get('total_deaths', 0)}")
        logger.info(f"Capacity: {stats.get('capacity_usage', 'N/A')}")
        logger.info("-" * SEPARATOR_WIDTH)
        logger.info(f"Fish: {stats.get('fish_count', 0)}")
        logger.info(f"Food: {stats.get('food_count', 0)}")
        logger.info(f"Plants: {stats.get('plant_count', 0)}")

        # Death causes
        death_causes = stats.get("death_causes", {})
        if death_causes:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Death Causes:")
            for cause, count in death_causes.items():
                logger.info(f"  {cause}: {count}")

        # Reproduction stats
        repro_stats = stats.get("reproduction_stats", {})
        if repro_stats:
            logger.info("-" * SEPARATOR_WIDTH)
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
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Genetic Diversity:")
            logger.info(
                f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/{TOTAL_ALGORITHM_COUNT}"
            )
            logger.info(f"  Unique Species: {diversity_stats.get('unique_species', 0)}/4")
            logger.info(f"  Diversity Score: {diversity_stats.get('diversity_score_pct', 'N/A')}")
            logger.info(f"  Color Variance: {diversity_stats.get('color_variance', 0):.4f}")
            logger.info(f"  Speed Variance: {diversity_stats.get('speed_variance', 0):.4f}")
            logger.info(f"  Size Variance: {diversity_stats.get('size_variance', 0):.4f}")
            logger.info(f"  Vision Variance: {diversity_stats.get('vision_variance', 0):.4f}")

        logger.info("=" * SEPARATOR_WIDTH)

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
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("HEADLESS FISH TANK SIMULATION")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info(
            f"Running for {max_frames} frames ({max_frames / FRAME_RATE:.1f} seconds of sim time)"
        )
        logger.info(f"Stats will be printed every {stats_interval} frames")
        if export_json:
            logger.info(f"Stats will be exported to: {export_json}")
        logger.info("=" * SEPARATOR_WIDTH)

        self.setup()

        for frame in range(max_frames):
            self.update()

            # Print stats periodically
            if frame > 0 and frame % stats_interval == 0:
                self.print_stats()

        # Print final stats
        logger.info("")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("SIMULATION COMPLETE - Final Statistics")
        logger.info("=" * SEPARATOR_WIDTH)
        self.print_stats()

        # Generate algorithm performance report if available
        if self.ecosystem is not None:
            logger.info("")
            logger.info("=" * SEPARATOR_WIDTH)
            logger.info("GENERATING ALGORITHM PERFORMANCE REPORT...")
            logger.info("=" * SEPARATOR_WIDTH)
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
                logger.info("=" * SEPARATOR_WIDTH)
                logger.info("EXPORTING JSON STATISTICS FOR LLM ANALYSIS...")
                logger.info("=" * SEPARATOR_WIDTH)
                self.export_stats_json(export_json)


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
