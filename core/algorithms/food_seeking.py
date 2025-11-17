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

import random
import math
from typing import Tuple, List
from dataclasses import dataclass

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.constants import SCREEN_HEIGHT
from core.entities import Food, Crab, Fish as FishClass


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

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check for predators first - but adjust caution based on energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

        # IMPROVEMENT: Adaptive flee threshold based on energy state
        flee_threshold = 45 if is_critical else (80 if is_low else 120)

        if predator_distance < flee_threshold:
            # NEW: Use predictive avoidance
            if hasattr(nearest_predator, 'vel'):
                from core.predictive_movement import get_avoidance_direction
                direction = get_avoidance_direction(
                    fish.pos, fish.vel, nearest_predator.pos, nearest_predator.vel, 1.0
                )
            else:
                # Fallback to simple flee
                direction = (fish.pos - nearest_predator.pos).normalize()

            # IMPROVEMENT: Conserve energy when fleeing in critical state
            flee_speed = 1.1 if is_critical else 1.3

            # NEW: Remember danger zone
            if hasattr(fish, 'memory_system'):
                from core.fish_memory import MemoryType
                fish.memory_system.add_memory(
                    MemoryType.DANGER_ZONE,
                    nearest_predator.pos,
                    strength=1.0,
                    metadata={'predator_type': type(nearest_predator).__name__}
                )

            return direction.x * flee_speed, direction.y * flee_speed

        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()

            # IMPROVEMENT: Smarter chase distance calculation
            if is_critical:
                max_chase_distance = 400  # Chase far when desperate
            elif is_low:
                max_chase_distance = 250  # Moderate chase when low
            else:
                max_chase_distance = 150 + (energy_ratio * 150)  # Conservative when safe

            if distance < max_chase_distance:
                # NEW: Use predictive interception for moving food
                if hasattr(nearest_food, 'vel') and nearest_food.vel.length() > 0.1:
                    from core.predictive_movement import predict_intercept_point
                    intercept_point, _ = predict_intercept_point(
                        fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                    )
                    if intercept_point:
                        target_pos = intercept_point
                    else:
                        target_pos = nearest_food.pos
                else:
                    target_pos = nearest_food.pos

                direction = (target_pos - fish.pos).normalize()

                # IMPROVEMENT: Speed based on urgency and distance
                base_speed = self.parameters["speed_multiplier"]

                # Speed up when closer to food
                proximity_boost = (1.0 - min(distance / 100, 1.0)) * 0.5

                # Urgency boost when low/critical energy
                urgency_boost = 0.3 if is_critical else (0.15 if is_low else 0)

                speed = base_speed * (1.0 + proximity_boost + urgency_boost)

                # NEW: Remember successful food locations
                if hasattr(fish, 'memory_system') and distance < 50:
                    from core.fish_memory import MemoryType
                    fish.memory_system.add_memory(
                        MemoryType.FOOD_LOCATION,
                        nearest_food.pos,
                        strength=0.8
                    )

                return direction.x * speed, direction.y * speed

        # NEW: Use enhanced memory system if no food found
        if (is_critical or is_low) and hasattr(fish, 'memory_system'):
            from core.fish_memory import MemoryType
            best_food_memory = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
            if best_food_memory:
                direction = (best_food_memory.location - fish.pos).normalize()
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
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check for predators - even urgent fish should avoid immediate danger
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

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

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check predators first - but be less cautious when critically low energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

        # In critical energy, only flee if predator is very close
        flee_threshold = 50 if is_critical else (70 if is_low else 90)
        if nearest_predator and predator_distance < flee_threshold:
            direction = (fish.pos - nearest_predator.pos).normalize()
            flee_speed = 1.2 if is_critical else 1.4  # Conserve energy even when fleeing
            return direction.x * flee_speed, direction.y * flee_speed

        foods = fish.environment.get_agents_of_type(Food)
        best_food = None
        best_score = -float('inf')

        # IMPROVEMENT: Also consider remembered food locations if no food visible
        remembered_locations = fish.get_remembered_food_locations() if hasattr(fish, 'get_remembered_food_locations') else []

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
            score = (quality * quality_weight
                    - distance * distance_weight
                    - danger_score * danger_weight)

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
            direction = (best_food.pos - fish.pos).normalize()
            # IMPROVEMENT: Speed based on urgency and distance
            base_speed = 1.1 if is_critical else 0.9
            speed = base_speed + min(50 / max(distance_to_food, 1), 0.5)
            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: If no good food found but have memories and critically low, go to memory
        if is_critical and remembered_locations:
            closest_memory = min(remembered_locations, key=lambda pos: (pos - fish.pos).length())
            direction = (closest_memory - fish.pos).normalize()
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
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

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

        # Check for nearby food first
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 100:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * self.parameters["food_priority"], direction.y * self.parameters["food_priority"]

        # Otherwise patrol
        if self.patrol_center is None:
            self.patrol_center = Vector2(fish.pos.x, fish.pos.y)

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

        # Look for current food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            # Remember this location
            if len(self.food_memory_locations) < 5:
                self.food_memory_locations.append(Vector2(nearest_food.pos.x, nearest_food.pos.y))
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

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 95:
            # NEW: Broadcast danger signal
            if hasattr(fish.environment, 'communication_system'):
                from core.fish_communication import SignalType
                fish.environment.communication_system.broadcast_signal(
                    SignalType.DANGER_WARNING,
                    fish.pos,
                    target_location=nearest_predator.pos,
                    strength=1.0,
                    urgency=1.0
                )

            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.3, direction.y * 1.3

        # Look for food directly first
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food and (nearest_food.pos - fish.pos).length() < 80:
            # NEW: Broadcast food found signal (if social)
            if hasattr(fish.environment, 'communication_system') and fish.genome.social_tendency > 0.5:
                from core.fish_communication import SignalType
                fish.environment.communication_system.broadcast_signal(
                    SignalType.FOOD_FOUND,
                    fish.pos,
                    target_location=nearest_food.pos,
                    strength=fish.genome.social_tendency,  # More social = stronger signal
                    urgency=0.7
                )

            # Food is close, go for it directly
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 1.1, direction.y * 1.1

        # NEW: Listen for food signals from communication system
        best_signal_target = None
        if hasattr(fish.environment, 'communication_system'):
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
                    if hasattr(other_fish, 'vel') and other_fish.vel.length() > 0:
                        to_food = (food.pos - other_fish.pos).normalize()
                        vel_dir = other_fish.vel.normalize()
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
