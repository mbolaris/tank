"""EnergyAwareFoodSeeker food-seeking behavior."""


import random
from dataclasses import dataclass
from typing import Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm
from core.config.food import (
    PREDATOR_DEFAULT_FAR_DISTANCE,
    PREDATOR_GUARDING_FOOD_DISTANCE,
    PREDATOR_PROXIMITY_THRESHOLD,
)
from core.entities import Crab

@dataclass
class EnergyAwareFoodSeeker(BehaviorAlgorithm):
    """Seek food more aggressively when energy is low."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="energy_aware_food_seeker",
            parameters={
                "urgency_threshold": (rng or random).uniform(0.3, 0.7),
                "calm_speed": (rng or random).uniform(0.3, 0.6),
                "urgent_speed": (rng or random).uniform(0.8, 1.2),
            },
            rng=rng,
        )

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
