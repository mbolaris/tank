"""Food spawning system.

This system handles automatic food spawning based on population and energy levels.
Extracted from SimulationEngine to follow Single Responsibility Principle.

Before: SimulationEngine.spawn_auto_food() - 80 lines mixed with other concerns
After: FoodSpawningSystem - dedicated, testable, configurable
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core import entities
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
from core.systems.base import BaseSystem

if TYPE_CHECKING:
    from core.environment import Environment
    from core.simulation_engine import SimulationEngine


@dataclass
class SpawnRateConfig:
    """Configuration for food spawn rate adjustments.

    Separating configuration into a dataclass makes the system:
    - Easier to test with different configs
    - Easier to tune parameters
    - Self-documenting about what can be configured
    """

    base_rate: int = AUTO_FOOD_SPAWN_RATE
    ultra_low_energy_threshold: float = AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD
    low_energy_threshold: float = AUTO_FOOD_LOW_ENERGY_THRESHOLD
    high_energy_threshold_1: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
    high_energy_threshold_2: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
    high_pop_threshold_1: int = AUTO_FOOD_HIGH_POP_THRESHOLD_1
    high_pop_threshold_2: int = AUTO_FOOD_HIGH_POP_THRESHOLD_2
    live_food_chance: float = LIVE_FOOD_SPAWN_CHANCE


class FoodSpawningSystem(BaseSystem):
    """Handles automatic food spawning based on ecosystem needs.

    This system monitors population and energy levels to dynamically
    adjust food spawning rates. It prevents both starvation (too little food)
    and overpopulation (too much food).

    Spawn rate adjustments:
    - Ultra-low energy: 4x faster spawning (emergency feeding)
    - Low energy: 3x faster spawning
    - High energy/population: Slower spawning
    - Normal: Base spawn rate

    Time of day effects:
    - Dawn/Dusk: More live food (twilight feeding)
    - Night: Slightly more live food
    - Day: Standard live food chance
    """

    def __init__(
        self,
        engine: "SimulationEngine",
        config: Optional[SpawnRateConfig] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize the food spawning system.

        Args:
            engine: The simulation engine
            config: Spawn rate configuration (uses defaults if None)
            rng: Random number generator (uses new Random if None)
        """
        super().__init__(engine, "FoodSpawning")
        self.config = config or SpawnRateConfig()
        self.rng = rng or random.Random()
        self._spawn_timer: int = 0
        self._food_spawned_count: int = 0
        self._live_food_spawned_count: int = 0

    def _do_update(self, frame: int) -> None:
        """Check if food should spawn this frame."""
        if not AUTO_FOOD_ENABLED:
            return

        environment = self.engine.environment
        if environment is None:
            return

        time_of_day = self.engine.time_system.get_time_of_day()
        self._maybe_spawn_food(environment, time_of_day)

    def _maybe_spawn_food(
        self,
        environment: "Environment",
        time_of_day: float,
    ) -> None:
        """Spawn food if the timer has elapsed.

        Args:
            environment: The simulation environment
            time_of_day: Current time of day (0.0-1.0)
        """
        # Calculate dynamic spawn rate based on ecosystem state
        spawn_rate = self._calculate_spawn_rate()

        self._spawn_timer += 1
        if self._spawn_timer < spawn_rate:
            return

        self._spawn_timer = 0

        # Decide food type and spawn
        if self._should_spawn_live_food(time_of_day):
            self._spawn_live_food(environment)
        else:
            self._spawn_regular_food(environment)

    def _calculate_spawn_rate(self) -> int:
        """Calculate spawn rate based on population and energy.

        Returns:
            Number of frames between food spawns
        """
        fish_list = self.engine.get_fish_list()
        fish_count = len(fish_list)
        total_energy = sum(fish.energy for fish in fish_list)

        config = self.config

        # Priority 1: Emergency feeding when energy is critically low
        if total_energy < config.ultra_low_energy_threshold:
            return config.base_rate // 4

        if total_energy < config.low_energy_threshold:
            return config.base_rate // 3

        # Priority 2: Reduce feeding when energy or population is high
        if (
            total_energy > config.high_energy_threshold_2
            or fish_count > config.high_pop_threshold_2
        ):
            return config.base_rate * 3

        if (
            total_energy > config.high_energy_threshold_1
            or fish_count > config.high_pop_threshold_1
        ):
            return int(config.base_rate * 1.67)

        return config.base_rate

    def _should_spawn_live_food(self, time_of_day: float) -> bool:
        """Determine if live food should spawn based on time of day.

        Args:
            time_of_day: Current time (0.0-1.0 where 0.5 is noon)

        Returns:
            True if live food should spawn
        """
        live_food_chance = self.config.live_food_chance

        # Time-of-day effects
        is_dawn = 0.15 <= time_of_day < 0.35
        is_day = 0.35 <= time_of_day < 0.65
        is_dusk = 0.65 <= time_of_day < 0.85
        is_night = not (is_dawn or is_day or is_dusk)

        if is_dawn or is_dusk:
            # Twilight: peak live food activity
            live_food_chance = min(0.95, live_food_chance * 2.2)
        elif is_night:
            # Night: moderately more live food
            live_food_chance = min(0.85, live_food_chance * 1.6)
        elif is_day:
            # Day: slightly less live food
            live_food_chance = max(0.25, live_food_chance * 0.9)

        return self.rng.random() < live_food_chance

    def _spawn_live_food(self, environment: "Environment") -> None:
        """Spawn a live food entity."""
        bounds = environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        x = self.rng.randint(int(min_x), int(max_x))
        y = self.rng.randint(int(min_y), int(max_y))

        food = entities.LiveFood(
            environment,
            x,
            y,
        )
        self.engine.add_entity(food)
        self._live_food_spawned_count += 1
        self._food_spawned_count += 1

    def _spawn_regular_food(self, environment: "Environment") -> None:
        """Spawn regular food using object pool."""
        bounds = environment.get_bounds()
        (min_x, _), (max_x, _) = bounds

        x = self.rng.randint(int(min_x), int(max_x))

        food = self.engine.food_pool.acquire(
            environment=environment,
            x=x,
            y=0,  # Spawn at top
            source_plant=None,
            allow_stationary_types=False,
        )
        self.engine.add_entity(food)
        self._food_spawned_count += 1

    def get_debug_info(self) -> dict:
        """Return debug information about food spawning."""
        return {
            **super().get_debug_info(),
            "spawn_timer": self._spawn_timer,
            "total_spawned": self._food_spawned_count,
            "live_food_spawned": self._live_food_spawned_count,
            "regular_food_spawned": self._food_spawned_count - self._live_food_spawned_count,
        }

    @property
    def food_spawned_count(self) -> int:
        """Total number of food entities spawned."""
        return self._food_spawned_count

    @property
    def live_food_spawned_count(self) -> int:
        """Number of live food entities spawned."""
        return self._live_food_spawned_count
