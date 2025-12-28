"""CooperativeForager food-seeking behavior."""


import math
import random
from dataclasses import dataclass
from typing import Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm
from core.config.food import (
    FOOD_PURSUIT_RANGE_DESPERATE,
    FOOD_PURSUIT_RANGE_NORMAL,
    PREDATOR_PROXIMITY_THRESHOLD,
    SOCIAL_FOLLOW_MAX_DISTANCE,
    SOCIAL_FOOD_PROXIMITY_THRESHOLD,
    SOCIAL_SIGNAL_DETECTION_RANGE,
)
from core.entities import Crab

@dataclass
class CooperativeForager(BehaviorAlgorithm):
    """Follow other fish to food sources - HEAVILY IMPROVED."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(
            algorithm_id="cooperative_forager",
            parameters={
                "follow_strength": (rng or random.Random()).uniform(0.8, 1.2),  # INCREASED from 0.5-0.9
                "independence": (rng or random.Random()).uniform(0.5, 0.8),  # INCREASED from 0.2-0.5
                "food_pursuit_speed": (rng or random.Random()).uniform(1.1, 1.4),  # NEW
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy state
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # OPTIMIZATION: Cache fish position
        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Check for predators - IMPROVED avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            # OPTIMIZATION: Inline distance calculation
            pred_x = nearest_predator.pos.x
            pred_y = nearest_predator.pos.y
            dx = pred_x - fish_x
            dy = pred_y - fish_y
            pred_dist = (dx * dx + dy * dy) ** 0.5

            if pred_dist < PREDATOR_PROXIMITY_THRESHOLD:
                # NEW: Broadcast danger signal
                if hasattr(fish.environment, "communication_system"):
                    from core.fish_communication import SignalType

                    fish.environment.communication_system.broadcast_signal(
                        SignalType.DANGER_WARNING,
                        fish.pos,
                        target_location=nearest_predator.pos,
                        strength=1.0,
                        urgency=1.0,
                    )

                # OPTIMIZATION: Inline normalization (away from predator)
                if pred_dist > 0.001:
                    norm_x = -dx / pred_dist
                    norm_y = -dy / pred_dist
                else:
                    angle = self.rng.random() * 6.283185  # 2*pi
                    norm_x = math.cos(angle)
                    norm_y = math.sin(angle)
                return norm_x * 1.3, norm_y * 1.3

        # Look for food directly first - EXPANDED range
        nearest_food = self._find_nearest_food(fish)
        detection_range = FOOD_PURSUIT_RANGE_DESPERATE if is_desperate else FOOD_PURSUIT_RANGE_NORMAL
        if nearest_food:
            # OPTIMIZATION: Inline distance calculation
            food_x = nearest_food.pos.x
            food_y = nearest_food.pos.y
            dx = food_x - fish_x
            dy = food_y - fish_y
            food_dist = (dx * dx + dy * dy) ** 0.5

            if food_dist < detection_range:
                # NEW: Broadcast food found signal (if social)
                if (
                    hasattr(fish.environment, "communication_system")
                    and fish.genome.behavioral.social_tendency.value > 0.5
                ):
                    from core.fish_communication import SignalType

                    fish.environment.communication_system.broadcast_signal(
                        SignalType.FOOD_FOUND,
                        fish.pos,
                        target_location=nearest_food.pos,
                        strength=fish.genome.behavioral.social_tendency.value,  # More social = stronger signal
                        urgency=0.7,
                    )

                # Food is close, go for it directly - FASTER
                # OPTIMIZATION: Inline normalization
                if food_dist > 0.001:
                    norm_x = dx / food_dist
                    norm_y = dy / food_dist
                else:
                    norm_x, norm_y = 1.0, 0.0
                speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
                return norm_x * speed, norm_y * speed

        # NEW: Listen for food signals from communication system
        best_signal_target = None
        if hasattr(fish.environment, "communication_system"):
            from core.fish_communication import SignalType

            food_signals = fish.environment.communication_system.get_nearby_signals(
                fish.pos, signal_type=SignalType.FOOD_FOUND
            )

            if food_signals:
                # Find best signal
                best_signal = max(food_signals, key=lambda s: s.strength * s.urgency)
                if best_signal.target_location:
                    best_signal_target = best_signal.target_location

        # Check if any nearby fish are near food (social learning)
        # OPTIMIZATION: Skip expensive social learning at high populations
        env = fish.environment

        best_target = None
        best_score = 0

        # Only do social learning if nearby fish count is reasonable
        if hasattr(env, "nearby_evolving_agents") and hasattr(env, "nearby_resources"):
            nearby_fish_list = env.nearby_evolving_agents(fish, SOCIAL_FOLLOW_MAX_DISTANCE)

            # OPTIMIZATION: Skip if too many fish nearby to avoid O(n*k) queries
            if len(nearby_fish_list) <= 8:
                for other_fish in nearby_fish_list:
                    other_x = other_fish.pos.x
                    other_y = other_fish.pos.y
                    dx_fish = other_x - fish_x
                    dy_fish = other_y - fish_y
                    fish_dist = (dx_fish * dx_fish + dy_fish * dy_fish) ** 0.5

                    # Check nearby food around this fish
                    nearby_food = env.nearby_resources(other_fish, SOCIAL_FOOD_PROXIMITY_THRESHOLD)
                    if nearby_food:
                        # Just use first food found
                        food = nearby_food[0]
                        food_x = food.pos.x
                        food_y = food.pos.y
                        dx_food = other_x - food_x
                        dy_food = other_y - food_y
                        food_dist = (dx_food * dx_food + dy_food * dy_food) ** 0.5

                        if food_dist < SOCIAL_FOOD_PROXIMITY_THRESHOLD:
                            score = (100 - food_dist) * (200 - fish_dist) / 100
                            if score > best_score:
                                best_score = score
                                best_target = other_fish.pos

        # NEW: Prefer signal target if it's good
        if best_signal_target:
            signal_dist = (best_signal_target - fish.pos).length()
            if signal_dist < SOCIAL_SIGNAL_DETECTION_RANGE:
                best_target = best_signal_target
                best_score = max(best_score, 50)  # Give it decent priority

        if best_target:
            direction = self._safe_normalize(best_target - fish.pos)
            # Follow with varying intensity
            intensity = min(best_score / 100, 1.0)
            return (
                direction.x * self.parameters["follow_strength"] * intensity,
                direction.y * self.parameters["follow_strength"] * intensity,
            )

        # No one to follow, explore independently
        if self.rng.random() < self.parameters["independence"]:
            return self.rng.uniform(-0.5, 0.5), self.rng.uniform(-0.5, 0.5)

        return 0, 0
