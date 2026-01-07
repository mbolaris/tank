"""GreedyFoodSeeker food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.food import (
    CHASE_DISTANCE_CRITICAL,
    CHASE_DISTANCE_LOW,
    CHASE_DISTANCE_SAFE_BASE,
    FOOD_MEMORY_RECORD_DISTANCE,
    PROXIMITY_BOOST_DIVISOR,
    PROXIMITY_BOOST_MULTIPLIER,
    URGENCY_BOOST_CRITICAL,
    URGENCY_BOOST_LOW,
)
from core.predictive_movement import predict_falling_intercept, predict_intercept_point


@dataclass
class GreedyFoodSeeker(BehaviorAlgorithm):
    """Always move directly toward nearest food.

    Uses genetic hunting traits to affect behavior:
    - pursuit_aggression: How fast to chase moving food
    - prediction_skill: How well to predict food movement
    - hunting_stamina: How long to sustain high-speed pursuit
    """

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="greedy_food_seeker",
            parameters={
                "speed_multiplier": _rng.uniform(0.7, 1.3),
                "detection_range": _rng.uniform(0.5, 1.0),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Use helper to check energy state (consolidates 3 method calls)
        is_critical, is_low, energy_ratio = self._get_energy_state(fish)

        # Use helper to check for predators and flee if necessary
        should_flee, flee_x, flee_y = self._should_flee_predator(fish)
        if should_flee:
            return flee_x, flee_y

        # Get hunting traits from genome (with defaults if not present)
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        prediction_skill = fish.genome.behavioral.prediction_skill.value

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()

            # IMPROVEMENT: Smarter chase distance calculation
            # Higher pursuit_aggression = willing to chase farther
            base_chase = CHASE_DISTANCE_SAFE_BASE * (1.0 + pursuit_aggression * 0.5)
            if is_critical:
                max_chase_distance = CHASE_DISTANCE_CRITICAL
            elif is_low:
                max_chase_distance = CHASE_DISTANCE_LOW
            else:
                max_chase_distance = base_chase + (energy_ratio * base_chase * 0.5)

            if distance < max_chase_distance:
                # Use predictive interception for moving food
                # Better prediction_skill = more accurate interception
                target_pos = nearest_food.pos

                # Check for moving food (falling or swimming)
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
                    is_accelerating = False
                    acceleration = 0.0

                    # Check for acceleration (falling food)
                    if hasattr(nearest_food, "food_properties"):
                        from core.config.food import FOOD_SINK_ACCELERATION

                        sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                        acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                        if acceleration > 0 and nearest_food.vel.y >= 0:
                            is_accelerating = True

                    # Calculate optimal intercept point
                    intercept_point = None
                    if is_accelerating:
                        intercept_point, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                        )
                    else:
                        intercept_point, _ = predict_intercept_point(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                        )

                    if intercept_point and prediction_skill > 0.3:
                        # Blend toward optimal intercept based on skill
                        # FIX: Changed blending logic to favor intercept more strongly
                        # Even moderate skill should commit to the prediction
                        skill_factor = 0.2 + (prediction_skill * 0.8)  # 0.3 -> 0.44, 0.9 -> 0.92

                        target_pos = Vector2(
                            nearest_food.pos.x * (1 - skill_factor)
                            + intercept_point.x * skill_factor,
                            nearest_food.pos.y * (1 - skill_factor)
                            + intercept_point.y * skill_factor,
                        )
                else:
                    target_pos = nearest_food.pos

                direction = self._safe_normalize(target_pos - fish.pos)

                # Speed based on urgency, distance, and HUNTING TRAITS
                base_speed = self.parameters["speed_multiplier"]

                # Speed up when closer to food
                proximity_boost = (
                    1.0 - min(distance / PROXIMITY_BOOST_DIVISOR, 1.0)
                ) * PROXIMITY_BOOST_MULTIPLIER

                # Urgency boost when low/critical energy
                urgency_boost = (
                    URGENCY_BOOST_CRITICAL if is_critical else (URGENCY_BOOST_LOW if is_low else 0)
                )

                # NEW: Hunting traits affect speed
                # pursuit_aggression adds speed when chasing
                # hunting_stamina affects whether we maintain speed (simplified for now)
                pursuit_boost = pursuit_aggression * 0.3  # Up to 30% speed boost

                speed = base_speed * (1.0 + proximity_boost + urgency_boost + pursuit_boost)

                # Remember successful food locations
                if hasattr(fish, "memory_system") and distance < FOOD_MEMORY_RECORD_DISTANCE:
                    from core.fish_memory import MemoryType

                    fish.memory_system.add_memory(
                        MemoryType.FOOD_LOCATION, nearest_food.pos, strength=0.8
                    )

                return direction.x * speed, direction.y * speed

        # Use enhanced memory system if no food found
        if (is_critical or is_low) and hasattr(fish, "memory_system"):
            from core.fish_memory import MemoryType

            best_food_memory = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
            if best_food_memory:
                direction = self._safe_normalize(best_food_memory.location - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

        return 0, 0
