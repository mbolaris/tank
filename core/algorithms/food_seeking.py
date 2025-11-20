"""Food-seeking behavior algorithms.

This module contains 12 algorithms focused on finding and pursuing food:
- GreedyFoodSeeker: Always move directly toward nearest food
- EnergyAwareFoodSeeker: Seek food more aggressively when energy is low
- OpportunisticFeeder: Only pursue food if it's close enough
- FoodQualityOptimizer: Prefer high-value food types
- AmbushFeeder: Wait in one spot for food to come close
- PatrolFeeder: Patrol in a pattern looking for food
- SurfaceSkimmer: Stay near surface to catch falling food
- BottomFeeder: Stay near bottom to catch sinking food
- ZigZagForager: Move in zigzag pattern to maximize food discovery
- CircularHunter: Circle around food before striking
- FoodMemorySeeker: Remember where food was found before
- CooperativeForager: Follow other fish to food sources
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.constants import (
    CHASE_DISTANCE_CRITICAL,
    CHASE_DISTANCE_LOW,
    CHASE_DISTANCE_SAFE_BASE,
    FLEE_SPEED_CRITICAL,
    FLEE_SPEED_NORMAL,
    FLEE_THRESHOLD_CRITICAL,
    FLEE_THRESHOLD_LOW,
    FLEE_THRESHOLD_NORMAL,
    PROXIMITY_BOOST_DIVISOR,
    PROXIMITY_BOOST_MULTIPLIER,
    SCREEN_HEIGHT,
    URGENCY_BOOST_CRITICAL,
    URGENCY_BOOST_LOW,
)
from core.entities import Crab, Food
from core.entities import Fish as FishClass


@dataclass
class GreedyFoodSeeker(BehaviorAlgorithm):
    """Always move directly toward nearest food."""

    def __init__(self):
        super().__init__(
            algorithm_id="greedy_food_seeker",
            parameters={
                "speed_multiplier": random.uniform(0.7, 1.3),
                "detection_range": random.uniform(0.5, 1.0),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check for predators first - but adjust caution based on energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

        # IMPROVEMENT: Adaptive flee threshold based on energy state
        flee_threshold = (
            FLEE_THRESHOLD_CRITICAL
            if is_critical
            else (FLEE_THRESHOLD_LOW if is_low else FLEE_THRESHOLD_NORMAL)
        )

        if predator_distance < flee_threshold:
            # NEW: Use predictive avoidance
            if hasattr(nearest_predator, "vel"):
                from core.predictive_movement import get_avoidance_direction

                direction = get_avoidance_direction(
                    fish.pos, fish.vel, nearest_predator.pos, nearest_predator.vel, 1.0
                )
            else:
                # Fallback to simple flee
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)

            # IMPROVEMENT: Conserve energy when fleeing in critical state
            flee_speed = FLEE_SPEED_CRITICAL if is_critical else FLEE_SPEED_NORMAL

            # NEW: Remember danger zone
            if hasattr(fish, "memory_system"):
                from core.fish_memory import MemoryType

                fish.memory_system.add_memory(
                    MemoryType.DANGER_ZONE,
                    nearest_predator.pos,
                    strength=1.0,
                    metadata={"predator_type": type(nearest_predator).__name__},
                )

            return direction.x * flee_speed, direction.y * flee_speed

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()

            # IMPROVEMENT: Smarter chase distance calculation
            if is_critical:
                max_chase_distance = CHASE_DISTANCE_CRITICAL
            elif is_low:
                max_chase_distance = CHASE_DISTANCE_LOW
            else:
                max_chase_distance = CHASE_DISTANCE_SAFE_BASE + (
                    energy_ratio * CHASE_DISTANCE_SAFE_BASE
                )

            if distance < max_chase_distance:
                # NEW: Use predictive interception for moving food
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.1:
                    from core.predictive_movement import predict_intercept_point

                    intercept_point, _ = predict_intercept_point(
                        fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                    )
                    target_pos = intercept_point or nearest_food.pos
                else:
                    target_pos = nearest_food.pos

                direction = self._safe_normalize(target_pos - fish.pos)

                # IMPROVEMENT: Speed based on urgency and distance
                base_speed = self.parameters["speed_multiplier"]

                # Speed up when closer to food
                proximity_boost = (
                    1.0 - min(distance / PROXIMITY_BOOST_DIVISOR, 1.0)
                ) * PROXIMITY_BOOST_MULTIPLIER

                # Urgency boost when low/critical energy
                urgency_boost = (
                    URGENCY_BOOST_CRITICAL if is_critical else (URGENCY_BOOST_LOW if is_low else 0)
                )

                speed = base_speed * (1.0 + proximity_boost + urgency_boost)

                # NEW: Remember successful food locations
                if hasattr(fish, "memory_system") and distance < 50:
                    from core.fish_memory import MemoryType

                    fish.memory_system.add_memory(
                        MemoryType.FOOD_LOCATION, nearest_food.pos, strength=0.8
                    )

                return direction.x * speed, direction.y * speed

        # NEW: Use enhanced memory system if no food found
        if (is_critical or is_low) and hasattr(fish, "memory_system"):
            from core.fish_memory import MemoryType

            best_food_memory = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
            if best_food_memory:
                direction = self._safe_normalize(best_food_memory.location - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check for predators - even urgent fish should avoid immediate danger
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999
        predator_nearby = predator_distance < 100  # Define predator proximity threshold

        # IMPROVEMENT: Critical energy mode - must find food NOW
        if is_critical:
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
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return (
                    direction.x * self.parameters["urgent_speed"],
                    direction.y * self.parameters["urgent_speed"],
                )

        # Flee if predator too close
        if predator_nearby:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            # Graduated urgency based on energy level
            if energy_ratio < self.parameters["urgency_threshold"]:
                speed = self.parameters["urgent_speed"]
            else:
                # Scale speed based on energy - conserve when high energy
                speed = self.parameters["calm_speed"] + (1.0 - energy_ratio) * 0.3

            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * speed, direction.y * speed
        return 0, 0


@dataclass
class OpportunisticFeeder(BehaviorAlgorithm):
    """Only pursue food if it's close enough - IMPROVED to avoid starvation."""

    def __init__(self):
        super().__init__(
            algorithm_id="opportunistic_feeder",
            parameters={
                "max_pursuit_distance": random.uniform(150, 300),  # INCREASED from 50-200
                "speed": random.uniform(0.9, 1.3),  # INCREASED from 0.6-1.0
                "exploration_speed": random.uniform(0.5, 0.8),  # NEW: explore when idle
            },
        )
        self.exploration_angle = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy state
        is_critical = fish.energy / fish.max_energy < 0.3
        is_low = fish.energy / fish.max_energy < 0.5

        # IMPROVEMENT: Flee from predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            flee_threshold = 60 if is_critical else 90
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest(fish, Food)
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
                if distance < 100:
                    speed *= 1.3
                if is_critical:
                    speed *= 1.2
                return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Don't just idle - explore!
        if is_critical or is_low:
            self.exploration_angle += random.uniform(-0.4, 0.4)
            ex_speed = self.parameters["exploration_speed"] * (1.5 if is_critical else 1.0)
            return (
                math.cos(self.exploration_angle) * ex_speed,
                math.sin(self.exploration_angle) * ex_speed,
            )

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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        fish.get_energy_ratio()

        # Check predators first - but be less cautious when critically low energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

        # In critical energy, only flee if predator is very close
        flee_threshold = 50 if is_critical else (70 if is_low else 90)
        if nearest_predator and predator_distance < flee_threshold:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            flee_speed = 1.2 if is_critical else 1.4  # Conserve energy even when fleeing
            return direction.x * flee_speed, direction.y * flee_speed

        foods = fish.environment.get_agents_of_type(Food)
        best_food = None
        best_score = -float("inf")

        # IMPROVEMENT: Also consider remembered food locations if no food visible
        remembered_locations = (
            fish.get_remembered_food_locations()
            if hasattr(fish, "get_remembered_food_locations")
            else []
        )

        for food in foods:
            distance = (food.pos - fish.pos).length()
            quality = food.get_energy_value()

            # Check if predator is near this food (danger score)
            danger_score = 0
            if nearest_predator:
                predator_food_dist = (nearest_predator.pos - food.pos).length()
                if predator_food_dist < 120:
                    danger_score = (120 - predator_food_dist) / 1.2  # Scale to 0-100

            # IMPROVEMENT: Smarter danger weighting based on energy state
            # Critical energy: mostly ignore danger (0.1 weight)
            # Low energy: some caution (0.4 weight)
            # Normal energy: high caution (0.8 weight)
            if is_critical:
                danger_weight = 0.1
            elif is_low:
                danger_weight = 0.4
            else:
                danger_weight = 0.7

            # IMPROVEMENT: Increase quality weight when low energy
            quality_weight = self.parameters["quality_weight"] * (1.5 if is_low else 1.0)
            distance_weight = self.parameters["distance_weight"] * (1.3 if is_critical else 1.0)

            # Calculate value: high quality, close distance, low danger
            score = (
                quality * quality_weight - distance * distance_weight - danger_score * danger_weight
            )

            # IMPROVEMENT: Bonus for food that's closer than predator
            if nearest_predator and distance < predator_distance * 0.7:
                score += 20  # Bonus for food we can likely get before predator

            if score > best_score:
                best_score = score
                best_food = food

        # IMPROVEMENT: Lower threshold for pursuing food when critically low
        min_score_threshold = -80 if is_critical else (-60 if is_low else -50)

        if best_food and best_score > min_score_threshold:
            distance_to_food = (best_food.pos - fish.pos).length()
            direction = self._safe_normalize(best_food.pos - fish.pos)
            # IMPROVEMENT: Speed based on urgency and distance
            base_speed = 1.1 if is_critical else 0.9
            speed = base_speed + min(50 / max(distance_to_food, 1), 0.5)
            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: If no good food found but have memories and critically low, go to memory
        if is_critical and remembered_locations:
            closest_memory = min(remembered_locations, key=lambda pos: (pos - fish.pos).length())
            direction = self._safe_normalize(closest_memory - fish.pos)
            return direction.x * 0.8, direction.y * 0.8

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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            if distance < self.parameters["strike_distance"]:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return (
                    direction.x * self.parameters["strike_speed"],
                    direction.y * self.parameters["strike_speed"],
                )
        return 0, 0


