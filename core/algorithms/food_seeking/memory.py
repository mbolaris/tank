"""FoodMemorySeeker food-seeking behavior."""


import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.food import (
    CHASE_DISTANCE_CRITICAL,
    CHASE_DISTANCE_LOW,
    CHASE_DISTANCE_SAFE_BASE,
    DANGER_WEIGHT_CRITICAL,
    DANGER_WEIGHT_LOW,
    DANGER_WEIGHT_NORMAL,
    FOOD_CIRCLING_APPROACH_DISTANCE,
    FOOD_MEMORY_RECORD_DISTANCE,
    FOOD_PURSUIT_RANGE_CLOSE,
    FOOD_PURSUIT_RANGE_DESPERATE,
    FOOD_PURSUIT_RANGE_EXTENDED,
    FOOD_PURSUIT_RANGE_NORMAL,
    FOOD_SAFETY_BONUS,
    FOOD_SAFETY_DISTANCE_RATIO,
    FOOD_SCORE_THRESHOLD_CRITICAL,
    FOOD_SCORE_THRESHOLD_LOW,
    FOOD_SCORE_THRESHOLD_NORMAL,
    FOOD_SPEED_BOOST_DISTANCE,
    FOOD_STRIKE_DISTANCE,
    FOOD_VELOCITY_THRESHOLD,
    PREDATOR_DANGER_ZONE_DIVISOR,
    PREDATOR_DANGER_ZONE_RADIUS,
    PREDATOR_DEFAULT_FAR_DISTANCE,
    PREDATOR_FLEE_DISTANCE_CAUTIOUS,
    PREDATOR_FLEE_DISTANCE_CONSERVATIVE,
    PREDATOR_FLEE_DISTANCE_DESPERATE,
    PREDATOR_FLEE_DISTANCE_NORMAL,
    PREDATOR_FLEE_DISTANCE_SAFE,
    PREDATOR_GUARDING_FOOD_DISTANCE,
    PREDATOR_PROXIMITY_THRESHOLD,
    PROXIMITY_BOOST_DIVISOR,
    PROXIMITY_BOOST_MULTIPLIER,
    SOCIAL_FOLLOW_MAX_DISTANCE,
    SOCIAL_FOOD_PROXIMITY_THRESHOLD,
    SOCIAL_SIGNAL_DETECTION_RANGE,
    URGENCY_BOOST_CRITICAL,
    URGENCY_BOOST_LOW,
)
from core.config.display import SCREEN_HEIGHT
from core.entities import Crab, Food
from core.predictive_movement import predict_intercept_point, predict_falling_intercept
from core.world import World

@dataclass
class FoodMemorySeeker(BehaviorAlgorithm):
    """Remember where food was found before."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="food_memory_seeker",
            parameters={
                "memory_strength": (rng or random).uniform(0.5, 1.0),
                "exploration_rate": (rng or random).uniform(0.2, 0.5),
            },
            rng=rng,
        )
        self.food_memory_locations: List[Vector2] = []

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

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
            rng = self.rng or getattr(fish.environment, "rng", random)
            if rng.random() > self.parameters["exploration_rate"]:
                target = rng.choice(self.food_memory_locations)
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
