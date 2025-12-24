"""SurfaceSkimmer food-seeking behavior."""


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
class SurfaceSkimmer(BehaviorAlgorithm):
    """Stay near surface to catch falling food - IMPROVED for better survival."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="surface_skimmer",
            parameters={
                "preferred_depth": (rng or random).uniform(0.1, 0.25),  # 10-25% from top
                "horizontal_speed": (rng or random).uniform(0.8, 1.3),  # INCREASED from 0.5-1.0
                "dive_for_food_threshold": (rng or random).uniform(150, 250),  # NEW: will dive for food
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy and threats
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_CONSERVATIVE:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]

        # Look for food - IMPROVED to actively pursue
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            food_dist = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Dive for food if desperate or food is reasonably close
            if is_desperate or food_dist < self.parameters["dive_for_food_threshold"]:
                # Go directly for food, abandoning surface position

                # Use prediction for diving
                prediction_skill = fish.genome.behavioral.prediction_skill.value
                target_pos = nearest_food.pos
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0:
                     # Using acceleration-aware prediction for better diving
                     is_accelerating = False
                     acceleration = 0.0
                     if hasattr(nearest_food, "food_properties"):
                         from core.config.food import FOOD_SINK_ACCELERATION
                         sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                         acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                         if acceleration > 0 and nearest_food.vel.y >= 0:
                             is_accelerating = True
                     
                     if is_accelerating:
                         intercept_point, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                         )
                         # High commitment to intercept for skimmers diving
                         target_pos = intercept_point
                     else:
                         target_pos = nearest_food.pos + nearest_food.vel * (prediction_skill * 10)

                direction = self._safe_normalize(target_pos - fish.pos)
                speed = 1.2 if is_desperate else 1.0

                # Aggression boosts dive speed
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                speed *= (1.0 + pursuit_aggression * 0.3)

                return direction.x * speed, direction.y * speed
            else:
                # Move horizontally toward food while maintaining depth
                vx = (nearest_food.pos.x - fish.pos.x) / 80  # FASTER horizontal tracking
                vy = (target_y - fish.pos.y) / 100
                # IMPROVEMENT: Speed up horizontal movement
                vx *= 1.5
                return vx, vy
        else:
            # No food visible - patrol surface actively
            vy = (target_y - fish.pos.y) / 100
            # IMPROVEMENT: Active patrol instead of random flip
            vx = self.parameters["horizontal_speed"]
            # Change direction periodically
            rng = self.rng or getattr(fish.environment, "rng", random)
            if rng.random() < 0.02:  # 2% chance per frame to reverse
                self.parameters["horizontal_speed"] *= -1
            return vx, vy
