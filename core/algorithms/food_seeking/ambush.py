"""AmbushFeeder food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.predictive_movement import (predict_falling_intercept,
                                      predict_intercept_point)


@dataclass
class AmbushFeeder(BehaviorAlgorithm):
    """Wait in one spot for food to come close."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="ambush_feeder",
            parameters={
                "strike_distance": _rng.uniform(30, 80),
                "strike_speed": _rng.uniform(1.0, 1.5),
                "patience": _rng.uniform(0.5, 1.0),
            },
            rng=_rng,
        )

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
                                nearest_food.pos.x * (1 - skill_factor)
                                + intercept_point.x * skill_factor,
                                nearest_food.pos.y * (1 - skill_factor)
                                + intercept_point.y * skill_factor,
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
