"""Predator avoidance behavior algorithms.

This module contains 10 algorithms focused on avoiding and escaping from predators:
- PanicFlee: Flee directly away from predators at maximum speed
- StealthyAvoider: Move slowly and carefully away from predators
- FreezeResponse: Freeze when predator is near
- ErraticEvader: Make unpredictable movements when threatened
- VerticalEscaper: Escape vertically when threatened
- GroupDefender: Stay close to group for safety
- SpiralEscape: Spiral away from predators
- BorderHugger: Move to tank edges when threatened
- PerpendicularEscape: Escape perpendicular to predator's approach
- DistanceKeeper: Maintain safe distance from predators
"""

import random
import math
from typing import Tuple
from dataclasses import dataclass

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from agents import Food, Crab, Fish as FishClass


@dataclass
class PanicFlee(BehaviorAlgorithm):
    """Flee directly away from predators at maximum speed."""

    def __init__(self):
        super().__init__(
            algorithm_id="panic_flee",
            parameters={
                "flee_speed": random.uniform(1.2, 1.8),
                "panic_distance": random.uniform(100, 200),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["panic_distance"]:
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["flee_speed"], direction.y * self.parameters["flee_speed"]

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.7, direction.y * 0.7
        return 0, 0


@dataclass
class StealthyAvoider(BehaviorAlgorithm):
    """Move slowly and carefully away from predators."""

    def __init__(self):
        super().__init__(
            algorithm_id="stealthy_avoider",
            parameters={
                "stealth_speed": random.uniform(0.3, 0.6),
                "awareness_range": random.uniform(150, 250),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["awareness_range"]:
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["stealth_speed"], direction.y * self.parameters["stealth_speed"]

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class FreezeResponse(BehaviorAlgorithm):
    """Freeze when predator is near."""

    def __init__(self):
        super().__init__(
            algorithm_id="freeze_response",
            parameters={
                "freeze_distance": random.uniform(80, 150),
                "resume_distance": random.uniform(200, 300),
            }
        )
        self.is_frozen = False

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["freeze_distance"]:
                self.is_frozen = True
            elif distance > self.parameters["resume_distance"]:
                self.is_frozen = False

            if self.is_frozen:
                return 0, 0

        return 0, 0


@dataclass
class ErraticEvader(BehaviorAlgorithm):
    """Make unpredictable movements when threatened."""

    def __init__(self):
        super().__init__(
            algorithm_id="erratic_evader",
            parameters={
                "evasion_speed": random.uniform(0.8, 1.3),
                "randomness": random.uniform(0.5, 1.0),
                "threat_range": random.uniform(100, 180),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()

            if distance < self.parameters["threat_range"]:
                # Erratic movement with some directional bias away from predator
                away_dir = (fish.pos - nearest_predator.pos).normalize()

                # Add randomness perpendicular to escape direction
                perp_x = -away_dir.y
                perp_y = away_dir.x

                # Mix escape direction with random perpendicular movement
                randomness = self.parameters["randomness"]
                vx = away_dir.x * 0.6 + perp_x * random.uniform(-randomness, randomness)
                vy = away_dir.y * 0.6 + perp_y * random.uniform(-randomness, randomness)

                # Adjust speed based on proximity - panic more when closer
                proximity_multiplier = 1.0 + (1.0 - min(distance / self.parameters["threat_range"], 1.0)) * 0.8

                # Try to stay away from edges when fleeing (avoid getting cornered)
                edge_margin = 80
                if fish.pos.x < edge_margin:
                    vx += 0.3
                elif fish.pos.x > SCREEN_WIDTH - edge_margin:
                    vx -= 0.3
                if fish.pos.y < edge_margin:
                    vy += 0.3
                elif fish.pos.y > SCREEN_HEIGHT - edge_margin:
                    vy -= 0.3

                # Sometimes join nearby fish for group defense
                if random.random() < 0.2:
                    allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish]
                    if allies:
                        nearest_ally = min(allies, key=lambda f: (f.pos - fish.pos).length())
                        if (nearest_ally.pos - fish.pos).length() < 100:
                            ally_dir = (nearest_ally.pos - fish.pos).normalize()
                            vx += ally_dir.x * 0.3
                            vy += ally_dir.y * 0.3

                return vx * self.parameters["evasion_speed"] * proximity_multiplier, \
                       vy * self.parameters["evasion_speed"] * proximity_multiplier
        return 0, 0


@dataclass
class VerticalEscaper(BehaviorAlgorithm):
    """Escape vertically when threatened."""

    def __init__(self):
        super().__init__(
            algorithm_id="vertical_escaper",
            parameters={
                "escape_direction": random.choice([-1, 1]),  # -1 for up, 1 for down
                "escape_speed": random.uniform(1.0, 1.5),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            return 0, self.parameters["escape_direction"] * self.parameters["escape_speed"]

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class GroupDefender(BehaviorAlgorithm):
    """Stay close to group for safety."""

    def __init__(self):
        super().__init__(
            algorithm_id="group_defender",
            parameters={
                "group_strength": random.uniform(0.6, 1.0),
                "min_group_distance": random.uniform(30, 80),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 200:
            # Find nearest ally
            allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish]
            if allies:
                nearest_ally = min(allies, key=lambda f: (f.pos - fish.pos).length())
                direction = (nearest_ally.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * self.parameters["group_strength"], direction.y * self.parameters["group_strength"]

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class SpiralEscape(BehaviorAlgorithm):
    """Spiral away from predators."""

    def __init__(self):
        super().__init__(
            algorithm_id="spiral_escape",
            parameters={
                "spiral_rate": random.uniform(0.1, 0.3),
                "spiral_radius": random.uniform(20, 60),
            }
        )
        self.spiral_angle = 0

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            self.spiral_angle += self.parameters["spiral_rate"]
            escape_dir = (fish.pos - nearest_predator.pos).normalize()
            # Rotate the escape direction
            vx = escape_dir.x * math.cos(self.spiral_angle) - escape_dir.y * math.sin(self.spiral_angle)
            vy = escape_dir.x * math.sin(self.spiral_angle) + escape_dir.y * math.cos(self.spiral_angle)
            return vx, vy

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class BorderHugger(BehaviorAlgorithm):
    """Move to tank edges when threatened."""

    def __init__(self):
        super().__init__(
            algorithm_id="border_hugger",
            parameters={
                "border_preference": random.choice(['top', 'bottom', 'left', 'right']),
                "hug_speed": random.uniform(0.7, 1.1),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 180:
            if self.parameters["border_preference"] == 'top':
                return 0, -self.parameters["hug_speed"]
            elif self.parameters["border_preference"] == 'bottom':
                return 0, self.parameters["hug_speed"]
            elif self.parameters["border_preference"] == 'left':
                return -self.parameters["hug_speed"], 0
            else:  # right
                return self.parameters["hug_speed"], 0

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class PerpendicularEscape(BehaviorAlgorithm):
    """Escape perpendicular to predator's approach."""

    def __init__(self):
        super().__init__(
            algorithm_id="perpendicular_escape",
            parameters={
                "escape_speed": random.uniform(1.0, 1.4),
                "direction_preference": random.choice([-1, 1]),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            to_fish = (fish.pos - nearest_predator.pos)
            if to_fish.length() > 0:
                to_fish = to_fish.normalize()
                # Perpendicular vector
                perp_x = -to_fish.y * self.parameters["direction_preference"]
                perp_y = to_fish.x * self.parameters["direction_preference"]
                return perp_x * self.parameters["escape_speed"], perp_y * self.parameters["escape_speed"]

        # CRITICAL FIX: Seek food when not fleeing from predators
        energy_ratio = fish.energy / fish.max_energy
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            # Seek food more aggressively when hungry
            if energy_ratio < 0.7 or food_distance < 80:
                direction = (nearest_food.pos - fish.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                    # More aggressive seeking when very hungry
                    seek_speed = 0.6 + (1.0 - energy_ratio) * 0.4
                    return direction.x * seek_speed, direction.y * seek_speed

        return 0, 0


@dataclass
class DistanceKeeper(BehaviorAlgorithm):
    """Maintain safe distance from predators."""

    def __init__(self):
        super().__init__(
            algorithm_id="distance_keeper",
            parameters={
                "safe_distance": random.uniform(120, 200),
                "approach_speed": random.uniform(0.3, 0.6),
                "flee_speed": random.uniform(0.8, 1.2),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            direction = (fish.pos - nearest_predator.pos)
            if direction.length() > 0:
                direction = direction.normalize()

                energy_ratio = fish.energy / fish.max_energy

                # Adjust safe distance based on energy - stay farther when low energy (can't flee well)
                effective_safe_distance = self.parameters["safe_distance"]
                if energy_ratio < 0.3:
                    effective_safe_distance *= 1.4  # Stay farther when weak

                if distance < effective_safe_distance * 0.7:
                    # Too close, flee urgently
                    # Flee speed depends on energy
                    flee_multiplier = max(0.6, energy_ratio)  # Slower when low energy (realistic)
                    return direction.x * self.parameters["flee_speed"] * flee_multiplier, \
                           direction.y * self.parameters["flee_speed"] * flee_multiplier

                elif distance < effective_safe_distance:
                    # In the danger zone, maintain distance
                    # Strafe perpendicular while keeping distance
                    perp_x, perp_y = -direction.y, direction.x
                    if random.random() > 0.5:
                        perp_x, perp_y = -perp_x, -perp_y
                    return (direction.x * 0.4 + perp_x * 0.6) * self.parameters["flee_speed"], \
                           (direction.y * 0.4 + perp_y * 0.6) * self.parameters["flee_speed"]

                elif distance > effective_safe_distance * 1.5:
                    # Safe enough - can focus on food if hungry
                    if energy_ratio < 0.6:
                        nearest_food = self._find_nearest(fish, Food)
                        if nearest_food and (nearest_food.pos - fish.pos).length() < 150:
                            # Food nearby and relatively safe
                            food_dir = (nearest_food.pos - fish.pos).normalize()
                            # Move toward food but keep an eye on predator
                            return (food_dir.x * 0.7 + direction.x * 0.3) * 0.8, \
                                   (food_dir.y * 0.7 + direction.y * 0.3) * 0.8
                    # Otherwise just maintain awareness
                    return direction.x * self.parameters["approach_speed"] * 0.3, \
                           direction.y * self.parameters["approach_speed"] * 0.3

        # No predator - search for food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 0.6, direction.y * 0.6

        return 0, 0
