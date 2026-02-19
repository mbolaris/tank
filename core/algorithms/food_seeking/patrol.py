"""PatrolFeeder food-seeking behavior."""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.food import (
    FOOD_PURSUIT_RANGE_DESPERATE,
    FOOD_PURSUIT_RANGE_NORMAL,
    PREDATOR_FLEE_DISTANCE_NORMAL,
)

if TYPE_CHECKING:
    from core.entities import Fish


@dataclass
class PatrolFeeder(BehaviorAlgorithm):
    """Patrol in a pattern looking for food - IMPROVED with better detection."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="patrol_feeder",
            parameters={
                "patrol_radius": _rng.uniform(100, 200),  # INCREASED from 50-150
                "patrol_speed": _rng.uniform(0.8, 1.2),  # INCREASED from 0.5-1.0
                "food_priority": _rng.uniform(1.0, 1.4),  # INCREASED from 0.6-1.0
            },
            rng=_rng,
        )
        self.patrol_center: Vector2 | None = None
        self.patrol_angle = _rng.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        # IMPROVEMENT: Check energy and predators
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_NORMAL:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Check for nearby food first - EXPANDED detection
        nearest_food = self._find_nearest_food(fish)
        detection_range = (
            FOOD_PURSUIT_RANGE_DESPERATE if is_desperate else FOOD_PURSUIT_RANGE_NORMAL
        )
        if nearest_food and (nearest_food.pos - fish.pos).length() < detection_range:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            # IMPROVEMENT: Faster when desperate
            speed = self.parameters["food_priority"] * (1.3 if is_desperate else 1.0)

            # Hunting traits
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= 1.0 + pursuit_aggression * 0.25

            return direction.x * speed, direction.y * speed

        # Otherwise patrol - FASTER rotation
        if self.patrol_center is None:
            self.patrol_center = Vector2(fish.pos.x, fish.pos.y)

        patrol_center = self.patrol_center
        assert patrol_center is not None
        self.patrol_angle += 0.15  # INCREASED from 0.05 for faster patrol
        target_x = patrol_center.x + math.cos(self.patrol_angle) * self.parameters["patrol_radius"]
        target_y = patrol_center.y + math.sin(self.patrol_angle) * self.parameters["patrol_radius"]
        direction = self._safe_normalize(Vector2(target_x, target_y) - fish.pos)
        # IMPROVEMENT: Patrol faster to cover more ground
        speed = self.parameters["patrol_speed"] * (1.3 if is_desperate else 1.0)
        return direction.x * speed, direction.y * speed
