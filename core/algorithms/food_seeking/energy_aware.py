"""EnergyAwareFoodSeeker food-seeking behavior."""


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
class EnergyAwareFoodSeeker(BehaviorAlgorithm):
    """Seek food more aggressively when energy is low."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="energy_aware_food_seeker",
            parameters={
                "urgency_threshold": rng.uniform(0.3, 0.7),
                "calm_speed": rng.uniform(0.3, 0.6),
                "urgent_speed": rng.uniform(0.8, 1.2),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        energy_ratio = fish.get_energy_ratio()

        # Get hunting traits
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        hunting_stamina = fish.genome.behavioral.hunting_stamina.value

        # Check for predators - even urgent fish should avoid immediate danger
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (
            (nearest_predator.pos - fish.pos).length()
            if nearest_predator
            else PREDATOR_DEFAULT_FAR_DISTANCE
        )
        predator_nearby = predator_distance < PREDATOR_PROXIMITY_THRESHOLD

        # IMPROVEMENT: Critical energy mode - must find food NOW
        if is_critical:
            # Desperate - must eat even with some predator risk
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                # If predator is blocking food, try to path around it
                if predator_nearby:
                    predator_to_food = (nearest_food.pos - nearest_predator.pos).length()
                    if predator_to_food < PREDATOR_GUARDING_FOOD_DISTANCE:
                        # Try perpendicular approach
                        to_food = (nearest_food.pos - fish.pos).normalize()
                        perp_x, perp_y = -to_food.y, to_food.x
                        return perp_x * 0.8, perp_y * 0.8
                direction = self._safe_normalize(nearest_food.pos - fish.pos)

                # Hunting traits boost speed
                trait_boost = pursuit_aggression * 0.4 + hunting_stamina * 0.2
                speed = self.parameters["urgent_speed"] * (1.0 + trait_boost)

                return (
                    direction.x * speed,
                    direction.y * speed,
                )

        # Flee if predator too close
        if predator_nearby:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Graduated urgency based on energy level
            if energy_ratio < self.parameters["urgency_threshold"]:
                speed = self.parameters["urgent_speed"]
            else:
                # Scale speed based on energy - conserve when high energy
                speed = self.parameters["calm_speed"] + (1.0 - energy_ratio) * 0.3

            # Apply hunting stamina bonus - maintain higher speed longer
            if hunting_stamina > 0.6:
                speed *= (1.0 + (hunting_stamina - 0.6) * 0.5)

            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * speed, direction.y * speed
        return 0, 0
