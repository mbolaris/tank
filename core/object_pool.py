"""Object pooling for frequently created/destroyed entities.

This module provides object pooling to reduce memory allocation overhead
and garbage collection pressure for entities like Food.
"""

import random
from typing import List, Optional

from core.entities import Food


class FoodPool:
    """Object pool for Food entities to reduce allocation overhead.

    Food entities are frequently created and destroyed in the simulation,
    which can cause memory allocation overhead and GC pressure. This pool
    reuses Food objects instead of creating new ones.
    """

    def __init__(self, initial_size: int = 50, rng: Optional[random.Random] = None):
        """Initialize the food pool.

        Args:
            initial_size: Number of Food objects to pre-allocate
            rng: Random number generator for deterministic food type selection
        """
        self._pool: List[Food] = []
        self._active: set = set()
        self._rng = rng if rng is not None else random

    def acquire(
        self,
        environment,
        x: float,
        y: float,
        source_plant=None,
        allow_stationary_types: bool = True,
    ) -> Food:
        """Get a Food object from the pool or create a new one.

        Args:
            environment: The environment for the food
            x: X position
            y: Y position
            source_plant: Optional plant that created this food
            allow_stationary_types: Whether to allow stationary food types

        Returns:
            A Food object ready to use
        """
        # Try to reuse from pool
        if self._pool:
            food = self._pool.pop()
            # Reset food state
            food.pos.x = x
            food.pos.y = y
            food.vel.x = 0
            food.vel.y = 0
            food.source_plant = source_plant
            # Re-randomize food type using seeded RNG
            food_type = Food._select_random_food_type(
                include_stationary=allow_stationary_types,
                rng=self._rng,
            )
            food.food_type = food_type
            food.food_properties = Food.FOOD_TYPES[food_type]
            food.is_stationary = food.food_properties.get("stationary", False)
        else:
            # Create new if pool is empty
            food = Food(
                environment=environment,
                x=x,
                y=y,
                source_plant=source_plant,
                allow_stationary_types=allow_stationary_types,
            )

        self._active.add(food)
        return food

    def release(self, food: Food) -> None:
        """Return a Food object to the pool for reuse.

        Args:
            food: The Food object to return to the pool
        """
        if food in self._active:
            self._active.remove(food)
            self._pool.append(food)

    def clear(self) -> None:
        """Clear the pool and active set."""
        self._pool.clear()
        self._active.clear()

    def get_stats(self) -> dict:
        """Get pool statistics for monitoring.

        Returns:
            Dictionary with pool size and active count
        """
        return {
            "pool_size": len(self._pool),
            "active_count": len(self._active),
            "total_capacity": len(self._pool) + len(self._active),
        }
