"""ZigZagForager food-seeking behavior."""


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
class ZigZagForager(BehaviorAlgorithm):
    """Move in zigzag pattern to maximize food discovery."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="zigzag_forager",
            parameters={
                "zigzag_frequency": (rng or random).uniform(0.02, 0.08),
                "zigzag_amplitude": (rng or random).uniform(0.5, 1.2),
                "forward_speed": (rng or random).uniform(0.6, 1.0),
            },
            rng=rng,
        )
        self.zigzag_phase = (rng or random).uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check for nearby food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food and (nearest_food.pos - fish.pos).length() < FOOD_PURSUIT_RANGE_CLOSE:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)

            # Aggression boosts chase speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed_boost = 1.0 + pursuit_aggression * 0.3

            return direction.x * speed_boost, direction.y * speed_boost

        # Zigzag movement
        self.zigzag_phase += self.parameters["zigzag_frequency"]
        vx = self.parameters["forward_speed"]
        vy = math.sin(self.zigzag_phase) * self.parameters["zigzag_amplitude"]

        return vx, vy
