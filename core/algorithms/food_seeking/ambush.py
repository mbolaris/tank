"""AmbushFeeder food-seeking behavior."""


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
class AmbushFeeder(BehaviorAlgorithm):
    """Wait in one spot for food to come close."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="ambush_feeder",
            parameters={
                "strike_distance": rng.uniform(30, 80),
                "strike_speed": rng.uniform(1.0, 1.5),
                "patience": rng.uniform(0.5, 1.0),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            if distance < self.parameters["strike_distance"]:
                # Prediction skill helps aim the strike
                prediction_skill = fish.genome.behavioral.prediction_skill.value
                target_pos = nearest_food.pos

                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
                     is_accelerating = False
                     acceleration = 0.0
                     if hasattr(nearest_food, "food_properties"):
                         from core.config.food import FOOD_SINK_ACCELERATION
                         sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                         acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                         if acceleration > 0 and nearest_food.vel.y >= 0:
                             is_accelerating = True

                     if is_accelerating:
                         target_pos, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                         )
                     else:
                         # Simple lead - now using intercept point properly
                         intercept_point, _ = predict_intercept_point(
                             fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                         )
                         if intercept_point:
                            # Blend based on skill - ambushers need good timing
                            skill_factor = 0.4 + (prediction_skill * 0.6)
                            target_pos = Vector2(
                                nearest_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                                nearest_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                            )

                direction = self._safe_normalize(target_pos - fish.pos)

                # Aggression boosts strike speed
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                strike_speed = self.parameters["strike_speed"] * (1.0 + pursuit_aggression * 0.4)

                return (
                    direction.x * strike_speed,
                    direction.y * strike_speed,
                )
        return 0, 0
