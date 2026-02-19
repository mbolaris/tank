"""ZigZagForager food-seeking behavior."""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm
from core.config.food import FOOD_PURSUIT_RANGE_CLOSE


@dataclass
class ZigZagForager(BehaviorAlgorithm):
    """Move in zigzag pattern to maximize food discovery."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="zigzag_forager",
            parameters={
                "zigzag_frequency": _rng.uniform(0.02, 0.08),
                "zigzag_amplitude": _rng.uniform(0.5, 1.2),
                "forward_speed": _rng.uniform(0.6, 1.0),
            },
            rng=_rng,
        )
        self.zigzag_phase = _rng.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        # Check for nearby food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food and (nearest_food.pos - fish.pos).length() < FOOD_PURSUIT_RANGE_CLOSE:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)

            # Aggression boosts chase speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed_boost = 1.0 + pursuit_aggression * 0.3

            return direction.x * speed_boost, direction.y * speed_boost

        # Zigzag movement
        self.zigzag_phase += self.parameters["zigzag_frequency"]
        vx = self.parameters["forward_speed"]
        vy = math.sin(self.zigzag_phase) * self.parameters["zigzag_amplitude"]

        return vx, vy
