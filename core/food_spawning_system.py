"""Food spawning system.

This module handles automatic food spawning with dynamic rate adjustment
based on population size and total energy in the ecosystem.
"""

import random
from typing import TYPE_CHECKING, List, Optional

from core.constants import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    LIVE_FOOD_SPAWN_CHANCE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)

if TYPE_CHECKING:
    from core import entities
    from core.ecosystem import EcosystemManager
    from core.environment import Environment
    from core.object_pool import FoodPool
    from core.time_system import TimeSystem


class AutoFoodSpawner:
    """Handles automatic food spawning with dynamic rate adjustment.

    The spawner adjusts spawn rates based on:
    - Total fish energy (faster spawning when starving)
    - Population size (slower spawning when crowded)
    - Time of day (more live food at dawn/dusk)

    Attributes:
        timer: Frames since last spawn
        rng: Random number generator for deterministic spawning
    """

    def __init__(
        self,
        rng: Optional[random.Random] = None,
        food_pool: Optional["FoodPool"] = None,
    ) -> None:
        """Initialize the food spawner.

        Args:
            rng: Random number generator (uses global random if None)
            food_pool: Object pool for efficient food creation
        """
        self.timer: int = 0
        self.rng = rng or random.Random()
        self.food_pool = food_pool

    def calculate_spawn_rate(self, total_energy: float, fish_count: int) -> int:
        """Calculate the current spawn rate based on ecosystem state.

        Args:
            total_energy: Total energy across all fish
            fish_count: Number of fish in the simulation

        Returns:
            Spawn rate in frames (lower = more frequent spawning)
        """
        spawn_rate = AUTO_FOOD_SPAWN_RATE

        # Priority 1: Emergency feeding when energy is critically low
        if total_energy < AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD:
            # Critical starvation: Quadruple spawn rate
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 4
        elif total_energy < AUTO_FOOD_LOW_ENERGY_THRESHOLD:
            # Low energy: Triple spawn rate
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 3

        # Priority 2: Reduce feeding when energy or population is high
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_2
        ):
            # Very high energy/population: Slow down significantly
            spawn_rate = AUTO_FOOD_SPAWN_RATE * 3
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_1
        ):
            # High energy/population: Slow down moderately
            spawn_rate = int(AUTO_FOOD_SPAWN_RATE * 1.67)

        return max(1, spawn_rate)  # Never less than 1 frame

    def calculate_live_food_chance(
        self, time_of_day: float, is_night: bool
    ) -> float:
        """Calculate the chance of spawning live food based on time of day.

        Live food (moving organisms) is more common at twilight hours
        and slightly boosted at night.

        Args:
            time_of_day: Time of day (0.0-1.0, 0=midnight, 0.5=noon)
            is_night: Whether it's currently night

        Returns:
            Probability of spawning live food (0.0-1.0)
        """
        live_food_chance = LIVE_FOOD_SPAWN_CHANCE

        is_dawn = 0.15 <= time_of_day < 0.35
        is_day = 0.35 <= time_of_day < 0.65
        is_dusk = 0.65 <= time_of_day < 0.85

        if is_dawn or is_dusk:
            # Twilight peaks: double live food chance
            live_food_chance = min(0.95, LIVE_FOOD_SPAWN_CHANCE * 2.2)
        elif is_night:
            # Night: slightly boost live food
            live_food_chance = min(0.85, LIVE_FOOD_SPAWN_CHANCE * 1.6)
        elif is_day:
            # Day: slightly reduce live food
            live_food_chance = max(0.25, LIVE_FOOD_SPAWN_CHANCE * 0.9)

        return live_food_chance

    def spawn(
        self,
        environment: "Environment",
        fish_list: List["entities.Fish"],
        time_system: Optional["TimeSystem"] = None,
        ecosystem: Optional["EcosystemManager"] = None,
    ) -> Optional["entities.Agent"]:
        """Attempt to spawn food if conditions are met.

        Args:
            environment: Environment for creating entities
            fish_list: Current list of fish for energy calculation
            time_system: Time system for day/night effects
            ecosystem: Ecosystem for tracking energy inflows

        Returns:
            New food entity if spawned, None otherwise
        """
        if not AUTO_FOOD_ENABLED:
            return None

        from core import entities

        # Calculate total energy and population
        fish_count = len(fish_list)
        total_energy = sum(fish.energy for fish in fish_list)

        # Get dynamic spawn rate
        spawn_rate = self.calculate_spawn_rate(total_energy, fish_count)

        self.timer += 1
        if self.timer < spawn_rate:
            return None

        self.timer = 0

        # Get time of day effects
        time_of_day = 0.5  # Default to noon
        is_night = False
        if time_system is not None:
            time_of_day = time_system.get_time_of_day()
            is_night = time_system.is_night()

        # Decide food type
        live_food_chance = self.calculate_live_food_chance(time_of_day, is_night)
        live_food_roll = self.rng.random()

        if live_food_roll < live_food_chance:
            # Spawn live food at random position
            food_x = self.rng.randint(0, SCREEN_WIDTH)
            food_y = self.rng.randint(0, SCREEN_HEIGHT)
            food = entities.LiveFood(
                environment,
                food_x,
                food_y,
            )
            )
        else:
            # Spawn regular food from top
            x = self.rng.randint(0, SCREEN_WIDTH)
            if self.food_pool is not None:
                # Use object pool for efficiency
                food = self.food_pool.acquire(
                    environment=environment,
                    x=x,
                    y=0,
                    source_plant=None,
                    allow_stationary_types=False,
                )
            else:
                # Create new food directly
                food = entities.Food(
                    environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False,
                )

        return food

    def update(
        self,
        environment: "Environment",
        fish_list: List["entities.Fish"],
        time_system: Optional["TimeSystem"] = None,
        ecosystem: Optional["EcosystemManager"] = None,
    ) -> List["entities.Agent"]:
        """Update the spawner and return any new food entities.

        This is a convenience method that calls spawn() and returns
        the result as a list for easy integration with simulation loops.

        Args:
            environment: Environment for creating entities
            fish_list: Current list of fish
            time_system: Time system for day/night effects
            ecosystem: Ecosystem for tracking energy

        Returns:
            List containing the new food entity, or empty list
        """
        food = self.spawn(environment, fish_list, time_system, ecosystem)
        return [food] if food is not None else []


