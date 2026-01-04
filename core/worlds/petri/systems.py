"""Petri dish specific systems.

Includes systems tailored for the circular Petri dish environment.
"""

from __future__ import annotations

from core.systems.food_spawning import FoodSpawningSystem


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

        # Get dish from environment and sample a point inside
        dish = getattr(environment, "dish", None)
        if dish is None:
            # Fallback if dish not available (shouldn't happen in Petri mode)
            return 0
        
        # Spawn strictly inside the dish with a small margin
        x, y = dish.sample_point(self._rng, margin=10.0)

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

