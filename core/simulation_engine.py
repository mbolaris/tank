"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without any visualization code.
"""

import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

from core import entities, environment, movement_strategy
from core.algorithms import get_algorithm_index, get_algorithm_name
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
    FRACTAL_PLANT_INITIAL_ENERGY,
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
)
from core.collision_system import CollisionSystem
from core.ecosystem import EcosystemManager
from core.entities.fractal_plant import FractalPlant, PlantNectar
from core.entity_factory import create_initial_population
from core.fish_poker import PokerInteraction
from core.genetics import Genome
from core.object_pool import FoodPool
from core.poker_system import PokerSystem
from core.plant_genetics import PlantGenome
from core.registry import get_algorithm_metadata
from core.reproduction_system import ReproductionSystem
from core.root_spots import RootSpotManager
from core.simulators.base_simulator import BaseSimulator
from core.time_system import TimeSystem

logger = logging.getLogger(__name__)


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

    def __init__(self, headless: bool = True, rng: Optional[random.Random] = None) -> None:
        """Initialize the simulation engine.

        Args:
            headless: If True, run without any visualization
            rng: Shared random number generator for deterministic runs
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

        # Systems
        self.collision_system = CollisionSystem(self)
        self.reproduction_system = ReproductionSystem(self)
        self.poker_system = PokerSystem(self, max_events=MAX_POKER_EVENTS)
        self.poker_events = self.poker_system.poker_events

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


    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize managers
        self.environment = environment.Environment(self.entities_list, SCREEN_WIDTH, SCREEN_HEIGHT, self.time_system)
        self.ecosystem = EcosystemManager(max_population=MAX_POPULATION)

        # Initialize fractal plant root spot manager
        if FRACTAL_PLANTS_ENABLED:
            self.root_spot_manager = RootSpotManager(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.create_initial_entities()

        # Create initial fractal plants
        if FRACTAL_PLANTS_ENABLED and self.root_spot_manager is not None:
            self._block_root_spots_with_obstacles()
            self.create_initial_fractal_plants()

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

        counts = {variant: 0 for variant in self._fractal_variants}
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
            initial_energy=FRACTAL_PLANT_INITIAL_ENERGY * 0.5,  # Start smaller
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

        Performance optimizations:
        - Type-specific entity lists avoid repeated isinstance() checks
        - Batch spatial grid updates at end of frame
        - Pre-fetch entity type classes to avoid repeated attribute access
        """
        if self.paused:
            return

        self.frame_count += 1

        self.time_system.update()
        time_modifier = self.time_system.get_activity_modifier()
        time_of_day = self.time_system.get_time_of_day()

        # Performance: Update cached detection modifier once per frame
        if self.environment is not None:
            self.environment.update_detection_modifier()

        new_entities: List[entities.Agent] = []
        entities_to_remove: List[entities.Agent] = []

        # Performance: Pre-fetch type references to avoid repeated module lookups
        Fish = entities.Fish
        Plant = entities.Plant
        Jellyfish = entities.Jellyfish
        Food = entities.Food
        LiveFood = entities.LiveFood

        # Performance: Cache ecosystem and fish_count lookup once
        ecosystem = self.ecosystem
        fish_count = len(self.get_fish_list()) if ecosystem is not None else 0

        # Performance: Iterate a copy but use type ID comparison when possible
        for entity in list(self.entities_list):
            entity_type = type(entity)

            if entity_type is Fish or isinstance(entity, Fish):
                newborn = entity.update(self.frame_count, time_modifier)
                if newborn is not None and ecosystem is not None:
                    if ecosystem.can_reproduce(fish_count):
                        new_entities.append(newborn)
                        fish_count += 1  # Track new births within frame

                if entity.is_dead():
                    self.record_fish_death(entity)

            elif entity_type is Plant or isinstance(entity, Plant):
                food = entity.update(self.frame_count, time_modifier, time_of_day)
                if food is not None:
                    new_entities.append(food)

            elif entity_type is Jellyfish or isinstance(entity, Jellyfish):
                entity.update(self.frame_count)
                # Remove dead jellyfish
                if entity.is_dead():
                    entities_to_remove.append(entity)
                    logger.info(f"Jellyfish #{entity.jellyfish_id} died at age {entity.age}")

            elif FRACTAL_PLANTS_ENABLED and hasattr(entity, 'plant_id'):
                # FractalPlant handling
                if isinstance(entity, FractalPlant):
                    nectar = entity.update(self.frame_count, time_modifier, time_of_day)
                    if nectar is not None:
                        new_entities.append(nectar)

                    # Remove dead plants
                    if entity.is_dead():
                        entity.die()  # Release root spot
                        entities_to_remove.append(entity)
                        logger.debug(f"FractalPlant #{entity.plant_id} died at age {entity.age}")

                elif isinstance(entity, PlantNectar):
                    entity.update(self.frame_count)

                    # Check if nectar was consumed (handled in collision detection)
                    if entity.is_consumed():
                        entities_to_remove.append(entity)

            else:
                entity.update(self.frame_count)

            self.keep_entity_on_screen(entity)

            # Remove regular food that sinks to bottom, but NOT live food (which swims freely)
            # Performance: Use type() check first (fast) before isinstance() (slower)
            if entity_type is Food or (isinstance(entity, Food) and not isinstance(entity, LiveFood)):
                if entity.pos.y >= SCREEN_HEIGHT - entity.height:
                    entities_to_remove.append(entity)

        # Batch entity removals (more efficient than removing during iteration)
        for entity in entities_to_remove:
            self.remove_entity(entity)

        for new_entity in new_entities:
            self.add_entity(new_entity)

        if self.environment is not None:
            self.spawn_auto_food(self.environment, time_of_day)

        # Performance: Update spatial grid incrementally for entities that moved
        # This is O(k) where k = moved entities, not O(n)
        if self.environment is not None:
            update_position = self.environment.update_agent_position
            for entity in self.entities_list:
                update_position(entity)

        # Uses spatial grid for efficiency
        self.handle_collisions()

        # Mate finding
        self.handle_reproduction()

        if ecosystem is not None:
            # Use cached fish list for better performance
            fish_list = self.get_fish_list()
            ecosystem.update_population_stats(fish_list)
            ecosystem.update(self.frame_count)

            # Auto-spawn fish based on population level (more likely at low populations)
            fish_count = len(fish_list)
            if fish_count < MAX_POPULATION:
                frames_since_last_spawn = self.frame_count - self.last_emergency_spawn_frame
                if frames_since_last_spawn >= EMERGENCY_SPAWN_COOLDOWN:
                    # Calculate spawn probability: very high at low populations, low at high populations
                    # At 0 fish: 100% chance, at CRITICAL_POPULATION_THRESHOLD: ~50%, at MAX_POPULATION: 0%
                    if fish_count < CRITICAL_POPULATION_THRESHOLD:
                        # Emergency mode: always spawn
                        spawn_probability = 1.0
                    else:
                        # Gradual decrease: use inverse square for steeper drop-off
                        # population_ratio goes from 0 (at critical) to 1 (at max)
                        population_ratio = (fish_count - CRITICAL_POPULATION_THRESHOLD) / (MAX_POPULATION - CRITICAL_POPULATION_THRESHOLD)
                        # Inverse curve: high probability at low populations, drops quickly
                        spawn_probability = (1.0 - population_ratio) ** 2 * 0.3  # Max 30% at critical threshold

                    if self.rng.random() < spawn_probability:
                        self.spawn_emergency_fish()
                        self.last_emergency_spawn_frame = self.frame_count

        # Rebuild caches at end of frame if dirty
        if self._cache_dirty:
            self._rebuild_caches()

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

        self.add_entity(new_fish)


    def _add_poker_event_to_history(
        self,
        winner_id: int,
        loser_id: int,
        winner_hand: str,
        loser_hand: str,
        energy_transferred: float,
        message: str,
        is_jellyfish: bool,
    ) -> None:
        """Helper method that delegates to the poker system."""

        self.poker_system._add_poker_event_to_history(
            winner_id,
            loser_id,
            winner_hand,
            loser_hand,
            energy_transferred,
            message,
            is_jellyfish,
        )

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Delegate event creation to the poker system."""

        self.poker_system.add_poker_event(poker)

    def add_jellyfish_poker_event(
        self,
        fish_id: int,
        fish_won: bool,
        fish_hand: str,
        jellyfish_hand: str,
        energy_transferred: float,
    ) -> None:
        """Delegate jellyfish poker events to the poker system."""

        self.poker_system.add_jellyfish_poker_event(
            fish_id,
            fish_won,
            fish_hand,
            jellyfish_hand,
            energy_transferred,
        )

    def get_recent_poker_events(
        self, max_age_frames: int = POKER_EVENT_MAX_AGE_FRAMES
    ) -> List[Dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        return self.poker_system.get_recent_poker_events(max_age_frames)

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation stats
        """
        if self.ecosystem is None:
            return {}

        stats = self.ecosystem.get_summary_stats(self.get_all_entities())
        stats["frame_count"] = self.frame_count
        stats["time_string"] = self.time_system.get_time_string()
        stats["elapsed_real_time"] = time.time() - self.start_time
        stats["simulation_speed"] = (
            self.frame_count / (FRAME_RATE * (time.time() - self.start_time))
            if time.time() > self.start_time
            else 0
        )

        # Add entity counts (use cached lists)
        fish_list = self.get_fish_list()
        stats["fish_count"] = len(fish_list)
        stats["food_count"] = len(self.get_food_list())
        # Add separate fish and plant energy
        stats["fish_energy"] = sum(fish.energy for fish in fish_list)
        plant_list = [e for e in self.entities_list if isinstance(e, FractalPlant)]
        stats["plant_energy"] = sum(plant.energy for plant in plant_list)
        
        # Update plant count to include fractal plants
        regular_plants = len([e for e in self.entities_list if isinstance(e, entities.Plant)])
        stats["plant_count"] = regular_plants + len(plant_list)

        return stats

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive simulation statistics to JSON file for LLM analysis.

        This export is designed to be consumed by LLMs to:
        - Analyze which behavior algorithms are successful/unsuccessful
        - Identify patterns in survival, reproduction, and energy efficiency
        - Generate insights for creating new/improved algorithms
        - Track evolution of parameters over generations

        Args:
            filename: Output JSON file path
        """
        if self.ecosystem is None:
            logger.warning("Cannot export stats: ecosystem not initialized")
            return

        # Get algorithm source mapping for AI agent
        algorithm_metadata = get_algorithm_metadata()

        # Gather comprehensive stats
        export_data = {
            "simulation_metadata": {
                "total_frames": self.frame_count,
                "total_sim_time_seconds": self.frame_count / FRAME_RATE,
                "elapsed_real_time_seconds": time.time() - self.start_time,
                "simulation_speed_multiplier": (
                    self.frame_count / (FRAME_RATE * (time.time() - self.start_time))
                    if time.time() > self.start_time
                    else 0
                ),
                "max_population": self.ecosystem.max_population,
            },
            "population_summary": {
                "total_births": self.ecosystem.total_births,
                "total_deaths": self.ecosystem.total_deaths,
                "current_generation": self.ecosystem.current_generation,
                "final_population": len(self.get_fish_list()),
            },
            "death_causes": dict(self.ecosystem.death_causes),
            "algorithm_registry": algorithm_metadata,
            "algorithm_performance": {},
            "poker_statistics": {},
            "generation_trends": [],
            "recommendations": {
                "top_performers": [],
                "worst_performers": [],
                "extinct_algorithms": [],
            },
        }

        # Export per-algorithm performance stats
        for algo_id, stats in self.ecosystem.algorithm_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            # Get source file info from registry
            metadata = algorithm_metadata.get(algo_name, {})
            source_file = metadata.get("source_file", "unknown")
            category = metadata.get("category", "unknown")

            export_data["algorithm_performance"][algo_name] = {
                "algorithm_id": algo_id,
                "source_file": source_file,
                "category": category,
                "total_births": stats.total_births,
                "total_deaths": stats.total_deaths,
                "current_population": stats.current_population,
                "avg_lifespan_frames": stats.get_avg_lifespan(),
                "survival_rate": stats.get_survival_rate(),
                "reproduction_rate": stats.get_reproduction_rate(),
                "total_reproductions": stats.total_reproductions,
                "total_food_eaten": stats.total_food_eaten,
                "death_breakdown": {
                    "starvation": stats.deaths_starvation,
                    "old_age": stats.deaths_old_age,
                    "predation": stats.deaths_predation,
                },
                # Performance metrics for LLM analysis
                "energy_efficiency": (
                    stats.total_food_eaten / stats.total_births if stats.total_births > 0 else 0.0
                ),
                "reproductive_success": (
                    stats.total_reproductions / stats.total_deaths
                    if stats.total_deaths > 0
                    else 0.0
                ),
            }

        # Export poker statistics per algorithm
        for algo_id, poker_stats in self.ecosystem.poker_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            if poker_stats.total_games > 0:
                export_data["poker_statistics"][algo_name] = {
                    "algorithm_id": algo_id,
                    "total_games": poker_stats.total_games,
                    "win_rate": poker_stats.get_win_rate(),
                    "fold_rate": poker_stats.get_fold_rate(),
                    "net_energy": poker_stats.get_net_energy(),
                    "roi": poker_stats.get_roi(),
                    "vpip": poker_stats.get_vpip(),
                    "aggression_factor": poker_stats.get_aggression_factor(),
                    "showdown_win_rate": poker_stats.get_showdown_win_rate(),
                    "bluff_success_rate": poker_stats.get_bluff_success_rate(),
                    "positional_advantage": poker_stats.get_positional_advantage(),
                }

        # Export generation trends
        for gen_num, gen_stats in sorted(self.ecosystem.generation_stats.items()):
            export_data["generation_trends"].append(
                {
                    "generation": gen_num,
                    "population": gen_stats.population,
                    "births": gen_stats.births,
                    "deaths": gen_stats.deaths,
                    "avg_age": gen_stats.avg_age,
                    "avg_speed": gen_stats.avg_speed,
                    "avg_size": gen_stats.avg_size,
                    "avg_energy": gen_stats.avg_energy,
                }
            )

        # Identify top performers (for LLM to learn from)
        algorithms_with_data = [
            (algo_id, stats)
            for algo_id, stats in self.ecosystem.algorithm_stats.items()
            if stats.total_births >= 5  # Minimum sample size
        ]

        # Sort by reproductive success
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate(), reverse=True)

        for algo_id, stats in algorithms_with_data[:5]:  # Top 5
            algo_name = get_algorithm_name(algo_id)
            export_data["recommendations"]["top_performers"].append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "survival_rate": stats.get_survival_rate(),
                    "reason": f"High reproduction rate ({stats.get_reproduction_rate():.2%}) and survival",
                }
            )

        # Identify worst performers (for LLM to learn what to avoid)
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate())
        for algo_id, stats in algorithms_with_data[:5]:  # Bottom 5
            algo_name = get_algorithm_name(algo_id)
            # Determine main death cause using max() for cleaner code
            death_causes = {
                "starvation": stats.deaths_starvation,
                "old_age": stats.deaths_old_age,
                "predation": stats.deaths_predation,
            }
            main_death_cause = (
                max(death_causes, key=death_causes.get) if any(death_causes.values()) else "unknown"
            )

            export_data["recommendations"]["worst_performers"].append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "main_death_cause": main_death_cause,
                    "reason": (
                        f"Low reproduction rate ({stats.get_reproduction_rate():.2%}), "
                        f"main death: {main_death_cause}"
                    ),
                }
            )

        # Identify extinct algorithms
        for algo_id, stats in self.ecosystem.algorithm_stats.items():
            if stats.total_births > 0 and stats.current_population == 0:
                algo_name = get_algorithm_name(algo_id)
                export_data["recommendations"]["extinct_algorithms"].append(
                    {
                        "algorithm_name": algo_name,
                        "algorithm_id": algo_id,
                        "total_births": stats.total_births,
                        "avg_lifespan": stats.get_avg_lifespan(),
                    }
                )

        # Write to file
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Comprehensive stats exported to: {filename}")
        logger.info(f"Export includes {len(export_data['algorithm_performance'])} algorithms")
        logger.info("Use this data for LLM-based behavior analysis and improvement!")

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
            import os

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
