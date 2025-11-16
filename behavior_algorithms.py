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


ALGORITHM_PARAMETER_BOUNDS = {
    'adaptive_pacer': {
        'base_speed': (0.5, 0.8),
        'energy_influence': (0.3, 0.7),
    },
    'alignment_matcher': {
        'alignment_radius': (60.0, 120.0),
        'alignment_strength': (0.5, 1.0),
    },
    'ambush_feeder': {
        'patience': (0.5, 1.0),
        'strike_distance': (30.0, 80.0),
        'strike_speed': (1.0, 1.5),
    },
    'boids_behavior': {
        'alignment_weight': (0.3, 0.7),
        'cohesion_weight': (0.3, 0.7),
        'separation_weight': (0.3, 0.7),
    },
    'border_hugger': {
        'hug_speed': (0.7, 1.1),
    },
    'bottom_feeder': {
        'preferred_depth': (0.7, 0.9),
        'search_speed': (0.4, 0.8),
    },
    'boundary_explorer': {
        'edge_preference': (0.6, 1.0),
        'exploration_speed': (0.5, 0.8),
    },
    'burst_swimmer': {
        'burst_duration': (30.0, 90.0),
        'burst_speed': (1.2, 1.6),
        'rest_duration': (60.0, 120.0),
    },
    'center_hugger': {
        'orbit_radius': (50.0, 120.0),
        'return_strength': (0.5, 0.9),
    },
    'circular_hunter': {
        'circle_radius': (40.0, 100.0),
        'circle_speed': (0.05, 0.15),
        'strike_threshold': (0.3, 0.6),
    },
    'cooperative_forager': {
        'follow_strength': (0.5, 0.9),
        'independence': (0.2, 0.5),
    },
    'corner_seeker': {
        'approach_speed': (0.4, 0.7),
    },
    'distance_keeper': {
        'approach_speed': (0.3, 0.6),
        'flee_speed': (0.8, 1.2),
        'safe_distance': (120.0, 200.0),
    },
    'dynamic_schooler': {
        'calm_cohesion': (0.3, 0.6),
        'danger_cohesion': (0.8, 1.2),
        'danger_threshold': (150.0, 250.0),
    },
    'energy_aware_food_seeker': {
        'calm_speed': (0.3, 0.6),
        'urgency_threshold': (0.3, 0.7),
        'urgent_speed': (0.8, 1.2),
    },
    'energy_balancer': {
        'max_energy_ratio': (0.7, 0.9),
        'min_energy_ratio': (0.3, 0.5),
    },
    'energy_conserver': {
        'activity_threshold': (0.4, 0.7),
        'rest_speed': (0.1, 0.3),
    },
    'erratic_evader': {
        'evasion_speed': (0.8, 1.3),
        'randomness': (0.5, 1.0),
        'threat_range': (100.0, 180.0),
    },
    'food_memory_seeker': {
        'exploration_rate': (0.2, 0.5),
        'memory_strength': (0.5, 1.0),
    },
    'food_quality_optimizer': {
        'distance_weight': (0.3, 0.7),
        'quality_weight': (0.5, 1.0),
    },
    'freeze_response': {
        'freeze_distance': (80.0, 150.0),
        'resume_distance': (200.0, 300.0),
    },
    'front_runner': {
        'independence': (0.5, 0.9),
        'leadership_strength': (0.7, 1.2),
    },
    'greedy_food_seeker': {
        'detection_range': (0.5, 1.0),
        'speed_multiplier': (0.7, 1.3),
    },
    'group_defender': {
        'group_strength': (0.6, 1.0),
        'min_group_distance': (30.0, 80.0),
    },
    'leader_follower': {
        'follow_strength': (0.6, 1.0),
        'max_follow_distance': (80.0, 150.0),
    },
    'loose_schooler': {
        'cohesion_strength': (0.3, 0.6),
        'max_distance': (100.0, 200.0),
    },
    'metabolic_optimizer': {
        'efficiency_threshold': (0.5, 0.8),
        'high_efficiency_speed': (0.7, 1.1),
        'low_efficiency_speed': (0.2, 0.4),
    },
    'mirror_mover': {
        'mirror_distance': (50.0, 100.0),
        'mirror_strength': (0.6, 1.0),
    },
    'nomadic_wanderer': {
        'direction_change_rate': (0.01, 0.05),
        'wander_strength': (0.5, 0.9),
    },
    'opportunistic_feeder': {
        'max_pursuit_distance': (50.0, 200.0),
        'speed': (0.6, 1.0),
    },
    'opportunistic_rester': {
        'active_speed': (0.5, 0.9),
        'safe_radius': (100.0, 200.0),
    },
    'panic_flee': {
        'flee_speed': (1.2, 1.8),
        'panic_distance': (100.0, 200.0),
    },
    'patrol_feeder': {
        'food_priority': (0.6, 1.0),
        'patrol_radius': (50.0, 150.0),
        'patrol_speed': (0.5, 1.0),
    },
    'perimeter_guard': {
        'orbit_radius': (70.0, 130.0),
        'orbit_speed': (0.5, 0.9),
    },
    'perpendicular_escape': {
        'escape_speed': (1.0, 1.4),
    },
    'random_explorer': {
        'change_frequency': (0.02, 0.08),
        'exploration_speed': (0.5, 0.9),
    },
    'route_patroller': {
        'patrol_speed': (0.5, 0.8),
        'waypoint_threshold': (30.0, 60.0),
    },
    'separation_seeker': {
        'min_distance': (30.0, 70.0),
        'separation_strength': (0.5, 1.0),
    },
    'spiral_escape': {
        'spiral_radius': (20.0, 60.0),
        'spiral_rate': (0.1, 0.3),
    },
    'starvation_preventer': {
        'critical_threshold': (0.2, 0.4),
        'urgency_multiplier': (1.3, 1.8),
    },
    'stealthy_avoider': {
        'awareness_range': (150.0, 250.0),
        'stealth_speed': (0.3, 0.6),
    },
    'surface_skimmer': {
        'horizontal_speed': (0.5, 1.0),
        'preferred_depth': (0.1, 0.3),
    },
    'sustainable_cruiser': {
        'consistency': (0.7, 1.0),
        'cruise_speed': (0.4, 0.7),
    },
    'territorial_defender': {
        'aggression': (0.5, 1.0),
        'territory_radius': (80.0, 150.0),
    },
    'tight_schooler': {
        'cohesion_strength': (0.7, 1.2),
        'preferred_distance': (20.0, 50.0),
    },
    'vertical_escaper': {
        'escape_speed': (1.0, 1.5),
    },
    'wall_follower': {
        'follow_speed': (0.5, 0.8),
        'wall_distance': (20.0, 60.0),
    },
    'zigzag_forager': {
        'forward_speed': (0.6, 1.0),
        'zigzag_amplitude': (0.5, 1.2),
        'zigzag_frequency': (0.02, 0.08),
    },
}


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
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.parameter_bounds:
            bounds = ALGORITHM_PARAMETER_BOUNDS.get(self.algorithm_id)
            if bounds:
                self.parameter_bounds = {key: (float(low), float(high)) for key, (low, high) in bounds.items()}

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
        for key, current_value in list(self.parameters.items()):
            # Skip non-numeric parameters (they shouldn't be mutated)
            if not isinstance(current_value, (int, float)):
                continue

            if random.random() >= mutation_rate:
                continue

            bounds = self.parameter_bounds.get(key)
            if bounds:
                lower, upper = bounds
                span = upper - lower
                if span <= 0:
                    span = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, mutation_strength) * span
                mutated = max(lower, min(upper, mutated))
            else:
                scale = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, mutation_strength) * scale
                mutated = max(0.0, mutated)

            self.parameters[key] = mutated

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
        from agents import Food, Crab

        # Check for predators first - don't chase food if predator is too close
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            # Flee from predator instead
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # Consider energy efficiency - don't chase food that's too far if energy is medium
            energy_ratio = fish.energy / fish.max_energy
            max_chase_distance = 150 + (energy_ratio * 200)  # Chase further when high energy

            if distance < max_chase_distance:
                direction = (nearest_food.pos - fish.pos).normalize()
                # Speed up when closer to food
                speed_boost = 1.0 + (1.0 - min(distance / 100, 1.0)) * 0.5
                return direction.x * self.parameters["speed_multiplier"] * speed_boost, direction.y * self.parameters["speed_multiplier"] * speed_boost
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
        from agents import Food, Crab

        energy_ratio = fish.energy / fish.max_energy

        # Check for predators - even urgent fish should avoid immediate danger
        nearest_predator = self._find_nearest(fish, Crab)
        predator_nearby = nearest_predator and (nearest_predator.pos - fish.pos).length() < 100

        # In critical energy state, take calculated risks
        if energy_ratio < 0.15:
            # Desperate - must eat even with some predator risk
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                # If predator is blocking food, try to path around it
                if predator_nearby:
                    predator_to_food = (nearest_food.pos - nearest_predator.pos).length()
                    if predator_to_food < 80:  # Predator is guarding the food
                        # Try perpendicular approach
                        to_food = (nearest_food.pos - fish.pos).normalize()
                        perp_x, perp_y = -to_food.y, to_food.x
                        return perp_x * 0.8, perp_y * 0.8
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["urgent_speed"], direction.y * self.parameters["urgent_speed"]

        # Flee if predator too close
        if predator_nearby:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            # Graduated urgency based on energy level
            if energy_ratio < self.parameters["urgency_threshold"]:
                speed = self.parameters["urgent_speed"]
            else:
                # Scale speed based on energy - conserve when high energy
                speed = self.parameters["calm_speed"] + (1.0 - energy_ratio) * 0.3

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
        from agents import Food, Crab

        # Check predators first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 90:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.4, direction.y * 1.4

        foods = fish.environment.get_agents_of_type(Food)
        best_food = None
        best_score = -float('inf')

        energy_ratio = fish.energy / fish.max_energy

        for food in foods:
            distance = (food.pos - fish.pos).length()
            quality = food.get_energy_value()

            # Check if predator is near this food (danger score)
            danger_score = 0
            if nearest_predator:
                predator_food_dist = (nearest_predator.pos - food.pos).length()
                if predator_food_dist < 100:
                    danger_score = 100 - predator_food_dist  # Higher danger when predator is closer to food

            # Calculate value: high quality, close distance, low danger
            # When desperate (low energy), ignore danger more
            danger_weight = 0.3 if energy_ratio < 0.3 else 0.8
            score = (quality * self.parameters["quality_weight"]
                    - distance * self.parameters["distance_weight"]
                    - danger_score * danger_weight)

            if score > best_score:
                best_score = score
                best_food = food

        if best_food and best_score > -50:  # Don't pursue if score is terrible
            distance_to_food = (best_food.pos - fish.pos).length()
            direction = (best_food.pos - fish.pos).normalize()
            # Move faster when food is close
            speed = 0.8 + min(50 / max(distance_to_food, 1), 0.6)
            return direction.x * speed, direction.y * speed
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
        from agents import Food, Crab

        # Predator check
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 110:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest(fish, Food)
        if not nearest_food:
            return 0, 0

        distance = (nearest_food.pos - fish.pos).length()

        # If food is moving (has velocity), predict its position
        food_future_pos = nearest_food.pos
        if hasattr(nearest_food, 'vel') and nearest_food.vel.length() > 0:
            # Predict food position 10 frames ahead
            food_future_pos = nearest_food.pos + nearest_food.vel * 10

        # Strike if close enough and angle is good
        if distance < self.parameters["circle_radius"] * self.parameters["strike_threshold"]:
            direction = (food_future_pos - fish.pos).normalize()
            # Fast strike
            return direction.x * 1.5, direction.y * 1.5

        # Tighten circle as we get closer
        effective_radius = self.parameters["circle_radius"] * (distance / 150)
        effective_radius = max(effective_radius, self.parameters["circle_radius"] * 0.5)

        # Circle around food with varying speed (faster when farther)
        circle_speed = self.parameters["circle_speed"] * (1 + distance / 200)
        self.circle_angle += circle_speed

        target_x = nearest_food.pos.x + math.cos(self.circle_angle) * effective_radius
        target_y = nearest_food.pos.y + math.sin(self.circle_angle) * effective_radius
        direction = (Vector2(target_x, target_y) - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            # Move faster when adjusting position
            speed = 0.8 + min(direction.length() / 100, 0.5)
            return direction.x * speed, direction.y * speed
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
        from agents import Food, Fish as FishClass, Crab

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 95:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.3, direction.y * 1.3

        # Look for food directly first
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 80:
            # Food is close, go for it directly
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 1.1, direction.y * 1.1

        # Check if any nearby fish are near food (social learning)
        foods = fish.environment.get_agents_of_type(Food)
        fishes = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish]

        best_target = None
        best_score = 0

        for other_fish in fishes:
            fish_dist = (other_fish.pos - fish.pos).length()
            if fish_dist > 200:  # Too far to follow
                continue

            # Check if this fish is near food or moving toward food
            for food in foods:
                food_dist = (other_fish.pos - food.pos).length()
                if food_dist < 80:
                    # Score based on how close the other fish is to food
                    # and how close we are to that fish
                    score = (100 - food_dist) * (200 - fish_dist) / 100

                    # Bonus if fish is moving toward the food
                    if hasattr(other_fish, 'vel') and other_fish.vel.length() > 0:
                        to_food = (food.pos - other_fish.pos).normalize()
                        vel_dir = other_fish.vel.normalize()
                        alignment = to_food.dot(vel_dir)
                        if alignment > 0.5:  # Fish is moving toward food
                            score *= 1.5

                    if score > best_score:
                        best_score = score
                        best_target = other_fish.pos

        if best_target:
            direction = (best_target - fish.pos)
            if direction.length() > 0:
                direction = direction.normalize()
                # Follow with varying intensity
                intensity = min(best_score / 100, 1.0)
                return direction.x * self.parameters["follow_strength"] * intensity, \
                       direction.y * self.parameters["follow_strength"] * intensity

        # No one to follow, explore independently
        if random.random() < self.parameters["independence"]:
            return random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)

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
        from agents import Crab, Fish as FishClass
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

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
        from agents import Crab, Food

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
        from agents import Fish as FishClass, Crab, Food

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]

        # Check for predators - school tightens when threatened
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = nearest_predator and (nearest_predator.pos - fish.pos).length() or float('inf')
        in_danger = predator_distance < 200

        # Check for food opportunities
        nearest_food = self._find_nearest(fish, Food)
        food_distance = nearest_food and (nearest_food.pos - fish.pos).length() or float('inf')
        food_nearby = food_distance < 100

        if not allies:
            # Alone - seek food or flee
            if in_danger and predator_distance < 150:
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * 1.3, direction.y * 1.3
            elif food_nearby:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * 0.7, direction.y * 0.7
            return 0, 0

        # Filter to nearby allies for efficiency
        nearby_allies = [f for f in allies if (f.pos - fish.pos).length() < 150]
        if not nearby_allies:
            nearby_allies = allies[:5]  # Use closest 5 if none nearby

        # Separation - avoid crowding
        sep_x, sep_y = 0, 0
        separation_distance = 40 if in_danger else 50  # Tighter when threatened
        for ally in nearby_allies:
            distance = (ally.pos - fish.pos).length()
            if 0 < distance < separation_distance:
                direction = (fish.pos - ally.pos).normalize()
                # Stronger separation when very close
                strength = (separation_distance - distance) / separation_distance
                sep_x += direction.x * strength / max(distance, 1)
                sep_y += direction.y * strength / max(distance, 1)

        # Alignment - match velocity
        avg_vel = sum((f.vel for f in nearby_allies), Vector2()) / len(nearby_allies)
        if avg_vel.length() > 0:
            avg_vel = avg_vel.normalize()
        align_x, align_y = avg_vel.x, avg_vel.y

        # Cohesion - move toward center
        center = sum((f.pos for f in nearby_allies), Vector2()) / len(nearby_allies)
        coh_dir = (center - fish.pos)
        if coh_dir.length() > 0:
            coh_dir = coh_dir.normalize()
        else:
            coh_dir = Vector2()

        # Dynamic weight adjustment based on context
        sep_weight = self.parameters["separation_weight"]
        align_weight = self.parameters["alignment_weight"]
        coh_weight = self.parameters["cohesion_weight"]

        if in_danger:
            # When threatened: increase cohesion and alignment (school tightens)
            coh_weight *= 1.8
            align_weight *= 1.5
            sep_weight *= 0.6
        elif food_nearby:
            # When food nearby: increase separation (compete for food)
            sep_weight *= 1.4
            coh_weight *= 0.7

        # Combine forces
        vx = (sep_x * sep_weight +
              align_x * align_weight +
              coh_dir.x * coh_weight)
        vy = (sep_y * sep_weight +
              align_y * align_weight +
              coh_dir.y * coh_weight)

        # Add predator avoidance
        if in_danger and predator_distance < 150:
            avoid_dir = (fish.pos - nearest_predator.pos).normalize()
            threat_strength = (150 - predator_distance) / 150
            vx += avoid_dir.x * threat_strength * 2.0
            vy += avoid_dir.y * threat_strength * 2.0

        # Add food attraction for whole school
        if food_nearby and food_distance < 80:
            food_dir = (nearest_food.pos - fish.pos).normalize()
            vx += food_dir.x * 0.5
            vy += food_dir.y * 0.5

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
        from agents import Fish as FishClass, Crab, Food

        # Check for danger with graded threat levels
        predators = fish.environment.get_agents_of_type(Crab)
        nearest_predator = self._find_nearest(fish, Crab)

        # Calculate threat level (0 = no threat, 1 = extreme threat)
        threat_level = 0
        if nearest_predator:
            pred_distance = (nearest_predator.pos - fish.pos).length()
            if pred_distance < self.parameters["danger_threshold"]:
                threat_level = 1.0 - (pred_distance / self.parameters["danger_threshold"])

        # Check for food opportunities
        nearest_food = self._find_nearest(fish, Food)
        food_opportunity = 0
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            if food_distance < 120:
                food_opportunity = 1.0 - (food_distance / 120)

        # Check energy state
        energy_ratio = fish.energy / fish.max_energy

        # Dynamic cohesion based on multiple factors
        if threat_level > 0.5:
            # High threat - tight schooling
            cohesion = self.parameters["danger_cohesion"]
        elif energy_ratio < 0.4 and food_opportunity > 0.3:
            # Hungry with food nearby - break formation to compete
            cohesion = self.parameters["calm_cohesion"] * 0.5
        elif energy_ratio > 0.8:
            # Well-fed and safe - loose exploration
            cohesion = self.parameters["calm_cohesion"] * 0.7
        else:
            # Normal conditions - moderate cohesion
            cohesion = self.parameters["calm_cohesion"]

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish and f.species == fish.species]
        if allies:
            # Move toward school center
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            direction = (center - fish.pos)

            vx, vy = 0, 0
            if direction.length() > 0:
                direction = direction.normalize()
                vx = direction.x * cohesion
                vy = direction.y * cohesion

            # Add threat response
            if threat_level > 0.3 and nearest_predator:
                avoid_dir = (fish.pos - nearest_predator.pos).normalize()
                vx += avoid_dir.x * threat_level * 1.5
                vy += avoid_dir.y * threat_level * 1.5

            # Add food seeking when safe and hungry
            if threat_level < 0.2 and energy_ratio < 0.6 and nearest_food:
                food_dir = (nearest_food.pos - fish.pos).normalize()
                hunger = 1.0 - energy_ratio
                vx += food_dir.x * hunger * 0.7
                vy += food_dir.y * hunger * 0.7

            # Normalize
            length = math.sqrt(vx*vx + vy*vy)
            if length > 0:
                return vx/length, vy/length

        # No allies - go solo
        if threat_level > 0.5 and nearest_predator:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2
        elif energy_ratio < 0.5 and nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 0.8, direction.y * 0.8

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
        from agents import Food, Crab

        energy_ratio = fish.energy / fish.max_energy

        # Check for immediate threats
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 100:
            # Must flee even if conserving energy
            direction = (fish.pos - nearest_predator.pos).normalize()
            # Slower flee when low energy (realistic)
            flee_speed = 0.8 + energy_ratio * 0.5
            return direction.x * flee_speed, direction.y * flee_speed

        # Only pursue very close food when in conservation mode
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            # Only move for food if it's very close or energy is critical
            if food_distance < 40 or energy_ratio < 0.25:
                direction = (nearest_food.pos - fish.pos).normalize()
                # Slow approach to conserve energy
                return direction.x * self.parameters["rest_speed"], direction.y * self.parameters["rest_speed"]

        # Rest mode - minimal movement
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
        from agents import Food, Crab

        energy_ratio = fish.energy / fish.max_energy

        # Check environment
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        predator_nearby = nearest_predator and (nearest_predator.pos - fish.pos).length() < 150
        food_nearby = nearest_food and (nearest_food.pos - fish.pos).length() < 100

        self.cycle_timer += 1

        # Interrupt cycle for emergencies
        if predator_nearby and not self.is_bursting:
            # Emergency burst to escape
            self.is_bursting = True
            self.cycle_timer = 0

        # Adjust cycle based on energy
        burst_duration = self.parameters["burst_duration"]
        rest_duration = self.parameters["rest_duration"]

        if energy_ratio < 0.3:
            # Low energy - shorter bursts, longer rest
            burst_duration *= 0.7
            rest_duration *= 1.3
        elif energy_ratio > 0.7:
            # High energy - longer bursts
            burst_duration *= 1.2
            rest_duration *= 0.8

        if self.is_bursting and self.cycle_timer > burst_duration:
            self.is_bursting = False
            self.cycle_timer = 0
        elif not self.is_bursting and self.cycle_timer > rest_duration:
            # Only burst if there's a reason (food, exploration, or good energy)
            if food_nearby or energy_ratio > 0.5:
                self.is_bursting = True
                self.cycle_timer = 0

        if self.is_bursting:
            # Directed burst movement
            if predator_nearby:
                # Burst away from predator
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["burst_speed"], direction.y * self.parameters["burst_speed"]
            elif food_nearby:
                # Burst toward food
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["burst_speed"], direction.y * self.parameters["burst_speed"]
            else:
                # Exploration burst - vary direction
                angle = self.cycle_timer * 0.1
                vx = math.cos(angle) * self.parameters["burst_speed"]
                vy = math.sin(angle) * self.parameters["burst_speed"] * 0.5
                return vx, vy
        else:
            # Resting - minimal drift
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
        from agents import Food, Crab, Fish as FishClass

        energy_ratio = fish.energy / fish.max_energy

        # Base speed influenced by energy
        base_speed = self.parameters["base_speed"] * (1 + (energy_ratio - 0.5) * self.parameters["energy_influence"])

        # Check environment for context
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        vx, vy = 0, 0

        # Predator response
        if nearest_predator:
            pred_distance = (nearest_predator.pos - fish.pos).length()
            if pred_distance < 140:
                # Escape with pace proportional to energy and threat
                threat = 1.0 - (pred_distance / 140)
                escape_speed = base_speed * (1.5 + threat * 0.8)
                # Reduce if low energy
                if energy_ratio < 0.3:
                    escape_speed *= 0.7
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * escape_speed, direction.y * escape_speed

        # Food seeking with adaptive pacing
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            hunger = 1.0 - energy_ratio

            # Only pursue if hungry enough or food is very close
            if hunger > 0.3 or food_distance < 60:
                # Pace based on distance and hunger
                pursuit_speed = base_speed * (0.7 + hunger * 0.6)
                # Speed up as we get closer
                if food_distance < 80:
                    pursuit_speed *= 1.3

                direction = (nearest_food.pos - fish.pos).normalize()
                vx = direction.x * pursuit_speed
                vy = direction.y * pursuit_speed

        # Social pacing - match nearby fish speeds
        if vx == 0 and vy == 0:
            allies = [f for f in fish.environment.get_agents_of_type(FishClass)
                     if f != fish and (f.pos - fish.pos).length() < 100]
            if allies:
                avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
                if avg_vel.length() > 0:
                    avg_vel_normalized = avg_vel.normalize()
                    # Match their pace but adjusted by our energy
                    social_pace = base_speed * 0.8
                    vx = avg_vel_normalized.x * social_pace
                    vy = avg_vel_normalized.y * social_pace

        # Default gentle cruising if nothing else to do
        if vx == 0 and vy == 0:
            # Cruise in a gentle pattern
            import time
            t = time.time() * 0.3
            vx = math.cos(t) * base_speed * 0.6
            vy = math.sin(t * 0.5) * base_speed * 0.3

        return vx, vy


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
        from agents import Food, Crab, Fish as FishClass
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # Check for important stimuli
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        # Predator avoidance
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        # Food opportunism
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            if food_distance < 70:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * 1.0, direction.y * 1.0

        # Boundary avoidance - don't explore into walls
        edge_margin = 60
        avoid_x, avoid_y = 0, 0
        if fish.pos.x < edge_margin:
            avoid_x = 0.5
        elif fish.pos.x > SCREEN_WIDTH - edge_margin:
            avoid_x = -0.5
        if fish.pos.y < edge_margin:
            avoid_y = 0.5
        elif fish.pos.y > SCREEN_HEIGHT - edge_margin:
            avoid_y = -0.5

        # Change direction periodically or when hitting boundaries
        if random.random() < self.parameters["change_frequency"] or (avoid_x != 0 or avoid_y != 0):
            # Bias new direction away from edges
            new_x = random.uniform(-1, 1) + avoid_x
            new_y = random.uniform(-1, 1) + avoid_y
            self.current_direction = Vector2(new_x, new_y)
            if self.current_direction.length() > 0:
                self.current_direction = self.current_direction.normalize()

        # Sometimes explore toward unexplored areas (away from other fish)
        if random.random() < 0.1:
            allies = fish.environment.get_agents_of_type(FishClass)
            if len(allies) > 1:
                # Find average position of other fish
                other_fish = [f for f in allies if f != fish]
                if other_fish:
                    crowd_center = sum((f.pos for f in other_fish), Vector2()) / len(other_fish)
                    # Explore away from the crowd
                    away_from_crowd = (fish.pos - crowd_center)
                    if away_from_crowd.length() > 0:
                        self.current_direction = away_from_crowd.normalize()

        return self.current_direction.x * self.parameters["exploration_speed"], \
               self.current_direction.y * self.parameters["exploration_speed"]


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
        from agents import Food, Crab

        if not self.initialized:
            # Create strategic waypoints - cover different areas of tank
            num_waypoints = random.randint(4, 7)
            for i in range(num_waypoints):
                # Distribute waypoints in a pattern
                angle = (2 * math.pi * i) / num_waypoints
                radius = random.uniform(120, 250)
                center_x, center_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
                wp_x = center_x + math.cos(angle) * radius
                wp_y = center_y + math.sin(angle) * radius
                # Clamp to bounds
                wp_x = max(60, min(SCREEN_WIDTH - 60, wp_x))
                wp_y = max(60, min(SCREEN_HEIGHT - 60, wp_y))
                self.waypoints.append(Vector2(wp_x, wp_y))
            self.initialized = True

        if not self.waypoints:
            return 0, 0

        # Check for threats and opportunities
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        # Interrupt patrol for immediate threats
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 100:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.3, direction.y * 1.3

        # Interrupt patrol for close food
        if nearest_food and (nearest_food.pos - fish.pos).length() < 60:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 0.9, direction.y * 0.9

        # Continue patrol
        target = self.waypoints[self.current_waypoint_idx]
        distance = (target - fish.pos).length()

        # Reached waypoint
        if distance < self.parameters["waypoint_threshold"]:
            # Look for food near this waypoint before moving on
            if nearest_food and (nearest_food.pos - target).length() < 100:
                # Food near waypoint - pursue it
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["patrol_speed"], direction.y * self.parameters["patrol_speed"]

            # Move to next waypoint
            self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
            target = self.waypoints[self.current_waypoint_idx]

        # Move toward current waypoint
        direction = (target - fish.pos)
        if direction.length() > 0:
            direction = direction.normalize()

            # Vary speed based on distance - slow down when approaching
            speed_multiplier = 1.0
            if distance < 80:
                speed_multiplier = 0.7 + (distance / 80) * 0.3

            return direction.x * self.parameters["patrol_speed"] * speed_multiplier, \
                   direction.y * self.parameters["patrol_speed"] * speed_multiplier
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
        from agents import Food, Crab
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # Check for threats and opportunities
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        # Immediate threat response
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 110:
            # Flee but maintain nomadic unpredictability
            base_escape = (fish.pos - nearest_predator.pos).normalize()
            perp_x, perp_y = -base_escape.y, base_escape.x
            randomness = random.uniform(-0.4, 0.4)
            vx = base_escape.x * 1.0 + perp_x * randomness
            vy = base_escape.y * 1.0 + perp_y * randomness
            return vx, vy

        # Opportunistic food grab
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            if food_distance < 50:
                # Close food - grab it
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * 1.0, direction.y * 1.0

        # Boundary awareness - avoid getting stuck in corners
        edge_margin = 70
        boundary_influence = 0
        if fish.pos.x < edge_margin or fish.pos.x > SCREEN_WIDTH - edge_margin or \
           fish.pos.y < edge_margin or fish.pos.y > SCREEN_HEIGHT - edge_margin:
            # Turn toward center
            center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            to_center = (center - fish.pos).normalize()
            # Blend turn toward center with random wandering
            boundary_influence = 0.4
            self.wander_angle = math.atan2(to_center.y, to_center.x) + random.gauss(0, 0.3)

        # Gradually change direction with smooth random walk
        angle_change = random.gauss(0, self.parameters["direction_change_rate"])
        self.wander_angle += angle_change

        # Add some Perlin-like noise for more natural wandering
        # Use fish position to add spatial variation
        spatial_influence = math.sin(fish.pos.x * 0.01) * 0.05 + math.cos(fish.pos.y * 0.01) * 0.05
        self.wander_angle += spatial_influence

        vx = math.cos(self.wander_angle) * self.parameters["wander_strength"]
        vy = math.sin(self.wander_angle) * self.parameters["wander_strength"]

        # Energy-based activity
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.4:
            # Lower energy = more purposeful toward food
            if nearest_food and (nearest_food.pos - fish.pos).length() < 150:
                food_dir = (nearest_food.pos - fish.pos).normalize()
                # Blend wandering with food seeking
                vx = vx * 0.4 + food_dir.x * 0.6
                vy = vy * 0.4 + food_dir.y * 0.6

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


def get_algorithm_index(algorithm: BehaviorAlgorithm) -> int:
    """Get the index of an algorithm in the ALL_ALGORITHMS list.

    Args:
        algorithm: The behavior algorithm instance

    Returns:
        Index (0-47) of the algorithm, or -1 if not found
    """
    algorithm_class = type(algorithm)
    try:
        return ALL_ALGORITHMS.index(algorithm_class)
    except ValueError:
        return -1


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
