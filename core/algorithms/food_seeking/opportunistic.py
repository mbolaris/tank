"""OpportunisticFeeder food-seeking behavior."""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from core.algorithms.base import BehaviorAlgorithm
from core.config.food import (
    FOOD_SPEED_BOOST_DISTANCE,
    PREDATOR_FLEE_DISTANCE_CONSERVATIVE,
    PREDATOR_FLEE_DISTANCE_DESPERATE,
)

if TYPE_CHECKING:
    from core.entities import Fish


@dataclass
class OpportunisticFeeder(BehaviorAlgorithm):
    """Only pursue food if it's close enough - IMPROVED to avoid starvation."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="opportunistic_feeder",
            parameters={
                "max_pursuit_distance": _rng.uniform(150, 300),  # INCREASED from 50-200
                "speed": _rng.uniform(0.9, 1.3),  # INCREASED from 0.6-1.0
                "exploration_speed": _rng.uniform(0.5, 0.8),  # NEW: explore when idle
            },
            rng=_rng,
        )
        self.exploration_angle = _rng.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        from core.entities import Crab

        # IMPROVEMENT: Check energy state
        is_critical = fish.energy / fish.max_energy < 0.3
        is_low = fish.energy / fish.max_energy < 0.5

        # IMPROVEMENT: Flee from predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            flee_threshold = (
                PREDATOR_FLEE_DISTANCE_DESPERATE
                if is_critical
                else PREDATOR_FLEE_DISTANCE_CONSERVATIVE
            )
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Expand pursuit when hungry
            max_dist = self.parameters["max_pursuit_distance"]
            if is_critical:
                max_dist *= 2  # Desperate: chase much further
            elif is_low:
                max_dist *= 1.5

            if distance < max_dist:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                # IMPROVEMENT: Speed up when close and when hungry
                speed = self.parameters["speed"]

                # Hunting traits
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                speed *= 1.0 + pursuit_aggression * 0.3

                if distance < FOOD_SPEED_BOOST_DISTANCE:
                    speed *= 1.3
                if is_critical:
                    speed *= 1.2
                return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Don't just idle - explore! (use environment RNG for determinism)
        if is_critical or is_low:
            self.exploration_angle += fish.environment.rng.uniform(-0.4, 0.4)
            ex_speed = self.parameters["exploration_speed"] * (1.5 if is_critical else 1.0)
            return (
                math.cos(self.exploration_angle) * ex_speed,
                math.sin(self.exploration_angle) * ex_speed,
            )

        return 0, 0
