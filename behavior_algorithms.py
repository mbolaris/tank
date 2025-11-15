"""Behavior algorithms for fish - a collection of parametrizable strategies for evolution.

This module provides ~50 different behavior algorithms that fish can inherit and evolve.
Each algorithm has tunable parameters that mutate during reproduction.
"""

import random
import math
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, List, Optional, TYPE_CHECKING
from pygame.math import Vector2
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from agents import Fish
    from environment import Environment


@dataclass
class BehaviorAlgorithm(ABC):
    """Base class for all behavior algorithms.

    Each algorithm has:
    - A unique algorithm_id
    - A set of parameters that can mutate
    - An execute method that determines fish movement
    """

    algorithm_id: str
    parameters: Dict[str, float] = field(default_factory=dict)

    @abstractmethod
    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        """Execute the algorithm and return desired velocity.

        Args:
            fish: The fish using this algorithm

        Returns:
            Tuple of (velocity_x, velocity_y) as direction (-1 to 1 range)
        """
        pass

    def mutate_parameters(self, mutation_rate: float = 0.15, mutation_strength: float = 0.2) -> None:
        """Mutate the algorithm's parameters.

        Args:
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of mutations
        """
        for key in self.parameters:
            if random.random() < mutation_rate:
                self.parameters[key] += random.gauss(0, mutation_strength)
                self.parameters[key] = max(0.0, min(1.0, self.parameters[key]))

    @classmethod
    def random_instance(cls) -> 'BehaviorAlgorithm':
        """Create a random instance of this algorithm with random parameters."""
        raise NotImplementedError("Subclasses must implement random_instance")


# ============================================================================
# FOOD SEEKING ALGORITHMS (12 algorithms)
# ============================================================================

