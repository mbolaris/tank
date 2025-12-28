"""SpiralForager food-seeking behavior."""


import random
from dataclasses import dataclass
from typing import Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm
from core.config.food import (
    FOOD_PURSUIT_RANGE_EXTENDED,
    PREDATOR_FLEE_DISTANCE_SAFE,
)
from core.entities import Crab

@dataclass
class SpiralForager(BehaviorAlgorithm):
    """NEW: Spiral outward from center to systematically cover area - replaces weak algorithms."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="spiral_forager",
            parameters={
                "spiral_speed": (rng or random.Random()).uniform(0.8, 1.2),
                "spiral_growth": (rng or random.Random()).uniform(0.3, 0.7),
                "food_pursuit_speed": (rng or random.Random()).uniform(1.1, 1.5),
            },
            rng=rng,
        )
        self.spiral_angle = 0
        self.spiral_radius = 10

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_SAFE:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Always check for food first
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # Abandon spiral to pursue food
            if distance < FOOD_PURSUIT_RANGE_EXTENDED or is_desperate:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
                return direction.x * speed, direction.y * speed

        # Spiral search pattern
        self.spiral_angle += 0.25  # Fast spiral
        self.spiral_radius += self.parameters["spiral_growth"]

        # Reset spiral if too large
        if self.spiral_radius > 150:
            self.spiral_radius = 10

        # Calculate spiral movement
        import math

        vx = math.cos(self.spiral_angle) * self.parameters["spiral_speed"]
        vy = math.sin(self.spiral_angle) * self.parameters["spiral_speed"]

        return vx, vy
