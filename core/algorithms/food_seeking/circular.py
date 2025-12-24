"""CircularHunter food-seeking behavior."""


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
class CircularHunter(BehaviorAlgorithm):
    """Circle around food before striking - IMPROVED for better survival."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="circular_hunter",
            parameters={
                "circle_radius": (rng or random).uniform(50, 80),
                "approach_speed": (rng or random).uniform(0.9, 1.2),
                "strike_distance": (rng or random).uniform(60, 100),
                "exploration_speed": (rng or random).uniform(0.6, 0.9),
            },
            rng=rng,
        )
        self.circle_angle = 0
        self.exploration_direction = (rng or random).uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check energy status for smarter decisions
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3
        is_low_energy = energy_ratio < 0.5

        # Predator check - flee distance based on energy
        nearest_predator = self._find_nearest(fish, Crab)
        flee_distance = PREDATOR_FLEE_DISTANCE_DESPERATE if is_desperate else PREDATOR_FLEE_DISTANCE_NORMAL
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < flee_distance:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            # Conserve energy when desperate
            flee_speed = 1.2 if is_desperate else 1.4
            return direction.x * flee_speed, direction.y * flee_speed

        nearest_food = self._find_nearest_food(fish)
        if not nearest_food:
            # CRITICAL FIX: Actively explore instead of stopping!
            # Slowly change direction for more exploration coverage
            rng = self.rng or getattr(fish.environment, "rng", random)
            self.exploration_direction += rng.uniform(-0.3, 0.3)
            exploration_vec = Vector2(
                math.cos(self.exploration_direction), math.sin(self.exploration_direction)
            )
            speed = self.parameters["exploration_speed"]
            return exploration_vec.x * speed, exploration_vec.y * speed

        distance = (nearest_food.pos - fish.pos).length()

        # If food is moving (has velocity), predict its position
        food_future_pos = nearest_food.pos
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
                 food_future_pos, _ = predict_falling_intercept(
                    fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                 )
             else:
                 intercept_point, _ = predict_intercept_point(
                     fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                 )
                 if intercept_point:
                     food_future_pos = intercept_point
                 else:
                     food_future_pos = nearest_food.pos + nearest_food.vel * 10

        # IMPROVEMENT: Skip circling when desperate or very hungry
        # Go straight for food when energy is low!
        if is_desperate or is_low_energy:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            speed = 1.3  # Fast, direct approach when hungry

            # Hunting traits
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= (1.0 + pursuit_aggression * 0.3)

            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Larger strike distance to actually catch food
        if distance < self.parameters["strike_distance"]:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            # Fast strike
            strike_speed = 1.5

            # Aggression boosts strike speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            strike_speed *= (1.0 + pursuit_aggression * 0.4)

            return direction.x * strike_speed, direction.y * strike_speed

        # Only circle when well-fed (this is the "hunting" behavior)
        # IMPROVEMENT: Much faster circling to not waste time
        if distance < FOOD_CIRCLING_APPROACH_DISTANCE:
            self.circle_angle += 0.25  # Much faster than old 0.05-0.15!

            target_x = (
                nearest_food.pos.x + math.cos(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_y = (
                nearest_food.pos.y + math.sin(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_vector = Vector2(target_x, target_y) - fish.pos
            direction = self._safe_normalize(target_vector)
            # Faster circling movement
            speed = self.parameters["approach_speed"]
            return direction.x * speed, direction.y * speed
        else:
            # Food is far - approach directly
            direction = self._safe_normalize(food_future_pos - fish.pos)
            return (
                direction.x * self.parameters["approach_speed"],
                direction.y * self.parameters["approach_speed"],
            )
