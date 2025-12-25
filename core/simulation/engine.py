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

4. Backward compatibility is maintained - all the old methods still work,
   they just delegate to the appropriate manager.

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

import logging
import os
import random
import time
import uuid
from typing import Any, Dict, List, Optional

from core import entities, environment, movement_strategy
from core.agents_wrapper import AgentsWrapper
from core.collision_system import CollisionSystem
from core.config.simulation_config import SimulationConfig
from core.ecosystem import EcosystemManager
from core.entities.plant import Plant, PlantNectar
from core.simulation import diagnostics

from core.entity_factory import create_initial_population
from core.genetics import Genome, PlantGenome
from core.plant_manager import PlantManager
from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
from core.poker_interaction import PokerInteraction
from core.poker_system import PokerSystem
from core.reproduction_system import ReproductionSystem
from core.root_spots import RootSpotManager
from core.services.stats_calculator import StatsCalculator
from core.simulation.entity_manager import EntityManager
from core.simulation.system_registry import SystemRegistry


from core.systems.base import BaseSystem
from core.systems.entity_lifecycle import EntityLifecycleSystem
from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig
from core.time_system import TimeSystem
from core.update_phases import PHASE_DESCRIPTIONS, UpdatePhase

logger = logging.getLogger(__name__)


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
        config: Optional[SimulationConfig] = None,
        *,
        headless: Optional[bool] = None,
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
        enable_poker_benchmarks: Optional[bool] = None,
    ) -> None:
        """Initialize the simulation engine.

        Args:
            config: Aggregate simulation configuration
            headless: Override headless mode (for backward compatibility)
            rng: Shared random number generator for deterministic runs
            seed: Optional seed (used if rng is not provided)
            enable_poker_benchmarks: Override poker benchmark toggle
        """
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

        # RNG handling: prefer explicit rng, then seed, then fresh RNG
        # IMPORTANT: Also seed the global random module for determinism
        # This ensures code that falls back to `random` (not rng) is still deterministic
        if rng is not None:
            self.rng: random.Random = rng
            self.seed = None
        elif seed is not None:
            self.rng = random.Random(seed)
            self.seed = seed
            # Seed global random for code that falls back to global random
            random.seed(seed)
        else:
            self.rng = random.Random()
            self.seed = None

        # Observability: Unique identifier for this simulation run
        self.run_id: str = str(uuid.uuid4())
        logger.info(f"SimulationEngine initialized with run_id={self.run_id}")

        # Entity management (delegated to EntityManager)
        self._entity_manager = EntityManager(
            rng=self.rng,
            get_environment=lambda: self.environment,
            get_ecosystem=lambda: self.ecosystem,
            get_root_spot_manager=lambda: self.root_spot_manager,
        )

        # Backward compatibility: expose entities_list
        # This is a property that delegates to EntityManager
        self.agents = AgentsWrapper(self)

        # System registry (delegated to SystemRegistry)
        self._system_registry = SystemRegistry()

        # Core state
        self.environment: Optional[environment.Environment] = None
        self.ecosystem: Optional[EcosystemManager] = None
        self.time_system: TimeSystem = TimeSystem(self)
        self.start_time: float = time.time()


        # NOTE: EventBus was removed as dead code. It subscribed to events
        # that were never emitted, and emitted events with no subscribers.
        # If we need pub/sub in the future, re-add it with actual use cases.

        # Systems - initialized here, registered in setup()
        self.collision_system = CollisionSystem(self)
        self.reproduction_system = ReproductionSystem(self)
        self.poker_system = PokerSystem(self, max_events=self.config.poker.max_poker_events)
        self.poker_system.enabled = self.config.server.poker_activity_enabled
        self.poker_events = self.poker_system.poker_events
        self.lifecycle_system = EntityLifecycleSystem(self)

        # Food spawning (initialized in setup after environment exists)
        self.food_spawning_system: Optional[FoodSpawningSystem] = None

        # Plant management (initialized in setup)
        self.plant_manager: Optional[PlantManager] = None

        # Periodic poker benchmark evaluation
        self.benchmark_evaluator: Optional[PeriodicBenchmarkEvaluator] = None
        if self.config.poker.enable_periodic_benchmarks:
            self.benchmark_evaluator = PeriodicBenchmarkEvaluator(
                self.config.poker.benchmark_config
            )

        # Services
        self.stats_calculator = StatsCalculator(self)


        # Phase tracking for debugging
        self._current_phase: Optional[UpdatePhase] = None
        self._phase_debug_enabled: bool = self.config.enable_phase_debug

    # =========================================================================
    # Properties for Backward Compatibility
    # =========================================================================

    @property
    def entities_list(self) -> List[entities.Agent]:
        """All entities in the simulation (delegates to EntityManager)."""
        return self._entity_manager.entities_list

    @property
    def food_pool(self):
        """Food object pool (delegates to EntityManager)."""
        return self._entity_manager.food_pool

    @property
    def root_spot_manager(self) -> Optional[RootSpotManager]:
        """Backward-compatible access to root spot manager via PlantManager."""
        if self.plant_manager is None:
            return None
        return self.plant_manager.root_spot_manager

    # =========================================================================
    # Setup
    # =========================================================================

    def setup(self) -> None:
        """Setup the simulation."""
        display = self.config.display
        eco_config = self.config.ecosystem

        # Initialize environment
        self.environment = environment.Environment(
            self._entity_manager.entities_list,
            display.screen_width,
            display.screen_height,
            self.time_system,
            rng=self.rng,
        )

        # Initialize ecosystem manager
        self.ecosystem = EcosystemManager(max_population=eco_config.max_population)

        # Initialize plant management
        if self.config.server.plants_enabled:
            self.plant_manager = PlantManager(
                environment=self.environment,
                ecosystem=self.ecosystem,
                entity_adder=self,
                rng=self.rng,
            )

        # Initialize food spawning system
        self.food_spawning_system = FoodSpawningSystem(
            self,
            rng=self.rng,
            spawn_rate_config=self._build_spawn_rate_config(),
            auto_food_enabled=self.config.food.auto_food_enabled,
            display_config=display,
        )

        # Register systems in execution order
        self._system_registry.register(self.lifecycle_system)
        self._system_registry.register(self.time_system)
        self._system_registry.register(self.food_spawning_system)
        self._system_registry.register(self.collision_system)
        self._system_registry.register(self.reproduction_system)
        self._system_registry.register(self.poker_system)


        # Create initial entities
        self.create_initial_entities()

        # Create initial fractal plants
        if self.plant_manager is not None:
            self._block_root_spots_with_obstacles()
            self.plant_manager.create_initial_plants(self._entity_manager.entities_list)

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

    def get_systems(self) -> List[BaseSystem]:
        """Get all registered systems in execution order."""
        return self._system_registry.get_all()

    # Also expose via private attribute for backward compat
    @property
    def _systems(self) -> List[BaseSystem]:
        """Backward compatible access to systems list."""
        return self._system_registry.get_all()

    def get_system(self, name: str) -> Optional[BaseSystem]:
        """Get a system by name."""
        return self._system_registry.get(name)

    def get_systems_debug_info(self) -> Dict[str, Any]:
        """Get debug information from all registered systems."""
        return self._system_registry.get_debug_info()

    def set_system_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a system by name."""
        return self._system_registry.set_enabled(name, enabled)


    # =========================================================================
    # Phase Tracking
    # =========================================================================

    def get_current_phase(self) -> Optional[UpdatePhase]:
        """Get the current update phase (None if not in update loop)."""
        return self._current_phase

    def get_phase_description(self, phase: Optional[UpdatePhase] = None) -> str:
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
        """Create initial entities in the fish tank with multiple species."""
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

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def keep_entity_on_screen(
        self, entity: entities.Agent, screen_width: Optional[int] = None, screen_height: Optional[int] = None
    ) -> None:
        """Keep an entity fully within the bounds of the screen.

        Args:
            entity: Entity to constrain
            screen_width: Optional override for screen width
            screen_height: Optional override for screen height
        """
        w = screen_width if screen_width is not None else self.config.display.screen_width
        h = screen_height if screen_height is not None else self.config.display.screen_height

        # Clamp horizontally
        if entity.pos.x < 0:
            entity.pos.x = 0
        elif entity.pos.x + entity.width > w:
            entity.pos.x = w - entity.width

        # Clamp vertically
        if entity.pos.y < 0:
            entity.pos.y = 0
        elif entity.pos.y + entity.height > h:
            entity.pos.y = h - entity.height

    def get_all_entities(self) -> List[entities.Agent]:
        """Get all entities in the simulation."""
        return self._entity_manager.entities_list

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation."""
        if hasattr(entity, "add_internal"):
            entity.add_internal(self.agents)
        self._entity_manager.add(entity)

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation."""
        self._entity_manager.remove(entity)

    def get_fish_list(self) -> List[entities.Fish]:
        """Get cached list of all fish in the simulation."""
        return self._entity_manager.get_fish()

    def get_food_list(self) -> List[entities.Food]:
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

    def record_fish_death(self, fish: entities.Agent, cause: Optional[str] = None) -> None:
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

        The update loop executes in well-defined phases (see UpdatePhase enum).
        Each phase is implemented as a separate method for readability and testability.

        Phase Order:
            1. FRAME_START: Reset counters, increment frame
            2. TIME_UPDATE: Advance day/night cycle
            3. ENVIRONMENT: Update ecosystem and detection modifiers
            4. ENTITY_ACT: Update all entities, collect spawns/deaths
            5. LIFECYCLE: Process deaths, add/remove entities
            6. SPAWN: Auto-spawn food
            7. COLLISION: Handle collisions
            8. REPRODUCTION: Handle mating and emergency spawns
            9. FRAME_END: Update stats, rebuild caches
        """
        if self.paused:
            return

        # Execute each phase in order
        # Time values are returned from TIME_UPDATE and passed to ENTITY_ACT
        self._phase_frame_start()
        time_modifier, time_of_day = self._phase_time_update()
        self._phase_environment()
        new_entities, entities_to_remove = self._phase_entity_act(time_modifier, time_of_day)
        self._phase_lifecycle(new_entities, entities_to_remove)
        self._phase_spawn()
        self._phase_collision()
        self._phase_reproduction()
        self._phase_frame_end()

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

    def _phase_entity_act(
        self, time_modifier: float, time_of_day: float
    ) -> tuple:
        """ENTITY_ACT: Update all entities, collect spawns/deaths.
        
        Args:
            time_modifier: Activity modifier from day/night cycle
            time_of_day: Current time of day (0-1)
            
        Returns:
            Tuple of (new_entities, entities_to_remove)
        """
        self._current_phase = UpdatePhase.ENTITY_ACT
        new_entities: List[entities.Agent] = []
        entities_to_remove: List[entities.Agent] = []

        # Performance: Pre-fetch type references
        Fish = entities.Fish

        ecosystem = self.ecosystem
        fish_count = len(self.get_fish_list()) if ecosystem is not None else 0

        for entity in list(self._entity_manager.entities_list):
            result = entity.update(self.frame_count, time_modifier, time_of_day)

            # Handle spawned entities
            if result.spawned_entities:
                for spawned in result.spawned_entities:
                    if isinstance(spawned, Fish):
                        if ecosystem is not None and ecosystem.can_reproduce(fish_count):
                            spawned.register_birth()
                            new_entities.append(spawned)
                            fish_count += 1
                            self.lifecycle_system.record_birth()
                    else:
                        new_entities.append(spawned)

            # Handle entity death
            if entity.is_dead():
                if isinstance(entity, Fish):
                    self.record_fish_death(entity)
                elif isinstance(entity, Plant):
                    entity.die()
                    entities_to_remove.append(entity)
                    logger.debug(f"Plant #{entity.plant_id} died at age {entity.age}")
                elif isinstance(entity, PlantNectar):
                    entities_to_remove.append(entity)

            # Note: Food removal (expiry, off-screen) is handled by LifecycleSystem
            # in _phase_lifecycle to keep removal logic in one place

            self.keep_entity_on_screen(entity)

        return new_entities, entities_to_remove

    def _phase_lifecycle(
        self,
        new_entities: List[entities.Agent],
        entities_to_remove: List[entities.Agent],
    ) -> None:
        """LIFECYCLE: Process deaths, add/remove entities.
        
        This phase is the SINGLE OWNER of entity removal logic:
        - Entities marked for removal in entity_act phase
        - Food expiry and off-screen removal
        - Fish death effect cleanup
        """
        self._current_phase = UpdatePhase.LIFECYCLE
        
        # Remove entities collected during entity_act phase
        for entity in entities_to_remove:
            self.remove_entity(entity)

        # Process food removal (expiry, off-screen) - LifecycleSystem owns this logic
        screen_height = self.config.display.screen_height
        for entity in list(self._entity_manager.entities_list):
            if isinstance(entity, entities.Food):
                self.lifecycle_system.process_food_removal(entity, screen_height)

        # Cleanup fish that finished their death animation
        self.cleanup_dying_fish()

        # Add new entities spawned during entity_act
        for new_entity in new_entities:
            self.add_entity(new_entity)

    def _phase_spawn(self) -> None:
        """SPAWN: Auto-spawn food and update spatial positions."""
        self._current_phase = UpdatePhase.SPAWN
        
        if self.food_spawning_system:
            self.food_spawning_system.update(self.frame_count)

        # Update spatial grid for moved entities
        if self.environment is not None:
            update_position = self.environment.update_agent_position
            for entity in self._entity_manager.entities_list:
                update_position(entity)

    def _phase_collision(self) -> None:
        """COLLISION: Handle collisions between entities.
        
        CollisionSystem now owns ALL collision logic including:
        - Fish-Food collisions (eating)
        - Fish-Crab collisions (predation)
        - Fish-Fish proximity for poker games
        - Food-Crab collisions
        """
        self._current_phase = UpdatePhase.COLLISION
        # CollisionSystem._do_update() handles all collision iteration
        self.collision_system.update(self.frame_count)
        # Mixed poker (fish-plant, plant-plant) handled by PokerSystem
        self.handle_mixed_poker_games()

    def _phase_reproduction(self) -> None:
        """REPRODUCTION: Handle mating and emergency spawns.

        Orchestration Note: The engine decides WHEN stats are recorded.
        The business logic (HOW) lives in EcosystemManager methods.
        This split is intentional - orchestration stays in engine.
        """
        self._current_phase = UpdatePhase.REPRODUCTION
        # ReproductionSystem now handles both mating and emergency spawns
        self.handle_reproduction()

        ecosystem = self.ecosystem
        if ecosystem is None:
            return

        fish_list = self.get_fish_list()

        # Delegate stats recording to EcosystemManager
        ecosystem.update_population_stats(fish_list)

        if self.frame_count % 1000 == 0:
            alive_ids = {f.fish_id for f in fish_list}
            ecosystem.cleanup_dead_fish(alive_ids)

        # Record energy snapshot for delta calculations
        total_fish_energy = sum(
            f.energy + f._reproduction_component.overflow_energy_bank
            for f in fish_list
        )
        ecosystem.record_energy_snapshot(total_fish_energy, len(fish_list))

    def _phase_frame_end(self) -> None:
        """FRAME_END: Update stats, rebuild caches."""
        self._current_phase = UpdatePhase.FRAME_END

        if self.benchmark_evaluator is not None:
            fish_list = self.get_fish_list()
            self.benchmark_evaluator.maybe_run(self.frame_count, fish_list)

        if self._entity_manager.is_dirty:
            self._rebuild_caches()

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

    def get_recent_poker_events(
        self, max_age_frames: Optional[int] = None
    ) -> List[Dict[str, Any]]:
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
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics."""
        return self.stats_calculator.get_stats()

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
        export_json: Optional[str] = None,
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

    def run_collect_stats(self, max_frames: int = 100) -> Dict[str, Any]:
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
