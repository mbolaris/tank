"""Food spawning system for automatic food generation.

This module handles automatic food spawning based on ecosystem health.
Spawn rates adapt dynamically to maintain ecosystem balance.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.SPAWN
- Uses deterministic RNG for reproducible simulations
- Respects AUTO_FOOD_ENABLED configuration
"""

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH
from core.config.food import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    LIVE_FOOD_SPAWN_CHANCE,
)
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.config.simulation_config import DisplayConfig
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class SpawnRateConfig:
    """Configuration for dynamic food spawn rates.

    Attributes:
        base_rate: Base frames between spawns (lower = faster)
        ultra_low_energy_threshold: Total energy below this triggers 4x spawning
        low_energy_threshold: Total energy below this triggers 3x spawning
        high_energy_threshold_1: Energy above this reduces spawning
        high_energy_threshold_2: Energy above this further reduces spawning
        high_pop_threshold_1: Population above this reduces spawning
        high_pop_threshold_2: Population above this further reduces spawning
        live_food_chance: Probability of spawning live (moving) food
    """

    base_rate: int = AUTO_FOOD_SPAWN_RATE
    ultra_low_energy_threshold: float = AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD
    low_energy_threshold: float = AUTO_FOOD_LOW_ENERGY_THRESHOLD
    high_energy_threshold_1: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
    high_energy_threshold_2: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
    high_pop_threshold_1: int = AUTO_FOOD_HIGH_POP_THRESHOLD_1
    high_pop_threshold_2: int = AUTO_FOOD_HIGH_POP_THRESHOLD_2
    live_food_chance: float = LIVE_FOOD_SPAWN_CHANCE


@runs_in_phase(UpdatePhase.SPAWN)
class FoodSpawningSystem(BaseSystem):
    """Manages automatic food spawning to maintain ecosystem balance.

    This system spawns food at a rate that adapts to ecosystem health:
    - Low total energy → increased spawn rate (prevent starvation)
    - High population → decreased spawn rate (prevent overpopulation)
    - Critical conditions → emergency spawning

    The spawn rate creates selection pressure: faster spawning makes
    survival easier but weakens natural selection.

    Attributes:
        config: SpawnRateConfig with rate parameters
        _rng: Random number generator for deterministic behavior
        _total_spawned: Count of food spawned since system creation
        _frames_since_spawn: Frames elapsed since last spawn
    """

    def __init__(
        self,
        engine: "SimulationEngine",
        rng: random.Random | None = None,
        spawn_rate_config: SpawnRateConfig | None = None,
        auto_food_enabled: bool = AUTO_FOOD_ENABLED,
        display_config: Optional["DisplayConfig"] = None,
    ) -> None:
        """Initialize the food spawning system.

        Args:
            engine: The simulation engine
            rng: Random number generator (uses engine's rng if not provided)
            spawn_rate_config: Spawn rate configuration (uses defaults if not provided)
            auto_food_enabled: Master toggle for auto food spawning
            display_config: Display config for spawn bounds
        """
        super().__init__(engine, "FoodSpawning")
        from core.util.rng import require_rng_param

        self._rng = require_rng_param(rng, "__init__")
        self.config = spawn_rate_config if spawn_rate_config is not None else SpawnRateConfig()
        self._auto_food_enabled = auto_food_enabled
        self._screen_width = display_config.screen_width if display_config else SCREEN_WIDTH
        self._screen_height = display_config.screen_height if display_config else SCREEN_HEIGHT
        self._total_spawned: int = 0
        self._frames_since_spawn: int = 0
        self._last_spawn_rate: int = self.config.base_rate

    def _do_update(self, frame: int) -> SystemResult:
        """Spawn food based on ecosystem health.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult with spawn statistics
        """
        if not self._auto_food_enabled:
            return SystemResult.skipped_result()

        if self._engine.environment is None:
            return SystemResult.empty()

        self._frames_since_spawn += 1

        # Calculate dynamic spawn rate based on ecosystem state
        spawn_rate = self._calculate_spawn_rate()
        self._last_spawn_rate = spawn_rate

        # Check if it's time to spawn
        if self._frames_since_spawn < spawn_rate:
            return SystemResult.empty()

        # Reset counter and spawn food
        self._frames_since_spawn = 0
        spawned_count = self._spawn_food()

        return SystemResult(
            entities_spawned=spawned_count,
            details={
                "spawn_rate": spawn_rate,
                "live_food": spawned_count > 0
                and self._rng.random() < self.config.live_food_chance,
            },
        )

    def _calculate_spawn_rate(self) -> int:
        """Calculate the current spawn rate based on ecosystem state.

        Lower return values mean faster spawning.

        Returns:
            Frames between spawns (adjusted for ecosystem health)
        """
        base_rate = self.config.base_rate

        # Get ecosystem state
        ecosystem = self._engine.ecosystem
        if ecosystem is None:
            return base_rate

        fish_list = self._engine.get_fish_list()
        fish_count = len(fish_list)

        # Calculate total fish energy
        total_energy = sum(f.energy for f in fish_list)

        # Energy-based modifiers (struggling populations get more food)
        if total_energy < self.config.ultra_low_energy_threshold:
            # Crisis: 4x spawn rate
            rate_modifier = 0.25
        elif total_energy < self.config.low_energy_threshold:
            # Struggling: 3x spawn rate
            rate_modifier = 0.33
        elif total_energy > self.config.high_energy_threshold_2:
            # Thriving: reduce spawn rate
            rate_modifier = 2.0
        elif total_energy > self.config.high_energy_threshold_1:
            # Comfortable: slightly reduce spawn rate
            rate_modifier = 1.5
        else:
            rate_modifier = 1.0

        # Population-based modifiers (high population = less food)
        if fish_count > self.config.high_pop_threshold_2:
            rate_modifier *= 1.5
        elif fish_count > self.config.high_pop_threshold_1:
            rate_modifier *= 1.25

        return max(1, int(base_rate * rate_modifier))

    def _spawn_food(self) -> int:
        """Spawn a food entity at a random location.

        Returns:
            Number of food entities spawned (0 or 1)
        """
        from core import entities

        environment = self._engine.environment
        if environment is None:
            return 0

        # Random spawn position at top of screen
        margin = 50
        x = self._rng.randint(margin, self._screen_width - margin)
        y = self._rng.randint(10, min(50, self._screen_height))  # Near top of tank

        # Determine if live food
        is_live = self._rng.random() < self.config.live_food_chance

        # Get food from pool or create new
        food_pool = self._engine.food_pool
        if is_live:
            # LiveFood requires: environment, x, y
            food = entities.LiveFood(environment, x, y)
        else:
            # FoodPool.acquire requires: environment, x, y
            # Auto-spawned food should fall; exclude stationary types like nectar.
            food = food_pool.acquire(environment, x, y, allow_stationary_types=False)

        # Add to simulation via mutation queue
        if self._engine.request_spawn(food, reason="auto_food_spawn"):
            self._total_spawned += 1
            return 1

        return 0

    def get_debug_info(self) -> dict[str, Any]:
        """Return food spawning statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "total_spawned": self._total_spawned,
            "frames_since_spawn": self._frames_since_spawn,
            "current_spawn_rate": self._last_spawn_rate,
            "config": {
                "base_rate": self.config.base_rate,
                "live_food_chance": self.config.live_food_chance,
                "auto_food_enabled": self._auto_food_enabled,
            },
        }
