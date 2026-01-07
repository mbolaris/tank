"""SurfaceSkimmer food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from core.algorithms.base import BehaviorAlgorithm
from core.config.display import SCREEN_HEIGHT
from core.config.food import PREDATOR_FLEE_DISTANCE_CONSERVATIVE

if TYPE_CHECKING:
    from core.entities import Fish

from core.predictive_movement import predict_falling_intercept


@dataclass
class SurfaceSkimmer(BehaviorAlgorithm):
    """Stay near surface to catch falling food - IMPROVED for better survival."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="surface_skimmer",
            parameters={
                "preferred_depth": _rng.uniform(0.1, 0.25),  # 10-25% from top
                "horizontal_speed": _rng.uniform(0.8, 1.3),  # INCREASED from 0.5-1.0
                "dive_for_food_threshold": _rng.uniform(150, 250),  # NEW: will dive for food
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        from core.entities import Crab

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
                speed *= 1.0 + pursuit_aggression * 0.3

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
            if self.rng.random() < 0.02:  # 2% chance per frame to reverse
                self.parameters["horizontal_speed"] *= -1
            return vx, vy