@dataclass
class PatrolFeeder(BehaviorAlgorithm):
    """Patrol in a pattern looking for food - IMPROVED with better detection."""

    def __init__(self):
        super().__init__(
            algorithm_id="patrol_feeder",
            parameters={
                "patrol_radius": random.uniform(100, 200),  # INCREASED from 50-150
                "patrol_speed": random.uniform(0.8, 1.2),  # INCREASED from 0.5-1.0
                "food_priority": random.uniform(1.0, 1.4),  # INCREASED from 0.6-1.0
            },
        )
        self.patrol_center = None
        self.patrol_angle = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy and predators
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < 80:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Check for nearby food first - EXPANDED detection
        nearest_food = self._find_nearest(fish, Food)
        detection_range = 200 if is_desperate else 150  # INCREASED from 100
        if nearest_food and (nearest_food.pos - fish.pos).length() < detection_range:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            # IMPROVEMENT: Faster when desperate
            speed = self.parameters["food_priority"] * (1.3 if is_desperate else 1.0)
            return direction.x * speed, direction.y * speed

        # Otherwise patrol - FASTER rotation
        if self.patrol_center is None:
            self.patrol_center = Vector2(fish.pos.x, fish.pos.y)

        self.patrol_angle += 0.15  # INCREASED from 0.05 for faster patrol
        target_x = (
            self.patrol_center.x + math.cos(self.patrol_angle) * self.parameters["patrol_radius"]
        )
        target_y = (
            self.patrol_center.y + math.sin(self.patrol_angle) * self.parameters["patrol_radius"]
        )
        direction = self._safe_normalize(Vector2(target_x, target_y) - fish.pos)
        # IMPROVEMENT: Patrol faster to cover more ground
        speed = self.parameters["patrol_speed"] * (1.3 if is_desperate else 1.0)
        return direction.x * speed, direction.y * speed