@dataclass
class GreedyFoodSeeker(BehaviorAlgorithm):
    """Always move directly toward nearest food."""

    def __init__(self):
        super().__init__(
            algorithm_id="greedy_food_seeker",
            parameters={
                "speed_multiplier": random.uniform(0.7, 1.3),
                "detection_range": random.uniform(0.5, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * self.parameters["speed_multiplier"], direction.y * self.parameters["speed_multiplier"]
        return 0, 0


@dataclass
class EnergyAwareFoodSeeker(BehaviorAlgorithm):
    """Seek food more aggressively when energy is low."""

    def __init__(self):
        super().__init__(
            algorithm_id="energy_aware_food_seeker",
            parameters={
                "urgency_threshold": random.uniform(0.3, 0.7),
                "calm_speed": random.uniform(0.3, 0.6),
                "urgent_speed": random.uniform(0.8, 1.2),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        energy_ratio = fish.energy / fish.max_energy
        nearest_food = self._find_nearest(fish, Food)

        if nearest_food:
            speed = self.parameters["urgent_speed"] if energy_ratio < self.parameters["urgency_threshold"] else self.parameters["calm_speed"]
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * speed, direction.y * speed
        return 0, 0


@dataclass
class OpportunisticFeeder(BehaviorAlgorithm):
    """Only pursue food if it's close enough."""

    def __init__(self):
        super().__init__(
            algorithm_id="opportunistic_feeder",
            parameters={
                "max_pursuit_distance": random.uniform(50, 200),
                "speed": random.uniform(0.6, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            if distance < self.parameters["max_pursuit_distance"]:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["speed"], direction.y * self.parameters["speed"]
        return 0, 0


@dataclass
class FoodQualityOptimizer(BehaviorAlgorithm):
    """Prefer high-value food types."""

    def __init__(self):
        super().__init__(
            algorithm_id="food_quality_optimizer",
            parameters={
                "quality_weight": random.uniform(0.5, 1.0),
                "distance_weight": random.uniform(0.3, 0.7),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        foods = fish.environment.get_agents_of_type(Food)
        best_food = None
        best_score = -float('inf')

        for food in foods:
            distance = (food.pos - fish.pos).length()
            quality = food.get_energy_value()
            score = quality * self.parameters["quality_weight"] - distance * self.parameters["distance_weight"]
            if score > best_score:
                best_score = score
                best_food = food

        if best_food:
            direction = (best_food.pos - fish.pos).normalize()
            return direction.x, direction.y
        return 0, 0


@dataclass
class AmbushFeeder(BehaviorAlgorithm):
    """Wait in one spot for food to come close."""

    def __init__(self):
        super().__init__(
            algorithm_id="ambush_feeder",
            parameters={
                "strike_distance": random.uniform(30, 80),
                "strike_speed": random.uniform(1.0, 1.5),
                "patience": random.uniform(0.5, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            if distance < self.parameters["strike_distance"]:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["strike_speed"], direction.y * self.parameters["strike_speed"]
        return 0, 0


@dataclass
class PatrolFeeder(BehaviorAlgorithm):
    """Patrol in a pattern looking for food."""

    def __init__(self):
        super().__init__(
            algorithm_id="patrol_feeder",
            parameters={
                "patrol_radius": random.uniform(50, 150),
                "patrol_speed": random.uniform(0.5, 1.0),
                "food_priority": random.uniform(0.6, 1.0),
            }
        )
        self.patrol_center = None
        self.patrol_angle = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        # Check for nearby food first
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 100:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * self.parameters["food_priority"], direction.y * self.parameters["food_priority"]

        # Otherwise patrol
        if self.patrol_center is None:
            self.patrol_center = fish.pos.copy()

        self.patrol_angle += 0.05
        target_x = self.patrol_center.x + math.cos(self.patrol_angle) * self.parameters["patrol_radius"]
        target_y = self.patrol_center.y + math.sin(self.patrol_angle) * self.parameters["patrol_radius"]
        direction = (Vector2(target_x, target_y) - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            return direction.x * self.parameters["patrol_speed"], direction.y * self.parameters["patrol_speed"]
        return 0, 0


@dataclass
class SurfaceSkimmer(BehaviorAlgorithm):
    """Stay near surface to catch falling food."""

    def __init__(self):
        super().__init__(
            algorithm_id="surface_skimmer",
            parameters={
                "preferred_depth": random.uniform(0.1, 0.3),  # 10-30% from top
                "horizontal_speed": random.uniform(0.5, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_HEIGHT
        from agents import Food

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]

        # Move toward target depth
        vy = (target_y - fish.pos.y) / 100  # Gentle vertical adjustment

        # Look for food while at surface
        nearest_food = self._find_nearest(fish, Food)
        vx = 0
        if nearest_food:
            vx = (nearest_food.pos.x - fish.pos.x) / 100
        else:
            vx = self.parameters["horizontal_speed"] if random.random() > 0.5 else -self.parameters["horizontal_speed"]

        return vx, vy


@dataclass
class BottomFeeder(BehaviorAlgorithm):
    """Stay near bottom to catch sinking food."""

    def __init__(self):
        super().__init__(
            algorithm_id="bottom_feeder",
            parameters={
                "preferred_depth": random.uniform(0.7, 0.9),  # 70-90% from top
                "search_speed": random.uniform(0.4, 0.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_HEIGHT
        from agents import Food

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]
        vy = (target_y - fish.pos.y) / 100

        nearest_food = self._find_nearest(fish, Food)
        vx = 0
        if nearest_food:
            vx = (nearest_food.pos.x - fish.pos.x) / 100
        else:
            vx = self.parameters["search_speed"] if random.random() > 0.5 else -self.parameters["search_speed"]

        return vx, vy


@dataclass
class ZigZagForager(BehaviorAlgorithm):
    """Move in zigzag pattern to maximize food discovery."""

    def __init__(self):
        super().__init__(
            algorithm_id="zigzag_forager",
            parameters={
                "zigzag_frequency": random.uniform(0.02, 0.08),
                "zigzag_amplitude": random.uniform(0.5, 1.2),
                "forward_speed": random.uniform(0.6, 1.0),
            }
        )
        self.zigzag_phase = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        # Check for nearby food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 80:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x, direction.y

        # Zigzag movement
        self.zigzag_phase += self.parameters["zigzag_frequency"]
        vx = self.parameters["forward_speed"]
        vy = math.sin(self.zigzag_phase) * self.parameters["zigzag_amplitude"]

        return vx, vy


@dataclass
class CircularHunter(BehaviorAlgorithm):
    """Circle around food before striking."""

    def __init__(self):
        super().__init__(
            algorithm_id="circular_hunter",
            parameters={
                "circle_radius": random.uniform(40, 100),
                "circle_speed": random.uniform(0.05, 0.15),
                "strike_threshold": random.uniform(0.3, 0.6),
            }
        )
        self.circle_angle = 0

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        nearest_food = self._find_nearest(fish, Food)
        if not nearest_food:
            return 0, 0

        distance = (nearest_food.pos - fish.pos).length()

        # Strike if close enough
        if distance < self.parameters["circle_radius"] * self.parameters["strike_threshold"]:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x, direction.y

        # Circle around food
        self.circle_angle += self.parameters["circle_speed"]
        target_x = nearest_food.pos.x + math.cos(self.circle_angle) * self.parameters["circle_radius"]
        target_y = nearest_food.pos.y + math.sin(self.circle_angle) * self.parameters["circle_radius"]
        direction = (Vector2(target_x, target_y) - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            return direction.x, direction.y
        return 0, 0


@dataclass
class FoodMemorySeeker(BehaviorAlgorithm):
    """Remember where food was found before."""

    def __init__(self):
        super().__init__(
            algorithm_id="food_memory_seeker",
            parameters={
                "memory_strength": random.uniform(0.5, 1.0),
                "exploration_rate": random.uniform(0.2, 0.5),
            }
        )
        self.food_memory_locations: List[Vector2] = []

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        # Look for current food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            # Remember this location
            if len(self.food_memory_locations) < 5:
                self.food_memory_locations.append(nearest_food.pos.copy())
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x, direction.y

        # No food visible, check memory
        if self.food_memory_locations and random.random() > self.parameters["exploration_rate"]:
            target = random.choice(self.food_memory_locations)
            direction = (target - fish.pos)
            if direction.length() > 0:
                direction = direction.normalize()
                return direction.x * self.parameters["memory_strength"], direction.y * self.parameters["memory_strength"]

        return 0, 0


@dataclass
class CooperativeForager(BehaviorAlgorithm):
    """Follow other fish to food sources."""

    def __init__(self):
        super().__init__(
            algorithm_id="cooperative_forager",
            parameters={
                "follow_strength": random.uniform(0.5, 0.9),
                "independence": random.uniform(0.2, 0.5),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food, Fish as FishClass

        # Check if any nearby fish are near food
        foods = fish.environment.get_agents_of_type(Food)
        fishes = fish.environment.get_agents_of_type(FishClass)

        for other_fish in fishes:
            if other_fish == fish:
                continue
            for food in foods:
                if (other_fish.pos - food.pos).length() < 50:
                    # Follow that fish!
                    direction = (other_fish.pos - fish.pos)
                    if direction.length() > 0:
                        direction = direction.normalize()
                        return direction.x * self.parameters["follow_strength"], direction.y * self.parameters["follow_strength"]

        return 0, 0


# ============================================================================
# PREDATOR AVOIDANCE ALGORITHMS (10 algorithms)
# ============================================================================

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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["panic_distance"]:
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["flee_speed"], direction.y * self.parameters["flee_speed"]
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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            if distance < self.parameters["awareness_range"]:
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["stealth_speed"], direction.y * self.parameters["stealth_speed"]
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
        from agents import Crab

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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < self.parameters["threat_range"]:
            vx = random.uniform(-1, 1) * self.parameters["randomness"] * self.parameters["evasion_speed"]
            vy = random.uniform(-1, 1) * self.parameters["randomness"] * self.parameters["evasion_speed"]
            return vx, vy
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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            return 0, self.parameters["escape_direction"] * self.parameters["escape_speed"]
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
        from agents import Crab, Fish as FishClass

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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            self.spiral_angle += self.parameters["spiral_rate"]
            escape_dir = (fish.pos - nearest_predator.pos).normalize()
            # Rotate the escape direction
            vx = escape_dir.x * math.cos(self.spiral_angle) - escape_dir.y * math.sin(self.spiral_angle)
            vy = escape_dir.x * math.sin(self.spiral_angle) + escape_dir.y * math.cos(self.spiral_angle)
            return vx, vy
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
        from agents import Crab
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            to_fish = (fish.pos - nearest_predator.pos)
            if to_fish.length() > 0:
                to_fish = to_fish.normalize()
                # Perpendicular vector
                perp_x = -to_fish.y * self.parameters["direction_preference"]
                perp_y = to_fish.x * self.parameters["direction_preference"]
                return perp_x * self.parameters["escape_speed"], perp_y * self.parameters["escape_speed"]
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
        from agents import Crab

        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            distance = (nearest_predator.pos - fish.pos).length()
            direction = (fish.pos - nearest_predator.pos)
            if direction.length() > 0:
                direction = direction.normalize()

                if distance < self.parameters["safe_distance"] * 0.7:
                    # Too close, flee
                    return direction.x * self.parameters["flee_speed"], direction.y * self.parameters["flee_speed"]
                elif distance > self.parameters["safe_distance"] * 1.3:
                    # Too far, can move closer
                    return -direction.x * self.parameters["approach_speed"], -direction.y * self.parameters["approach_speed"]
        return 0, 0


# ============================================================================
# SCHOOLING/SOCIAL ALGORITHMS (10 algorithms)
# ============================================================================

@dataclass
class TightScholer(BehaviorAlgorithm):
    """Stay very close to school members."""

    def __init__(self):
        super().__init__(
            algorithm_id="tight_schooler",
            parameters={
                "cohesion_strength": random.uniform(0.7, 1.2),
                "preferred_distance": random.uniform(20, 50),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            direction = (center - fish.pos)
            if direction.length() > 0:
                direction = direction.normalize()
                return direction.x * self.parameters["cohesion_strength"], direction.y * self.parameters["cohesion_strength"]
        return 0, 0


@dataclass
class LooseScholer(BehaviorAlgorithm):
    """Maintain loose association with school."""

    def __init__(self):
        super().__init__(
            algorithm_id="loose_schooler",
            parameters={
                "cohesion_strength": random.uniform(0.3, 0.6),
                "max_distance": random.uniform(100, 200),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            distance = (center - fish.pos).length()
            if distance > self.parameters["max_distance"]:
                direction = (center - fish.pos).normalize()
                return direction.x * self.parameters["cohesion_strength"], direction.y * self.parameters["cohesion_strength"]
        return 0, 0


@dataclass
class LeaderFollower(BehaviorAlgorithm):
    """Follow the fastest/strongest fish."""

    def __init__(self):
        super().__init__(
            algorithm_id="leader_follower",
            parameters={
                "follow_strength": random.uniform(0.6, 1.0),
                "max_follow_distance": random.uniform(80, 150),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            # Find "leader" (fish with most energy)
            leader = max(allies, key=lambda f: f.energy)
            distance = (leader.pos - fish.pos).length()
            if distance < self.parameters["max_follow_distance"]:
                direction = (leader.pos - fish.pos).normalize()
                return direction.x * self.parameters["follow_strength"], direction.y * self.parameters["follow_strength"]
        return 0, 0


@dataclass
class AlignmentMatcher(BehaviorAlgorithm):
    """Match velocity with nearby fish."""

    def __init__(self):
        super().__init__(
            algorithm_id="alignment_matcher",
            parameters={
                "alignment_strength": random.uniform(0.5, 1.0),
                "alignment_radius": random.uniform(60, 120),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass)
                 if f != fish and f.species == fish.species and (f.pos - fish.pos).length() < self.parameters["alignment_radius"]]

        if allies:
            avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
            if avg_vel.length() > 0:
                avg_vel = avg_vel.normalize()
                return avg_vel.x * self.parameters["alignment_strength"], avg_vel.y * self.parameters["alignment_strength"]
        return 0, 0


@dataclass
class SeparationSeeker(BehaviorAlgorithm):
    """Avoid crowding neighbors."""

    def __init__(self):
        super().__init__(
            algorithm_id="separation_seeker",
            parameters={
                "min_distance": random.uniform(30, 70),
                "separation_strength": random.uniform(0.5, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish]

        vx, vy = 0, 0
        for ally in allies:
            distance = (ally.pos - fish.pos).length()
            if 0 < distance < self.parameters["min_distance"]:
                direction = (fish.pos - ally.pos).normalize()
                strength = (self.parameters["min_distance"] - distance) / self.parameters["min_distance"]
                vx += direction.x * strength * self.parameters["separation_strength"]
                vy += direction.y * strength * self.parameters["separation_strength"]

        return vx, vy


@dataclass
class FrontRunner(BehaviorAlgorithm):
    """Lead the school from the front."""

    def __init__(self):
        super().__init__(
            algorithm_id="front_runner",
            parameters={
                "leadership_strength": random.uniform(0.7, 1.2),
                "independence": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        # Move in a consistent direction
        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            # Move away from center to lead
            direction = (fish.pos - center)
            if direction.length() > 0:
                direction = direction.normalize()
                return direction.x * self.parameters["leadership_strength"], direction.y * self.parameters["leadership_strength"]

        # If alone, just move forward
        return self.parameters["independence"], 0


@dataclass
class PerimeterGuard(BehaviorAlgorithm):
    """Stay on the outside of the school."""

    def __init__(self):
        super().__init__(
            algorithm_id="perimeter_guard",
            parameters={
                "orbit_radius": random.uniform(70, 130),
                "orbit_speed": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            to_center = (center - fish.pos)
            distance = to_center.length()

            if distance < self.parameters["orbit_radius"]:
                # Move away from center
                direction = -to_center.normalize()
                return direction.x * self.parameters["orbit_speed"], direction.y * self.parameters["orbit_speed"]
            elif distance > self.parameters["orbit_radius"] * 1.3:
                # Move toward center
                direction = to_center.normalize()
                return direction.x * self.parameters["orbit_speed"], direction.y * self.parameters["orbit_speed"]
        return 0, 0


@dataclass
class MirrorMover(BehaviorAlgorithm):
    """Mirror the movements of nearby fish."""

    def __init__(self):
        super().__init__(
            algorithm_id="mirror_mover",
            parameters={
                "mirror_strength": random.uniform(0.6, 1.0),
                "mirror_distance": random.uniform(50, 100),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass)
                 if f != fish and (f.pos - fish.pos).length() < self.parameters["mirror_distance"]]

        if allies:
            nearest = min(allies, key=lambda f: (f.pos - fish.pos).length())
            # Copy their velocity
            if nearest.vel.length() > 0:
                direction = nearest.vel.normalize()
                return direction.x * self.parameters["mirror_strength"], direction.y * self.parameters["mirror_strength"]
        return 0, 0


@dataclass
class BoidsBehavior(BehaviorAlgorithm):
    """Classic boids algorithm (separation, alignment, cohesion)."""

    def __init__(self):
        super().__init__(
            algorithm_id="boids_behavior",
            parameters={
                "separation_weight": random.uniform(0.3, 0.7),
                "alignment_weight": random.uniform(0.3, 0.7),
                "cohesion_weight": random.uniform(0.3, 0.7),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]

        if not allies:
            return 0, 0

        # Separation
        sep_x, sep_y = 0, 0
        for ally in allies:
            distance = (ally.pos - fish.pos).length()
            if 0 < distance < 50:
                direction = (fish.pos - ally.pos).normalize()
                sep_x += direction.x / distance
                sep_y += direction.y / distance

        # Alignment
        avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
        align_x, align_y = avg_vel.x, avg_vel.y

        # Cohesion
        center = sum((f.pos for f in allies), Vector2()) / len(allies)
        coh_dir = (center - fish.pos).normalize() if (center - fish.pos).length() > 0 else Vector2()

        # Combine
        vx = (sep_x * self.parameters["separation_weight"] +
              align_x * self.parameters["alignment_weight"] +
              coh_dir.x * self.parameters["cohesion_weight"])
        vy = (sep_y * self.parameters["separation_weight"] +
              align_y * self.parameters["alignment_weight"] +
              coh_dir.y * self.parameters["cohesion_weight"])

        # Normalize
        length = math.sqrt(vx*vx + vy*vy)
        if length > 0:
            return vx/length, vy/length
        return 0, 0


@dataclass
class DynamicScholer(BehaviorAlgorithm):
    """Switch between tight and loose schooling based on conditions."""

    def __init__(self):
        super().__init__(
            algorithm_id="dynamic_schooler",
            parameters={
                "danger_cohesion": random.uniform(0.8, 1.2),
                "calm_cohesion": random.uniform(0.3, 0.6),
                "danger_threshold": random.uniform(150, 250),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass, Crab

        # Check for danger
        predators = fish.environment.get_agents_of_type(Crab)
        in_danger = any((p.pos - fish.pos).length() < self.parameters["danger_threshold"] for p in predators)

        # Adjust cohesion based on danger
        cohesion = self.parameters["danger_cohesion"] if in_danger else self.parameters["calm_cohesion"]

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            direction = (center - fish.pos)
            if direction.length() > 0:
                direction = direction.normalize()
                return direction.x * cohesion, direction.y * cohesion
        return 0, 0


# ============================================================================
# ENERGY MANAGEMENT ALGORITHMS (8 algorithms)
# ============================================================================

@dataclass
class EnergyConserver(BehaviorAlgorithm):
    """Minimize movement to conserve energy."""

    def __init__(self):
        super().__init__(
            algorithm_id="energy_conserver",
            parameters={
                "activity_threshold": random.uniform(0.4, 0.7),
                "rest_speed": random.uniform(0.1, 0.3),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < self.parameters["activity_threshold"]:
            # Rest mode
            return 0, 0
        return 0, 0


@dataclass
class BurstSwimmer(BehaviorAlgorithm):
    """Alternate between bursts of activity and rest."""

    def __init__(self):
        super().__init__(
            algorithm_id="burst_swimmer",
            parameters={
                "burst_duration": random.uniform(30, 90),
                "rest_duration": random.uniform(60, 120),
                "burst_speed": random.uniform(1.2, 1.6),
            }
        )
        self.cycle_timer = 0
        self.is_bursting = True

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        self.cycle_timer += 1

        if self.is_bursting and self.cycle_timer > self.parameters["burst_duration"]:
            self.is_bursting = False
            self.cycle_timer = 0
        elif not self.is_bursting and self.cycle_timer > self.parameters["rest_duration"]:
            self.is_bursting = True
            self.cycle_timer = 0

        if self.is_bursting:
            # Move forward during burst
            return self.parameters["burst_speed"], 0
        return 0, 0


@dataclass
class OpportunisticRester(BehaviorAlgorithm):
    """Rest when no food or threats nearby."""

    def __init__(self):
        super().__init__(
            algorithm_id="opportunistic_rester",
            parameters={
                "safe_radius": random.uniform(100, 200),
                "active_speed": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food, Crab

        # Check for nearby stimuli
        foods = fish.environment.get_agents_of_type(Food)
        predators = fish.environment.get_agents_of_type(Crab)

        has_nearby_food = any((f.pos - fish.pos).length() < self.parameters["safe_radius"] for f in foods)
        has_nearby_threat = any((p.pos - fish.pos).length() < self.parameters["safe_radius"] for p in predators)

        if has_nearby_food or has_nearby_threat:
            return self.parameters["active_speed"], 0
        return 0, 0


@dataclass
class EnergyBalancer(BehaviorAlgorithm):
    """Balance energy expenditure with reserves."""

    def __init__(self):
        super().__init__(
            algorithm_id="energy_balancer",
            parameters={
                "min_energy_ratio": random.uniform(0.3, 0.5),
                "max_energy_ratio": random.uniform(0.7, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy

        # Scale activity by energy level
        if energy_ratio < self.parameters["min_energy_ratio"]:
            activity = 0.2
        elif energy_ratio > self.parameters["max_energy_ratio"]:
            activity = 1.0
        else:
            # Linear interpolation
            activity = 0.2 + 0.8 * ((energy_ratio - self.parameters["min_energy_ratio"]) /
                                   (self.parameters["max_energy_ratio"] - self.parameters["min_energy_ratio"]))

        return activity, 0


@dataclass
class SustainableCruiser(BehaviorAlgorithm):
    """Maintain steady, sustainable pace."""

    def __init__(self):
        super().__init__(
            algorithm_id="sustainable_cruiser",
            parameters={
                "cruise_speed": random.uniform(0.4, 0.7),
                "consistency": random.uniform(0.7, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Just maintain steady pace
        return self.parameters["cruise_speed"] * self.parameters["consistency"], 0


@dataclass
class StarvationPreventer(BehaviorAlgorithm):
    """Prioritize food when energy gets low."""

    def __init__(self):
        super().__init__(
            algorithm_id="starvation_preventer",
            parameters={
                "critical_threshold": random.uniform(0.2, 0.4),
                "urgency_multiplier": random.uniform(1.3, 1.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Food

        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < self.parameters["critical_threshold"]:
            # Emergency food seeking
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["urgency_multiplier"], direction.y * self.parameters["urgency_multiplier"]
        return 0, 0


@dataclass
class MetabolicOptimizer(BehaviorAlgorithm):
    """Adjust activity based on metabolic efficiency."""

    def __init__(self):
        super().__init__(
            algorithm_id="metabolic_optimizer",
            parameters={
                "efficiency_threshold": random.uniform(0.5, 0.8),
                "low_efficiency_speed": random.uniform(0.2, 0.4),
                "high_efficiency_speed": random.uniform(0.7, 1.1),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Use genome metabolism as efficiency indicator
        efficiency = 1.0 / fish.genome.metabolism_rate if fish.genome.metabolism_rate > 0 else 1.0

        if efficiency > self.parameters["efficiency_threshold"]:
            speed = self.parameters["high_efficiency_speed"]
        else:
            speed = self.parameters["low_efficiency_speed"]

        return speed, 0


@dataclass
class AdaptivePacer(BehaviorAlgorithm):
    """Adapt speed based on current energy and environment."""

    def __init__(self):
        super().__init__(
            algorithm_id="adaptive_pacer",
            parameters={
                "base_speed": random.uniform(0.5, 0.8),
                "energy_influence": random.uniform(0.3, 0.7),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        speed = self.parameters["base_speed"] * (1 + (energy_ratio - 0.5) * self.parameters["energy_influence"])
        return speed, 0


# ============================================================================
# TERRITORY/EXPLORATION ALGORITHMS (8 algorithms)
# ============================================================================

@dataclass
class TerritorialDefender(BehaviorAlgorithm):
    """Defend a territory from other fish."""

    def __init__(self):
        super().__init__(
            algorithm_id="territorial_defender",
            parameters={
                "territory_radius": random.uniform(80, 150),
                "aggression": random.uniform(0.5, 1.0),
            }
        )
        self.territory_center = None

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from agents import Fish as FishClass

        if self.territory_center is None:
            self.territory_center = fish.pos.copy()

        # Chase away intruders
        intruders = [f for f in fish.environment.get_agents_of_type(FishClass)
                    if f != fish and (f.pos - self.territory_center).length() < self.parameters["territory_radius"]]

        if intruders:
            nearest = min(intruders, key=lambda f: (f.pos - fish.pos).length())
            direction = (nearest.pos - fish.pos).normalize()
            return direction.x * self.parameters["aggression"], direction.y * self.parameters["aggression"]

        # Return to territory center
        direction = (self.territory_center - fish.pos)
        if direction.length() > self.parameters["territory_radius"]:
            direction = direction.normalize()
            return direction.x * 0.5, direction.y * 0.5

        return 0, 0


@dataclass
class RandomExplorer(BehaviorAlgorithm):
    """Explore randomly, covering new ground."""

    def __init__(self):
        super().__init__(
            algorithm_id="random_explorer",
            parameters={
                "change_frequency": random.uniform(0.02, 0.08),
                "exploration_speed": random.uniform(0.5, 0.9),
            }
        )
        self.current_direction = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        if random.random() < self.parameters["change_frequency"]:
            self.current_direction = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
            if self.current_direction.length() > 0:
                self.current_direction = self.current_direction.normalize()

        return self.current_direction.x * self.parameters["exploration_speed"], self.current_direction.y * self.parameters["exploration_speed"]


@dataclass
class WallFollower(BehaviorAlgorithm):
    """Follow along tank walls."""

    def __init__(self):
        super().__init__(
            algorithm_id="wall_follower",
            parameters={
                "wall_distance": random.uniform(20, 60),
                "follow_speed": random.uniform(0.5, 0.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # Find nearest wall
        dist_to_left = fish.pos.x
        dist_to_right = SCREEN_WIDTH - fish.pos.x
        dist_to_top = fish.pos.y
        dist_to_bottom = SCREEN_HEIGHT - fish.pos.y

        min_dist = min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)

        # Move parallel to nearest wall
        if min_dist == dist_to_left or min_dist == dist_to_right:
            return 0, self.parameters["follow_speed"]
        else:
            return self.parameters["follow_speed"], 0


@dataclass
class CornerSeeker(BehaviorAlgorithm):
    """Prefer staying in corners."""

    def __init__(self):
        super().__init__(
            algorithm_id="corner_seeker",
            parameters={
                "preferred_corner": random.choice(['top_left', 'top_right', 'bottom_left', 'bottom_right']),
                "approach_speed": random.uniform(0.4, 0.7),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # Determine corner position
        corners = {
            'top_left': Vector2(50, 50),
            'top_right': Vector2(SCREEN_WIDTH - 50, 50),
            'bottom_left': Vector2(50, SCREEN_HEIGHT - 50),
            'bottom_right': Vector2(SCREEN_WIDTH - 50, SCREEN_HEIGHT - 50),
        }

        target = corners[self.parameters["preferred_corner"]]
        direction = (target - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            return direction.x * self.parameters["approach_speed"], direction.y * self.parameters["approach_speed"]
        return 0, 0


@dataclass
class CenterHugger(BehaviorAlgorithm):
    """Stay near the center of the tank."""

    def __init__(self):
        super().__init__(
            algorithm_id="center_hugger",
            parameters={
                "orbit_radius": random.uniform(50, 120),
                "return_strength": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        distance = (center - fish.pos).length()

        if distance > self.parameters["orbit_radius"]:
            direction = (center - fish.pos).normalize()
            return direction.x * self.parameters["return_strength"], direction.y * self.parameters["return_strength"]
        return 0, 0


@dataclass
class RoutePatroller(BehaviorAlgorithm):
    """Patrol between specific waypoints."""

    def __init__(self):
        super().__init__(
            algorithm_id="route_patroller",
            parameters={
                "patrol_speed": random.uniform(0.5, 0.8),
                "waypoint_threshold": random.uniform(30, 60),
            }
        )
        self.waypoints: List[Vector2] = []
        self.current_waypoint_idx = 0
        self.initialized = False

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        if not self.initialized:
            # Create random waypoints
            num_waypoints = random.randint(3, 6)
            for _ in range(num_waypoints):
                self.waypoints.append(Vector2(random.uniform(50, SCREEN_WIDTH - 50),
                                            random.uniform(50, SCREEN_HEIGHT - 50)))
            self.initialized = True

        if not self.waypoints:
            return 0, 0

        target = self.waypoints[self.current_waypoint_idx]
        distance = (target - fish.pos).length()

        if distance < self.parameters["waypoint_threshold"]:
            self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
            target = self.waypoints[self.current_waypoint_idx]

        direction = (target - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            return direction.x * self.parameters["patrol_speed"], direction.y * self.parameters["patrol_speed"]
        return 0, 0


@dataclass
class BoundaryExplorer(BehaviorAlgorithm):
    """Explore edges and boundaries."""

    def __init__(self):
        super().__init__(
            algorithm_id="boundary_explorer",
            parameters={
                "edge_preference": random.uniform(0.6, 1.0),
                "exploration_speed": random.uniform(0.5, 0.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # Move toward edges
        center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        direction = (fish.pos - center)
        if direction.length() > 0:
            direction = direction.normalize()
            return direction.x * self.parameters["exploration_speed"] * self.parameters["edge_preference"], \
                   direction.y * self.parameters["exploration_speed"] * self.parameters["edge_preference"]
        return 0, 0


@dataclass
class NomadicWanderer(BehaviorAlgorithm):
    """Wander continuously without a home base."""

    def __init__(self):
        super().__init__(
            algorithm_id="nomadic_wanderer",
            parameters={
                "wander_strength": random.uniform(0.5, 0.9),
                "direction_change_rate": random.uniform(0.01, 0.05),
            }
        )
        self.wander_angle = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Gradually change direction
        self.wander_angle += random.gauss(0, self.parameters["direction_change_rate"])

        vx = math.cos(self.wander_angle) * self.parameters["wander_strength"]
        vy = math.sin(self.wander_angle) * self.parameters["wander_strength"]

        return vx, vy


# ============================================================================
# HELPER METHODS (shared across algorithms)
# ============================================================================

def _find_nearest(self, fish: 'Fish', agent_type) -> Optional[Any]:
    """Find nearest agent of given type."""
    agents = fish.environment.get_agents_of_type(agent_type)
    if not agents:
        return None
    return min(agents, key=lambda a: (a.pos - fish.pos).length())


# Inject helper method into base class
BehaviorAlgorithm._find_nearest = _find_nearest


# ============================================================================
# ALGORITHM REGISTRY
# ============================================================================

# All available algorithms
ALL_ALGORITHMS = [
    # Food seeking
    GreedyFoodSeeker,
    EnergyAwareFoodSeeker,
    OpportunisticFeeder,
    FoodQualityOptimizer,
    AmbushFeeder,
    PatrolFeeder,
    SurfaceSkimmer,
    BottomFeeder,
    ZigZagForager,
    CircularHunter,
    FoodMemorySeeker,
    CooperativeForager,

    # Predator avoidance
    PanicFlee,
    StealthyAvoider,
    FreezeResponse,
    ErraticEvader,
    VerticalEscaper,
    GroupDefender,
    SpiralEscape,
    BorderHugger,
    PerpendicularEscape,
    DistanceKeeper,

    # Schooling/social
    TightScholer,
    LooseScholer,
    LeaderFollower,
    AlignmentMatcher,
    SeparationSeeker,
    FrontRunner,
    PerimeterGuard,
    MirrorMover,
    BoidsBehavior,
    DynamicScholer,

    # Energy management
    EnergyConserver,
    BurstSwimmer,
    OpportunisticRester,
    EnergyBalancer,
    SustainableCruiser,
    StarvationPreventer,
    MetabolicOptimizer,
    AdaptivePacer,

    # Territory/exploration
    TerritorialDefender,
    RandomExplorer,
    WallFollower,
    CornerSeeker,
    CenterHugger,
    RoutePatroller,
    BoundaryExplorer,
    NomadicWanderer,
]


def get_random_algorithm() -> BehaviorAlgorithm:
    """Get a random behavior algorithm instance."""
    algorithm_class = random.choice(ALL_ALGORITHMS)
    return algorithm_class.random_instance()


def get_algorithm_by_id(algorithm_id: str) -> Optional[BehaviorAlgorithm]:
    """Get algorithm instance by ID."""
    for algo_class in ALL_ALGORITHMS:
        instance = algo_class.random_instance()
        if instance.algorithm_id == algorithm_id:
            return instance
    return None


def inherit_algorithm_with_mutation(parent_algorithm: BehaviorAlgorithm,
                                   mutation_rate: float = 0.15,
                                   mutation_strength: float = 0.2) -> BehaviorAlgorithm:
    """Create offspring algorithm by copying parent and mutating parameters.

    Args:
        parent_algorithm: Parent's behavior algorithm
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations

    Returns:
        New algorithm instance with mutated parameters
    """
    # Create new instance of same algorithm type
    offspring = parent_algorithm.__class__()

    # Copy parent parameters
    offspring.parameters = parent_algorithm.parameters.copy()

    # Mutate
    offspring.mutate_parameters(mutation_rate, mutation_strength)

    return offspring
