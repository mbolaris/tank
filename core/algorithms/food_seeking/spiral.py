"""SpiralForager food-seeking behavior."""


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
class SpiralForager(BehaviorAlgorithm):
    """NEW: Spiral outward from center to systematically cover area - replaces weak algorithms."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="spiral_forager",
            parameters={
                "spiral_speed": (rng or random).uniform(0.8, 1.2),
                "spiral_growth": (rng or random).uniform(0.3, 0.7),
                "food_pursuit_speed": (rng or random).uniform(1.1, 1.5),
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
