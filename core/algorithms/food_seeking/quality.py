"""FoodQualityOptimizer food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.food import (
    DANGER_WEIGHT_CRITICAL,
    DANGER_WEIGHT_LOW,
    DANGER_WEIGHT_NORMAL,
    FOOD_SAFETY_BONUS,
    FOOD_SAFETY_DISTANCE_RATIO,
    FOOD_SCORE_THRESHOLD_CRITICAL,
    FOOD_SCORE_THRESHOLD_LOW,
    FOOD_SCORE_THRESHOLD_NORMAL,
    PREDATOR_DANGER_ZONE_DIVISOR,
    PREDATOR_DANGER_ZONE_RADIUS,
    PREDATOR_DEFAULT_FAR_DISTANCE,
    PREDATOR_FLEE_DISTANCE_CAUTIOUS,
    PREDATOR_FLEE_DISTANCE_CONSERVATIVE,
    PREDATOR_FLEE_DISTANCE_DESPERATE,
)
from core.predictive_movement import predict_falling_intercept, predict_intercept_point


@dataclass
class FoodQualityOptimizer(BehaviorAlgorithm):
    """Prefer high-value food types."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="food_quality_optimizer",
            parameters={
                "quality_weight": _rng.uniform(0.5, 1.0),
                "distance_weight": _rng.uniform(0.3, 0.7),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab, Food
        from core.world import World

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        fish.get_energy_ratio()

        # Check predators first - but be less cautious when critically low energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (
            (nearest_predator.pos - fish.pos).length()
            if nearest_predator
            else PREDATOR_DEFAULT_FAR_DISTANCE
        )

        # In critical energy, only flee if predator is very close
        flee_threshold = (
            PREDATOR_FLEE_DISTANCE_DESPERATE
            if is_critical
            else (
                PREDATOR_FLEE_DISTANCE_CAUTIOUS if is_low else PREDATOR_FLEE_DISTANCE_CONSERVATIVE
            )
        )
        if nearest_predator and predator_distance < flee_threshold:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            flee_speed = 1.2 if is_critical else 1.4  # Conserve energy even when fleeing
            return direction.x * flee_speed, direction.y * flee_speed

        # Use World Protocol
        env: World = fish.environment
        foods = [f for f in env.get_agents_of_type(Food) if isinstance(f, Food)]
        best_food: Food | None = None
        best_score = -float("inf")

        # IMPROVEMENT: Also consider remembered food locations if no food visible
        remembered_locations = (
            fish.get_remembered_food_locations()
            if hasattr(fish, "get_remembered_food_locations")
            else []
        )

        for food in foods:
            distance = (food.pos - fish.pos).length()
            quality = food.get_energy_value()

            # Check if predator is near this food (danger score)
            danger_score = 0.0
            if nearest_predator:
                predator_food_dist = (nearest_predator.pos - food.pos).length()
                if predator_food_dist < PREDATOR_DANGER_ZONE_RADIUS:
                    danger_score = (
                        PREDATOR_DANGER_ZONE_RADIUS - predator_food_dist
                    ) / PREDATOR_DANGER_ZONE_DIVISOR

            # IMPROVEMENT: Smarter danger weighting based on energy state
            # Critical energy: mostly ignore danger
            # Low energy: some caution
            # Normal energy: high caution
            if is_critical:
                danger_weight = DANGER_WEIGHT_CRITICAL
            elif is_low:
                danger_weight = DANGER_WEIGHT_LOW
            else:
                danger_weight = DANGER_WEIGHT_NORMAL

            # IMPROVEMENT: Increase quality weight when low energy
            quality_weight = self.parameters["quality_weight"] * (1.5 if is_low else 1.0)
            distance_weight = self.parameters["distance_weight"] * (1.3 if is_critical else 1.0)

            # Calculate value: high quality, close distance, low danger
            score = (
                quality * quality_weight - distance * distance_weight - danger_score * danger_weight
            )

            # IMPROVEMENT: Bonus for food that's closer than predator
            if nearest_predator and distance < predator_distance * FOOD_SAFETY_DISTANCE_RATIO:
                score += FOOD_SAFETY_BONUS

            if score > best_score:
                best_score = score
                best_food = food

        # IMPROVEMENT: Lower threshold for pursuing food when critically low
        min_score_threshold = (
            FOOD_SCORE_THRESHOLD_CRITICAL
            if is_critical
            else (FOOD_SCORE_THRESHOLD_LOW if is_low else FOOD_SCORE_THRESHOLD_NORMAL)
        )

        if best_food and best_score > min_score_threshold:
            distance_to_food = (best_food.pos - fish.pos).length()

            # Use prediction for moving food
            prediction_skill = fish.genome.behavioral.prediction_skill.value
            target_pos = best_food.pos

            target_pos = best_food.pos

            if hasattr(best_food, "vel") and best_food.vel.length() > 0.01:
                # Check for acceleration
                is_accelerating = False
                acceleration = 0.0
                if hasattr(best_food, "food_properties"):
                    from core.config.food import FOOD_SINK_ACCELERATION

                    raw_sink_multiplier = best_food.food_properties.get("sink_multiplier", 1.0)
                    try:
                        sink_multiplier = float(cast(Any, raw_sink_multiplier))
                    except (TypeError, ValueError):
                        sink_multiplier = 1.0
                    acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                    if acceleration > 0 and best_food.vel.y >= 0:
                        is_accelerating = True

                intercept_point = None
                if is_accelerating:
                    intercept_point, _ = predict_falling_intercept(
                        fish.pos, fish.speed, best_food.pos, best_food.vel, acceleration
                    )
                else:
                    intercept_point, _ = predict_intercept_point(
                        fish.pos, fish.speed, best_food.pos, best_food.vel
                    )

                if intercept_point and prediction_skill > 0.3:
                    # Stronger commitment to prediction
                    skill_factor = 0.2 + (prediction_skill * 0.8)
                    target_pos = Vector2(
                        best_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                        best_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                    )

            direction = self._safe_normalize(target_pos - fish.pos)
            # IMPROVEMENT: Speed based on urgency and distance
            base_speed = 1.1 if is_critical else 0.9
            speed = base_speed + min(50 / max(distance_to_food, 1), 0.5)

            # Hunting traits boost
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= 1.0 + pursuit_aggression * 0.2

            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: If no good food found but have memories and critically low, go to memory
        if is_critical and remembered_locations:
            closest_memory = min(remembered_locations, key=lambda pos: (pos - fish.pos).length())
            direction = self._safe_normalize(closest_memory - fish.pos)
            return direction.x * 0.8, direction.y * 0.8

        return 0, 0
