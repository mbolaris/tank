"""Petri dish specific systems.

Includes systems tailored for the circular Petri dish environment.
"""

import math
import random
from typing import Optional

from core.systems.food_spawning import FoodSpawningSystem
from core.worlds.petri.geometry import PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS


class PetriFoodSpawningSystem(FoodSpawningSystem):
    """Spawns food randomly within the Petri dish."""

    def _spawn_food(self) -> int:
        """Spawn a food entity at a random location inside the dish.
        
        Returns:
            Number of food entities spawned (0 or 1)
        """
        from core import entities

        environment = self._engine.environment
        if environment is None:
            return 0

        # Spawn strictly inside the dish
        # Polar coordinates for uniform distribution within circle:
        # r = R * sqrt(random)
        # theta = random * 2 * pi
        
        # Use a slightly smaller radius to avoid spawning exactly on the rim
        spawn_radius = PETRI_RADIUS - 10.0
        
        r = spawn_radius * math.sqrt(self._rng.random())
        theta = self._rng.random() * 2 * math.pi
        
        x = PETRI_CENTER_X + r * math.cos(theta)
        y = PETRI_CENTER_Y + r * math.sin(theta)

        # Determine if live food
        is_live = self._rng.random() < self.config.live_food_chance

        # Get food from pool or create new
        food_pool = self._engine.food_pool
        if is_live:
            # LiveFood requires: environment, x, y
            food = entities.LiveFood(environment, x, y)
        else:
            # FoodPool.acquire requires: environment, x, y
            # Auto-spawned food in Petri dish is stationary/inert usually?
            # Or does it float? In top-down, gravity is Z-axis (not simulated).
            # So movement is Brownian or zero.
            # We'll rely on physics for movement if any.
            food = food_pool.acquire(environment, x, y, allow_stationary_types=False)

        # Add to simulation via mutation queue
        if self._engine.request_spawn(food, reason="auto_food_spawn"):
            self._total_spawned += 1
            return 1

        return 0
