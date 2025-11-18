"""Schooling and social behavior algorithms.

This module contains 10 algorithms focused on group behavior and social interactions:
- TightSchooler: Stay very close to school members
- LooseSchooler: Maintain loose association with school
- LeaderFollower: Follow the fastest/strongest fish
- AlignmentMatcher: Match velocity with nearby fish
- SeparationSeeker: Avoid crowding neighbors
- FrontRunner: Lead the school from the front
- PerimeterGuard: Stay on the outside of the school
- MirrorMover: Mirror the movements of nearby fish
- BoidsBehavior: Classic boids algorithm (separation, alignment, cohesion)
- DynamicSchooler: Switch between tight and loose schooling based on conditions
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.entities import Crab, Food
from core.entities import Fish as FishClass


@dataclass
class TightSchooler(BehaviorAlgorithm):
    """Stay very close to school members."""

    def __init__(self):
        super().__init__(
            algorithm_id="tight_schooler",
            parameters={
                "cohesion_strength": random.uniform(0.7, 1.2),
                "preferred_distance": random.uniform(20, 50),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            direction = self._safe_normalize(center - fish.pos)
            return (
                direction.x * self.parameters["cohesion_strength"],
                direction.y * self.parameters["cohesion_strength"],
            )
        return 0, 0


@dataclass
class LooseSchooler(BehaviorAlgorithm):
    """Maintain loose association with school."""

    def __init__(self):
        super().__init__(
            algorithm_id="loose_schooler",
            parameters={
                "cohesion_strength": random.uniform(0.3, 0.6),
                "max_distance": random.uniform(100, 200),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            distance = (center - fish.pos).length()
            if distance > self.parameters["max_distance"]:
                direction = self._safe_normalize(center - fish.pos)
                return (
                    direction.x * self.parameters["cohesion_strength"],
                    direction.y * self.parameters["cohesion_strength"],
                )
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            # Find "leader" (fish with most energy)
            leader = max(allies, key=lambda f: f.energy)
            distance = (leader.pos - fish.pos).length()
            if 0 < distance < self.parameters["max_follow_distance"]:
                direction = self._safe_normalize(leader.pos - fish.pos)
                return (
                    direction.x * self.parameters["follow_strength"],
                    direction.y * self.parameters["follow_strength"],
                )
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish
            and f.species == fish.species
            and (f.pos - fish.pos).length() < self.parameters["alignment_radius"]
        ]

        if allies:
            avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
            if avg_vel.length() > 0:
                avg_vel = self._safe_normalize(avg_vel)
                return (
                    avg_vel.x * self.parameters["alignment_strength"],
                    avg_vel.y * self.parameters["alignment_strength"],
                )
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [f for f in fish.environment.get_agents_of_type(FishClass) if f != fish]

        vx, vy = 0, 0
        for ally in allies:
            distance = (ally.pos - fish.pos).length()
            if 0 < distance < self.parameters["min_distance"]:
                direction = self._safe_normalize(fish.pos - ally.pos)
                strength = (self.parameters["min_distance"] - distance) / self.parameters[
                    "min_distance"
                ]
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Move in a consistent direction
        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            # Move away from center to lead
            direction = self._safe_normalize(fish.pos - center)
            return (
                direction.x * self.parameters["leadership_strength"],
                direction.y * self.parameters["leadership_strength"],
            )

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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            to_center = center - fish.pos
            distance = to_center.length()

            if distance < self.parameters["orbit_radius"]:
                # Move away from center
                normalized = self._safe_normalize(to_center)
                direction = Vector2(-normalized.x, -normalized.y)
                return (
                    direction.x * self.parameters["orbit_speed"],
                    direction.y * self.parameters["orbit_speed"],
                )
            elif distance > self.parameters["orbit_radius"] * 1.3:
                # Move toward center
                direction = self._safe_normalize(to_center)
                return (
                    direction.x * self.parameters["orbit_speed"],
                    direction.y * self.parameters["orbit_speed"],
                )
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and (f.pos - fish.pos).length() < self.parameters["mirror_distance"]
        ]

        if allies:
            nearest = min(allies, key=lambda f: (f.pos - fish.pos).length())
            # Copy their velocity
            if nearest.vel.length() > 0:
                direction = self._safe_normalize(nearest.vel)
                return (
                    direction.x * self.parameters["mirror_strength"],
                    direction.y * self.parameters["mirror_strength"],
                )
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]

        # Check for predators - school tightens when threatened
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (
            nearest_predator and (nearest_predator.pos - fish.pos).length() or float("inf")
        )
        in_danger = predator_distance < 200

        # Check for food opportunities
        nearest_food = self._find_nearest(fish, Food)
        food_distance = nearest_food and (nearest_food.pos - fish.pos).length() or float("inf")
        food_nearby = food_distance < 100

        if not allies:
            # Alone - seek food or flee
            if in_danger and predator_distance < 150:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3
            elif food_nearby:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
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
                direction = self._safe_normalize(fish.pos - ally.pos)
                # Stronger separation when very close
                strength = (separation_distance - distance) / separation_distance
                sep_x += direction.x * strength / max(distance, 1)
                sep_y += direction.y * strength / max(distance, 1)

        # Alignment - match velocity
        avg_vel = sum((f.vel for f in nearby_allies), Vector2()) / len(nearby_allies)
        if avg_vel.length() > 0:
            avg_vel = self._safe_normalize(avg_vel)
        align_x, align_y = avg_vel.x, avg_vel.y

        # Cohesion - move toward center
        center = sum((f.pos for f in nearby_allies), Vector2()) / len(nearby_allies)
        coh_dir = self._safe_normalize(center - fish.pos)

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
        vx = sep_x * sep_weight + align_x * align_weight + coh_dir.x * coh_weight
        vy = sep_y * sep_weight + align_y * align_weight + coh_dir.y * coh_weight

        # Add predator avoidance
        if in_danger and predator_distance < 150:
            avoid_dir = self._safe_normalize(fish.pos - nearest_predator.pos)
            threat_strength = (150 - predator_distance) / 150
            vx += avoid_dir.x * threat_strength * 2.0
            vy += avoid_dir.y * threat_strength * 2.0

        # Add food attraction for whole school
        if food_nearby and food_distance < 80:
            food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
            vx += food_dir.x * 0.5
            vy += food_dir.y * 0.5

        # Normalize
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            return vx / length, vy / length
        return 0, 0


@dataclass
class DynamicSchooler(BehaviorAlgorithm):
    """Switch between tight and loose schooling based on conditions."""

    def __init__(self):
        super().__init__(
            algorithm_id="dynamic_schooler",
            parameters={
                "danger_cohesion": random.uniform(0.8, 1.2),
                "calm_cohesion": random.uniform(0.3, 0.6),
                "danger_threshold": random.uniform(150, 250),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check for danger with graded threat levels
        fish.environment.get_agents_of_type(Crab)
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

        # Dynamic cohesion based on multiple factors (IMPROVED FOOD PRIORITY)
        if threat_level > 0.5:
            # High threat - tight schooling
            cohesion = self.parameters["danger_cohesion"]
        elif energy_ratio < 0.6 and food_opportunity > 0.2:  # Earlier breaking (was 0.4/0.3)
            # Hungry with food nearby - break formation to compete more aggressively
            cohesion = self.parameters["calm_cohesion"] * 0.3  # More independent (was 0.5)
        elif energy_ratio > 0.8:
            # Well-fed and safe - loose exploration
            cohesion = self.parameters["calm_cohesion"] * 0.7
        else:
            # Normal conditions - moderate cohesion
            cohesion = self.parameters["calm_cohesion"]

        allies = [
            f
            for f in fish.environment.get_agents_of_type(FishClass)
            if f != fish and f.species == fish.species
        ]
        if allies:
            # Move toward school center
            center = sum((f.pos for f in allies), Vector2()) / len(allies)
            direction = self._safe_normalize(center - fish.pos)

            vx = direction.x * cohesion
            vy = direction.y * cohesion

            # Add threat response
            if threat_level > 0.3 and nearest_predator:
                avoid_dir = self._safe_normalize(fish.pos - nearest_predator.pos)
                vx += avoid_dir.x * threat_level * 1.5
                vy += avoid_dir.y * threat_level * 1.5

            # Add food seeking when safe and hungry (IMPROVED THRESHOLDS)
            # Seek food earlier (when < 80% energy) and with lower threat tolerance
            if threat_level < 0.4 and energy_ratio < 0.8 and nearest_food:
                food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                hunger = 1.0 - energy_ratio
                # Increased food-seeking strength from 0.7 to 1.2
                food_weight = 1.2 * hunger
                vx += food_dir.x * food_weight
                vy += food_dir.y * food_weight

            # Normalize
            length = math.sqrt(vx * vx + vy * vy)
            if length > 0:
                return vx / length, vy / length

        # No allies - go solo (IMPROVED FOOD SEEKING)
        if threat_level > 0.5 and nearest_predator:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2
        elif energy_ratio < 0.75 and nearest_food:  # Seek food earlier (was 0.5, now 0.75)
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            hunger = 1.0 - energy_ratio
            seek_speed = 0.8 + hunger * 0.4  # More aggressive when hungrier
            return direction.x * seek_speed, direction.y * seek_speed

        return 0, 0
