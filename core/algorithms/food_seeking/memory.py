"""FoodMemorySeeker food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm, Vector2


@dataclass
class FoodMemorySeeker(BehaviorAlgorithm):
    """Remember where food was found before."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="food_memory_seeker",
            parameters={
                "memory_strength": _rng.uniform(0.5, 1.0),
                "exploration_rate": _rng.uniform(0.2, 0.5),
            },
            rng=_rng,
        )
        self.food_memory_locations: list[Vector2] = []

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        # Look for current food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Remember this location
            if len(self.food_memory_locations) < 5:
                self.food_memory_locations.append(Vector2(nearest_food.pos.x, nearest_food.pos.y))
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x, direction.y

        # No food visible, check memory
        if self.food_memory_locations:
            if self.rng.random() > self.parameters["exploration_rate"]:
                target = self.rng.choice(self.food_memory_locations)
            else:
                # If not randomly exploring, head to the closest remembered location
                target = min(
                    self.food_memory_locations,
                    key=lambda pos: (pos - fish.pos).length(),
                )
            direction = self._safe_normalize(target - fish.pos)
            return (
                direction.x * self.parameters["memory_strength"],
                direction.y * self.parameters["memory_strength"],
            )

        return 0, 0