@dataclass
class SurfaceSkimmer(BehaviorAlgorithm):
    """Stay near surface to catch falling food - IMPROVED for better survival."""

    def __init__(self):
        super().__init__(
            algorithm_id="surface_skimmer",
            parameters={
                "preferred_depth": random.uniform(0.1, 0.25),  # 10-25% from top
                "horizontal_speed": random.uniform(0.8, 1.3),  # INCREASED from 0.5-1.0
                "dive_for_food_threshold": random.uniform(150, 250),  # NEW: will dive for food
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy and threats
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < 90:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]

        # Look for food - IMPROVED to actively pursue
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            food_dist = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Dive for food if desperate or food is reasonably close
            if is_desperate or food_dist < self.parameters["dive_for_food_threshold"]:
                # Go directly for food, abandoning surface position
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                speed = 1.2 if is_desperate else 1.0
                return direction.x * speed, direction.y * speed
            else:
                # Move horizontally toward food while maintaining depth
                vx = (nearest_food.pos.x - fish.pos.x) / 80  # FASTER horizontal tracking
                vy = (target_y - fish.pos.y) / 100
                # IMPROVEMENT: Speed up horizontal movement
                vx *= 1.5
                return vx, vy
        else:
            # No food visible - patrol surface actively
            vy = (target_y - fish.pos.y) / 100
            # IMPROVEMENT: Active patrol instead of random flip
            vx = self.parameters["horizontal_speed"]
            # Change direction periodically
            if random.random() < 0.02:  # 2% chance per frame to reverse
                self.parameters["horizontal_speed"] *= -1
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]
        vy = (target_y - fish.pos.y) / 100

        nearest_food = self._find_nearest(fish, Food)
        vx = 0
        if nearest_food:
            vx = (nearest_food.pos.x - fish.pos.x) / 100
        else:
            vx = (
                self.parameters["search_speed"]
                if random.random() > 0.5
                else -self.parameters["search_speed"]
            )

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
            },
        )
        self.zigzag_phase = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check for nearby food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 80:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x, direction.y

        # Zigzag movement
        self.zigzag_phase += self.parameters["zigzag_frequency"]
        vx = self.parameters["forward_speed"]
        vy = math.sin(self.zigzag_phase) * self.parameters["zigzag_amplitude"]

        return vx, vy


