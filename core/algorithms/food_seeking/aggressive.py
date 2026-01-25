"""AggressiveHunter food-seeking behavior."""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.food import (
    FOOD_STRIKE_DISTANCE,
    PREDATOR_FLEE_DISTANCE_CAUTIOUS,
    PREDATOR_FLEE_DISTANCE_DESPERATE,
)

if TYPE_CHECKING:
    from core.entities import Fish

from core.predictive_movement import predict_falling_intercept, predict_intercept_point


@dataclass
class AggressiveHunter(BehaviorAlgorithm):
    """Aggressively pursue food with high-speed interception.

    This algorithm is especially effective at catching live/moving food.
    Uses genetic hunting traits to affect behavior:
    - pursuit_aggression: How fast to pursue
    - prediction_skill: How well to predict food trajectory
    - hunting_stamina: How long to maintain high-speed pursuit
    """

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "AggressiveHunter.__init__")
        super().__init__(
            algorithm_id="aggressive_hunter",
            parameters={
                "pursuit_speed": _rng.uniform(1.3, 1.7),
                "detection_range": _rng.uniform(250, 400),
                "strike_speed": _rng.uniform(1.5, 2.0),
            },
            rng=_rng,
        )
        self.last_food_pos: Optional[Vector2] = None

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        from core.entities import Crab

        energy_ratio = fish.energy / fish.max_energy
        is_critical = energy_ratio < 0.3

        # Get hunting traits from genome (with defaults if not present)
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        prediction_skill = fish.genome.behavioral.prediction_skill.value
        hunting_stamina = fish.genome.behavioral.hunting_stamina.value

        # Predator check - but take more risks when desperate or highly aggressive
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            # Higher aggression = less cautious around predators
            flee_threshold = (
                PREDATOR_FLEE_DISTANCE_DESPERATE
                if is_critical
                else PREDATOR_FLEE_DISTANCE_CAUTIOUS * (1.0 - pursuit_aggression * 0.3)
            )
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.4, direction.y * 1.4

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            self.last_food_pos = Vector2(nearest_food.pos.x, nearest_food.pos.y)

            # Detection range boosted by pursuit_aggression
            effective_detection = self.parameters["detection_range"] * (
                1.0 + pursuit_aggression * 0.3
            )

            # High-speed pursuit within detection range
            if distance < effective_detection:
                # Predict food movement - skill affects prediction accuracy
                target_pos = nearest_food.pos  # Default to current food position
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
                        intercept_point, _ = predict_intercept_point(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                        )
                        if intercept_point:
                            # Aggressive hunters commit to prediction based on skill
                            skill_factor = 0.5 + (prediction_skill * 0.5)
                            target_pos = Vector2(
                                nearest_food.pos.x * (1 - skill_factor)
                                + intercept_point.x * skill_factor,
                                nearest_food.pos.y * (1 - skill_factor)
                                + intercept_point.y * skill_factor,
                            )

                direction = self._safe_normalize(target_pos - fish.pos)

                # Speed boosted by hunting traits
                pursuit_boost = 1.0 + pursuit_aggression * 0.4  # Up to 40% faster

                # Strike mode when very close
                if distance < FOOD_STRIKE_DISTANCE:
                    strike_speed = self.parameters["strike_speed"] * pursuit_boost
                    return (direction.x * strike_speed, direction.y * strike_speed)
                else:
                    # Stamina affects how long we can maintain top speed
                    # (simplified: higher stamina = faster sustained speed)
                    pursuit_speed = (
                        self.parameters["pursuit_speed"]
                        * pursuit_boost
                        * (0.8 + hunting_stamina * 0.2)
                    )
                    return (direction.x * pursuit_speed, direction.y * pursuit_speed)

        # No food visible - check last known location
        if self.last_food_pos and is_critical:
            direction = self._safe_normalize(self.last_food_pos - fish.pos)
            return direction.x * 0.9, direction.y * 0.9

        # Active exploration - more aggressive fish explore faster
        angle = (fish.age or 0) * 0.1  # Use age for varied exploration
        explore_speed = 0.7 + pursuit_aggression * 0.3  # 0.7-1.0 based on aggression
        return math.cos(angle) * explore_speed, math.sin(angle) * explore_speed