class EmergencyFishSpawner:
    """Handles emergency fish spawning when population drops critically low.

    This spawner helps maintain genetic diversity and prevents extinction
    by spawning new fish with diverse genomes when population is low.
    """

    def __init__(
        self,
        cooldown_frames: int = 30,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize the emergency spawner.

        Args:
            cooldown_frames: Minimum frames between spawns
            rng: Random number generator
        """
        self.cooldown_frames = cooldown_frames
        self.last_spawn_frame = -cooldown_frames  # Allow immediate first spawn
        self.rng = rng or random.Random()

    def should_spawn(
        self,
        fish_count: int,
        max_population: int,
        critical_threshold: int,
        current_frame: int,
    ) -> bool:
        """Check if emergency spawning should occur.

        Args:
            fish_count: Current fish population
            max_population: Maximum allowed population
            critical_threshold: Population below which spawning is guaranteed
            current_frame: Current simulation frame

        Returns:
            True if a fish should be spawned
        """
        if fish_count >= max_population:
            return False

        frames_since_spawn = current_frame - self.last_spawn_frame
        if frames_since_spawn < self.cooldown_frames:
            return False

        # Calculate spawn probability based on population
        if fish_count < critical_threshold:
            # Emergency mode: always spawn
            spawn_probability = 1.0
        else:
            # Gradual decrease with inverse square curve
            population_ratio = (fish_count - critical_threshold) / (
                max_population - critical_threshold
            )
            spawn_probability = (1.0 - population_ratio) ** 2 * 0.3

        return self.rng.random() < spawn_probability

    def spawn(
        self,
        environment: "Environment",
        ecosystem: "EcosystemManager",
        fish_list: List["entities.Fish"],
        current_frame: int,
    ) -> Optional["entities.Fish"]:
        """Spawn an emergency fish with diverse genome.

        Args:
            environment: Environment for creating entities
            ecosystem: Ecosystem manager
            fish_list: Current fish list for diversity analysis
            current_frame: Current simulation frame

        Returns:
            New fish if spawned, None otherwise
        """
        from core import entities, movement_strategy
        from core.algorithms import get_algorithm_index
        from core.constants import (
            FILES,
            MAX_DIVERSITY_SPAWN_ATTEMPTS,
            SPAWN_MARGIN_PIXELS,
        )
        from core.genetics import Genome

        # Track spawn time
        self.last_spawn_frame = current_frame

        # With composable behaviors (1,152+ combinations), random spawns are naturally diverse
        genome: Genome = Genome.random(use_algorithm=True, rng=self.rng)

        # Random spawn position (avoid edges)
        x = self.rng.randint(
            SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS
        )
        y = self.rng.randint(
            SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS
        )

        # Create the fish
        new_fish = entities.Fish(
            environment,
            movement_strategy.AlgorithmicMovement(),
            FILES["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
        )
        )
        new_fish.register_birth()

        return new_fish
