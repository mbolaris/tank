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

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm
from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH


@dataclass
class PanicFlee(BehaviorAlgorithm):
    """Flee directly away from predators at maximum speed."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="panic_flee",
            parameters={
                "flee_speed": rng.uniform(1.2, 1.8),
                "panic_distance": rng.uniform(100, 200),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        predator, distance, escape_dir = self._get_predator_threat(
            fish, self.parameters["panic_distance"]
        )
        if predator:
            return (
                escape_dir.x * self.parameters["flee_speed"],
                escape_dir.y * self.parameters["flee_speed"],
            )

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7
        return 0, 0


@dataclass
class StealthyAvoider(BehaviorAlgorithm):
    """Move slowly and carefully away from predators."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="stealthy_avoider",
            parameters={
                "stealth_speed": rng.uniform(0.3, 0.6),
                "awareness_range": rng.uniform(150, 250),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        predator, distance, escape_dir = self._get_predator_threat(
            fish, self.parameters["awareness_range"]
        )
        if predator:
            return (
                escape_dir.x * self.parameters["stealth_speed"],
                escape_dir.y * self.parameters["stealth_speed"],
            )

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = nearest_food.pos - fish.pos
                if direction.length() > 0:
                    direction = direction.normalize()
                    return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class FreezeResponse(BehaviorAlgorithm):
    """Freeze when predator is near, but prioritize survival over safety when starving."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="freeze_response",
            parameters={
                "freeze_distance": rng.uniform(50, 90),  # Reduced from 80-150
                "resume_distance": rng.uniform(120, 180),  # Reduced from 200-300
                "desperation_threshold": rng.uniform(30, 50),  # Energy % to ignore threats
            },
            rng=rng,
        )
        self.is_frozen = False
        self.search_angle = rng.uniform(0, 6.28)  # For systematic food search

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        """Freeze when predator is near, but prioritize food when starving.

        AI-IMPROVED v2: Survival rate was 0%, all deaths from starvation.
        Key changes:
        - Reduced freeze distances (fish were freezing too often)
        - Added energy-aware behavior (desperate fish ignore predators)
        - Increased food-seeking speed from 0.5 to 0.8-1.0
        - Better food search pattern instead of random wandering
        """

        # Calculate energy percentage
        energy_percent = (fish.energy / fish.max_energy) * 100

        # When desperate (low energy), prioritize food over safety
        is_desperate = energy_percent < self.parameters["desperation_threshold"]

        # Check for predators (but may ignore if desperate)
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and not is_desperate:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["freeze_distance"]:
                self.is_frozen = True
            elif distance > self.parameters["resume_distance"]:
                self.is_frozen = False

            if self.is_frozen:
                return 0, 0  # Freeze in place when threatened
        else:
            # No predator or desperate - unfreeze
            self.is_frozen = False

        # Seek food aggressively when not frozen
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)

            # Speed based on energy level (desperate = faster)
            if is_desperate:
                speed = 1.0  # Full speed when starving
            elif energy_percent < 60:
                speed = 0.8  # Medium speed when moderately hungry
            else:
                speed = 0.6  # Cautious speed when comfortable

            return direction.x * speed, direction.y * speed

        # No food visible - systematic search instead of random wandering
        # Spiral search pattern to cover more area
        self.search_angle += 0.15
        search_speed = 0.7 if is_desperate else 0.4

        import math

        return (
            math.cos(self.search_angle) * search_speed,
            math.sin(self.search_angle) * search_speed,
        )


@dataclass
class ErraticEvader(BehaviorAlgorithm):
    """Make unpredictable movements when threatened."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="erratic_evader",
            parameters={
                "evasion_speed": rng.uniform(0.8, 1.3),
                "randomness": rng.uniform(0.5, 1.0),
                "threat_range": rng.uniform(100, 180),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab, Fish

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()

            if distance < self.parameters["threat_range"]:
                # Erratic movement with some directional bias away from predator
                away_dir = self._safe_normalize(fish.pos - nearest_predator.pos)

                # Add randomness perpendicular to escape direction
                perp_x = -away_dir.y
                perp_y = away_dir.x

                # Mix escape direction with random perpendicular movement (use environment RNG)
                randomness = self.parameters["randomness"]
                rng = fish.environment.rng
                vx = away_dir.x * 0.6 + perp_x * rng.uniform(-randomness, randomness)
                vy = away_dir.y * 0.6 + perp_y * rng.uniform(-randomness, randomness)

                # Adjust speed based on proximity - panic more when closer
                proximity_multiplier = (
                    1.0 + (1.0 - min(distance / self.parameters["threat_range"], 1.0)) * 0.8
                )

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

                # Sometimes join nearby fish for group defense (use environment RNG)
                if fish.environment.rng.random() < 0.2:
                    allies = [f for f in fish.environment.get_agents_of_type(Fish) if f != fish]
                    if allies:
                        nearest_ally = min(allies, key=lambda f: (f.pos - fish.pos).length())
                        if (nearest_ally.pos - fish.pos).length() < 100:
                            ally_dir = self._safe_normalize(nearest_ally.pos - fish.pos)
                            vx += ally_dir.x * 0.3
                            vy += ally_dir.y * 0.3

                return (
                    vx * self.parameters["evasion_speed"] * proximity_multiplier,
                    vy * self.parameters["evasion_speed"] * proximity_multiplier,
                )
        return 0, 0


@dataclass
class VerticalEscaper(BehaviorAlgorithm):
    """Escape vertically when threatened."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="vertical_escaper",
            parameters={
                "escape_direction": rng.choice([-1, 1]),  # -1 for up, 1 for down
                "escape_speed": rng.uniform(1.0, 1.5),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            return 0, self.parameters["escape_direction"] * self.parameters["escape_speed"]

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class GroupDefender(BehaviorAlgorithm):
    """Stay close to group for safety."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="group_defender",
            parameters={
                "group_strength": rng.uniform(0.6, 1.0),
                "min_group_distance": rng.uniform(30, 80),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab, Fish

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 200:
            # Find nearest ally
            allies = [f for f in fish.environment.get_agents_of_type(Fish) if f != fish]
            if allies:
                nearest_ally = min(allies, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(nearest_ally.pos - fish.pos)
                return (
                    direction.x * self.parameters["group_strength"],
                    direction.y * self.parameters["group_strength"],
                )

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class SpiralEscape(BehaviorAlgorithm):
    """Spiral away from predators."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="spiral_escape",
            parameters={
                "spiral_rate": rng.uniform(0.1, 0.3),
                "spiral_radius": rng.uniform(20, 60),
            },
            rng=rng,
        )
        self.spiral_angle = 0.0

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            self.spiral_angle += self.parameters["spiral_rate"]
            escape_dir = self._safe_normalize(fish.pos - nearest_predator.pos)
            # Rotate the escape direction
            vx = escape_dir.x * math.cos(self.spiral_angle) - escape_dir.y * math.sin(
                self.spiral_angle
            )
            vy = escape_dir.x * math.sin(self.spiral_angle) + escape_dir.y * math.cos(
                self.spiral_angle
            )
            return vx, vy

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class BorderHugger(BehaviorAlgorithm):
    """Move to tank edges when threatened."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="border_hugger",
            parameters={
                "border_preference": rng.choice(["top", "bottom", "left", "right"]),
                "hug_speed": rng.uniform(0.7, 1.1),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 180:
            if self.parameters["border_preference"] == "top":
                return 0, -self.parameters["hug_speed"]
            elif self.parameters["border_preference"] == "bottom":
                return 0, self.parameters["hug_speed"]
            elif self.parameters["border_preference"] == "left":
                return -self.parameters["hug_speed"], 0
            else:  # right
                return self.parameters["hug_speed"], 0

        # Seek food when safe
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.7:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.6, direction.y * 0.6
        return 0, 0


@dataclass
class PerpendicularEscape(BehaviorAlgorithm):
    """Escape perpendicular to predator's approach."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="perpendicular_escape",
            parameters={
                "escape_speed": rng.uniform(1.0, 1.4),
                "direction_preference": rng.choice([-1, 1]),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            to_fish = self._safe_normalize(fish.pos - nearest_predator.pos)
            # Perpendicular vector
            perp_x = -to_fish.y * self.parameters["direction_preference"]
            perp_y = to_fish.x * self.parameters["direction_preference"]
            return (
                perp_x * self.parameters["escape_speed"],
                perp_y * self.parameters["escape_speed"],
            )

        # CRITICAL FIX: Seek food when not fleeing from predators
        energy_ratio = fish.energy / fish.max_energy
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            # Seek food more aggressively when hungry
            if energy_ratio < 0.7 or food_distance < 80:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                # More aggressive seeking when very hungry
                seek_speed = 0.6 + (1.0 - energy_ratio) * 0.4
                return direction.x * seek_speed, direction.y * seek_speed

        return 0, 0


@dataclass
class DistanceKeeper(BehaviorAlgorithm):
    """Maintain safe distance from predators."""

    def __init__(self, rng: random.Random | None = None):
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        super().__init__(
            algorithm_id="distance_keeper",
            parameters={
                "safe_distance": rng.uniform(120, 200),
                "approach_speed": rng.uniform(0.3, 0.6),
                "flee_speed": rng.uniform(0.8, 1.2),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: random.Random | None = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)

            energy_ratio = fish.energy / fish.max_energy

            # Adjust safe distance based on energy - stay farther when low energy (can't flee well)
            effective_safe_distance = self.parameters["safe_distance"]
            if energy_ratio < 0.3:
                effective_safe_distance *= 1.4  # Stay farther when weak

            if distance < effective_safe_distance * 0.7:
                # Too close, flee urgently
                # Flee speed depends on energy
                flee_multiplier = max(0.6, energy_ratio)  # Slower when low energy (realistic)
                return (
                    direction.x * self.parameters["flee_speed"] * flee_multiplier,
                    direction.y * self.parameters["flee_speed"] * flee_multiplier,
                )

            elif distance < effective_safe_distance:
                # In the danger zone, maintain distance
                # Strafe perpendicular while keeping distance (use environment RNG)
                perp_x, perp_y = -direction.y, direction.x
                if fish.environment.rng.random() > 0.5:
                    perp_x, perp_y = -perp_x, -perp_y
                return (direction.x * 0.4 + perp_x * 0.6) * self.parameters["flee_speed"], (
                    direction.y * 0.4 + perp_y * 0.6
                ) * self.parameters["flee_speed"]

            elif distance > effective_safe_distance * 1.5:
                # Safe enough - can focus on food if hungry
                if energy_ratio < 0.6:
                    nearest_food = self._find_nearest_food(fish)
                    if nearest_food and (nearest_food.pos - fish.pos).length() < 150:
                        # Food nearby and relatively safe
                        food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                        # Move toward food but keep an eye on predator
                        return (food_dir.x * 0.7 + direction.x * 0.3) * 0.8, (
                            food_dir.y * 0.7 + direction.y * 0.3
                        ) * 0.8
                # Otherwise just maintain awareness
                return (
                    direction.x * self.parameters["approach_speed"] * 0.3,
                    direction.y * self.parameters["approach_speed"] * 0.3,
                )

        # No predator - search for food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * 0.6, direction.y * 0.6

        return 0, 0
