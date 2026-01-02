"""BottomFeeder food-seeking behavior."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm
from core.config.display import SCREEN_HEIGHT


@dataclass
class BottomFeeder(BehaviorAlgorithm):
    """Stay near bottom to catch sinking food."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="bottom_feeder",
            parameters={
                "preferred_depth": _rng.uniform(0.7, 0.9),  # 70-90% from top
                "search_speed": _rng.uniform(0.4, 0.8),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]
        vy = (target_y - fish.pos.y) / 100

        nearest_food = self._find_nearest_food(fish)
        vx = 0
        if nearest_food:
            # Prediction helps catch sinking food
            prediction_skill = fish.genome.behavioral.prediction_skill.value
            target_x = nearest_food.pos.x
            if hasattr(nearest_food, "vel"):
                target_x += nearest_food.vel.x * (prediction_skill * 20)

            vx = (target_x - fish.pos.x) / 100

            # Aggression boosts tracking speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            vx *= 1.0 + pursuit_aggression * 0.5
        else:
            vx = (
                self.parameters["search_speed"]
                if self.rng.random() > 0.5
                else -self.parameters["search_speed"]
            )

        return vx, vy