@dataclass
class CircularHunter(BehaviorAlgorithm):
    """Circle around food before striking - IMPROVED for better survival."""

    def __init__(self):
        super().__init__(
            algorithm_id="circular_hunter",
            parameters={
                "circle_radius": random.uniform(50, 80),
                "approach_speed": random.uniform(0.9, 1.2),
                "strike_distance": random.uniform(60, 100),
                "exploration_speed": random.uniform(0.6, 0.9),
            },
        )
        self.circle_angle = 0
        self.exploration_direction = random.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check energy status for smarter decisions
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3
        is_low_energy = energy_ratio < 0.5

        # Predator check - flee distance based on energy
        nearest_predator = self._find_nearest(fish, Crab)
        flee_distance = 80 if is_desperate else 110
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < flee_distance:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            # Conserve energy when desperate
            flee_speed = 1.2 if is_desperate else 1.4
            return direction.x * flee_speed, direction.y * flee_speed

        nearest_food = self._find_nearest(fish, Food)
        if not nearest_food:
            # CRITICAL FIX: Actively explore instead of stopping!
            # Slowly change direction for more exploration coverage
            self.exploration_direction += random.uniform(-0.3, 0.3)
            exploration_vec = Vector2(
                math.cos(self.exploration_direction), math.sin(self.exploration_direction)
            )
            speed = self.parameters["exploration_speed"]
            return exploration_vec.x * speed, exploration_vec.y * speed

        distance = (nearest_food.pos - fish.pos).length()

        # If food is moving (has velocity), predict its position
        food_future_pos = nearest_food.pos
        if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0:
            # Predict food position 10 frames ahead
            food_future_pos = nearest_food.pos + nearest_food.vel * 10

        # IMPROVEMENT: Skip circling when desperate or very hungry
        # Go straight for food when energy is low!
        if is_desperate or is_low_energy:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            speed = 1.3  # Fast, direct approach when hungry
            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Larger strike distance to actually catch food
        if distance < self.parameters["strike_distance"]:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            # Fast strike
            return direction.x * 1.5, direction.y * 1.5

        # Only circle when well-fed (this is the "hunting" behavior)
        # IMPROVEMENT: Much faster circling to not waste time
        if distance < 200:
            self.circle_angle += 0.25  # Much faster than old 0.05-0.15!

            target_x = (
                nearest_food.pos.x + math.cos(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_y = (
                nearest_food.pos.y + math.sin(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_vector = Vector2(target_x, target_y) - fish.pos
            direction = self._safe_normalize(target_vector)
            # Faster circling movement
            speed = self.parameters["approach_speed"]
            return direction.x * speed, direction.y * speed
        else:
            # Food is far - approach directly
            direction = self._safe_normalize(food_future_pos - fish.pos)
            return (
                direction.x * self.parameters["approach_speed"],
                direction.y * self.parameters["approach_speed"],
            )


@dataclass
class FoodMemorySeeker(BehaviorAlgorithm):
    """Remember where food was found before."""

    def __init__(self):
        super().__init__(
            algorithm_id="food_memory_seeker",
            parameters={
                "memory_strength": random.uniform(0.5, 1.0),
                "exploration_rate": random.uniform(0.2, 0.5),
            },
        )
        self.food_memory_locations: List[Vector2] = []

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Look for current food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            # Remember this location
            if len(self.food_memory_locations) < 5:
                self.food_memory_locations.append(Vector2(nearest_food.pos.x, nearest_food.pos.y))
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x, direction.y

        # No food visible, check memory
        if self.food_memory_locations and random.random() > self.parameters["exploration_rate"]:
            target = random.choice(self.food_memory_locations)
            direction = self._safe_normalize(target - fish.pos)
            return (
                direction.x * self.parameters["memory_strength"],
                direction.y * self.parameters["memory_strength"],
            )

        return 0, 0


@dataclass
class AggressiveHunter(BehaviorAlgorithm):
    """NEW: Aggressively pursue food with high-speed interception - replaces weak algorithms."""

    def __init__(self):
        super().__init__(
            algorithm_id="aggressive_hunter",
            parameters={
                "pursuit_speed": random.uniform(1.3, 1.7),
                "detection_range": random.uniform(250, 400),
                "strike_speed": random.uniform(1.5, 2.0),
            },
        )
        self.last_food_pos = None

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        is_critical = energy_ratio < 0.3

        # Predator check - but take more risks when desperate
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            flee_threshold = 50 if is_critical else 75  # Risk more when desperate
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.4, direction.y * 1.4

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            self.last_food_pos = Vector2(nearest_food.pos.x, nearest_food.pos.y)

            # High-speed pursuit within detection range
            if distance < self.parameters["detection_range"]:
                # Predict food movement
                target_pos = nearest_food.pos
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0:
                    # Lead the target
                    target_pos = nearest_food.pos + nearest_food.vel * 15

                direction = self._safe_normalize(target_pos - fish.pos)

                # Strike mode when very close
                if distance < 80:
                    return (
                        direction.x * self.parameters["strike_speed"],
                        direction.y * self.parameters["strike_speed"],
                    )
                else:
                    return (
                        direction.x * self.parameters["pursuit_speed"],
                        direction.y * self.parameters["pursuit_speed"],
                    )

        # No food visible - check last known location
        if self.last_food_pos and is_critical:
            direction = self._safe_normalize(self.last_food_pos - fish.pos)
            return direction.x * 0.9, direction.y * 0.9

        # Active exploration
        import math

        angle = fish.age * 0.1  # Use age for varied exploration
        return math.cos(angle) * 0.7, math.sin(angle) * 0.7


@dataclass
class SpiralForager(BehaviorAlgorithm):
    """NEW: Spiral outward from center to systematically cover area - replaces weak algorithms."""

    def __init__(self):
        super().__init__(
            algorithm_id="spiral_forager",
            parameters={
                "spiral_speed": random.uniform(0.8, 1.2),
                "spiral_growth": random.uniform(0.3, 0.7),
                "food_pursuit_speed": random.uniform(1.1, 1.5),
            },
        )
        self.spiral_angle = 0
        self.spiral_radius = 10

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < 85:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Always check for food first
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # Abandon spiral to pursue food
            if distance < 250 or is_desperate:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
                return direction.x * speed, direction.y * speed

        # Spiral search pattern
        self.spiral_angle += 0.25  # Fast spiral
        self.spiral_radius += self.parameters["spiral_growth"]

        # Reset spiral if too large
        if self.spiral_radius > 150:
            self.spiral_radius = 10

        # Calculate spiral movement
        import math

        vx = math.cos(self.spiral_angle) * self.parameters["spiral_speed"]
        vy = math.sin(self.spiral_angle) * self.parameters["spiral_speed"]

        return vx, vy


@dataclass
class CooperativeForager(BehaviorAlgorithm):
    """Follow other fish to food sources - HEAVILY IMPROVED."""

    def __init__(self):
        super().__init__(
            algorithm_id="cooperative_forager",
            parameters={
                "follow_strength": random.uniform(0.8, 1.2),  # INCREASED from 0.5-0.9
                "independence": random.uniform(0.5, 0.8),  # INCREASED from 0.2-0.5
                "food_pursuit_speed": random.uniform(1.1, 1.4),  # NEW
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy state
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # Check for predators - IMPROVED avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 100:
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

            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.3, direction.y * 1.3

        # Look for food directly first - EXPANDED range
        nearest_food = self._find_nearest(fish, Food)
        detection_range = 150 if is_desperate else 100  # INCREASED from 80
        if nearest_food and (nearest_food.pos - fish.pos).length() < detection_range:
            # NEW: Broadcast food found signal (if social)
            if (
                hasattr(fish.environment, "communication_system")
                and fish.genome.social_tendency > 0.5
            ):
                from core.fish_communication import SignalType

                fish.environment.communication_system.broadcast_signal(
                    SignalType.FOOD_FOUND,
                    fish.pos,
                    target_location=nearest_food.pos,
                    strength=fish.genome.social_tendency,  # More social = stronger signal
                    urgency=0.7,
                )

            # Food is close, go for it directly - FASTER
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
            return direction.x * speed, direction.y * speed

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
                    if hasattr(other_fish, "vel") and other_fish.vel.length() > 0:
                        to_food = self._safe_normalize(food.pos - other_fish.pos)
                        vel_dir = self._safe_normalize(other_fish.vel)
                        alignment = to_food.dot(vel_dir)
                        if alignment > 0.5:  # Fish is moving toward food
                            score *= 1.5

                    if score > best_score:
                        best_score = score
                        best_target = other_fish.pos

        # NEW: Prefer signal target if it's good
        if best_signal_target:
            signal_dist = (best_signal_target - fish.pos).length()
            if signal_dist < 250:  # Within reasonable range
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
        if random.random() < self.parameters["independence"]:
            return random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)

        return 0, 0
