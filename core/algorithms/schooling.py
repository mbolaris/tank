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
from typing import List, Tuple

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.entities import Crab
from core.entities import Fish as FishClass


def _get_nearby_fish(fish: "FishClass", radius: float) -> List["FishClass"]:
    """Get nearby fish using the fastest available spatial query method.
    
    OPTIMIZATION: Use dedicated nearby_fish method when available (faster).
    """
    env = fish.environment
    nearby = []
    if hasattr(env, "nearby_fish"):
        nearby = env.nearby_fish(fish, radius)
    else:
        nearby = env.nearby_agents_by_type(fish, radius, FishClass)
    
    # Filter out dead or migrated fish
    # This prevents "ghost attraction" where fish school towards empty spots
    return [f for f in nearby if not f.is_dead()]


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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Tight schoolers stay close, so use a moderate radius
        QUERY_RADIUS = 200
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]
        if allies:
            # OPTIMIZATION: Inline center calculation to avoid Vector2.__add__ overhead
            center_x, center_y = 0.0, 0.0
            for f in allies:
                center_x += f.pos.x
                center_y += f.pos.y
            n = len(allies)
            center_x /= n
            center_y /= n
            direction = self._safe_normalize(Vector2(center_x - fish.pos.x, center_y - fish.pos.y))
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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Loose schoolers maintain distance, so use a larger radius
        QUERY_RADIUS = 300
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]
        if allies:
            # OPTIMIZATION: Inline center calculation to avoid Vector2.__add__ overhead
            center_x, center_y = 0.0, 0.0
            for f in allies:
                center_x += f.pos.x
                center_y += f.pos.y
            n = len(allies)
            center_x /= n
            center_y /= n
            fish_x, fish_y = fish.pos.x, fish.pos.y
            dx, dy = center_x - fish_x, center_y - fish_y
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > self.parameters["max_distance"]:
                direction = self._safe_normalize(Vector2(dx, dy))
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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Query a bit beyond max_follow_distance to find potential leaders
        QUERY_RADIUS = 250
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
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
        # Use spatial query with alignment_radius (O(N) instead of O(N²))
        # This eliminates the double O(N²) problem: get_all + distance_filter
        allies = [
            f
            for f in _get_nearby_fish(fish, int(self.parameters["alignment_radius"]))
            if f.species == fish.species
        ]

        if allies:
            # OPTIMIZATION: Inline average velocity calculation
            avg_vel_x, avg_vel_y = 0.0, 0.0
            for f in allies:
                avg_vel_x += f.vel.x
                avg_vel_y += f.vel.y
            n = len(allies)
            avg_vel_x /= n
            avg_vel_y /= n
            avg_vel_len = (avg_vel_x * avg_vel_x + avg_vel_y * avg_vel_y) ** 0.5
            if avg_vel_len > 0:
                avg_vel_x /= avg_vel_len
                avg_vel_y /= avg_vel_len
                return (
                    avg_vel_x * self.parameters["alignment_strength"],
                    avg_vel_y * self.parameters["alignment_strength"],
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
        # Use spatial query with min_distance (O(N) instead of O(N²))
        # Only check fish within separation range
        QUERY_RADIUS = int(self.parameters["min_distance"] * 1.5)
        allies = _get_nearby_fish(fish, QUERY_RADIUS)

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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Front runners lead from ahead, check reasonable radius
        QUERY_RADIUS = 250
        # Move in a consistent direction
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]
        if allies:
            # OPTIMIZATION: Inline center calculation
            center_x, center_y = 0.0, 0.0
            for f in allies:
                center_x += f.pos.x
                center_y += f.pos.y
            n = len(allies)
            center_x /= n
            center_y /= n
            # Move away from center to lead
            direction = self._safe_normalize(Vector2(fish.pos.x - center_x, fish.pos.y - center_y))
            return (
                direction.x * self.parameters["leadership_strength"],
                direction.y * self.parameters["leadership_strength"],
            )

        # If alone, move in a random direction
        angle = random.random() * 6.283185307
        speed = self.parameters["independence"]
        return speed * math.cos(angle), speed * math.sin(angle)


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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Query beyond orbit_radius to find the school center
        QUERY_RADIUS = int(self.parameters["orbit_radius"] * 2)
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]
        if allies:
            # OPTIMIZATION: Inline center calculation
            center_x, center_y = 0.0, 0.0
            for f in allies:
                center_x += f.pos.x
                center_y += f.pos.y
            n = len(allies)
            center_x /= n
            center_y /= n
            fish_x, fish_y = fish.pos.x, fish.pos.y
            to_center_x = center_x - fish_x
            to_center_y = center_y - fish_y
            distance = (to_center_x * to_center_x + to_center_y * to_center_y) ** 0.5

            if distance < self.parameters["orbit_radius"]:
                # Move away from center
                if distance > 0.001:
                    dir_x = -to_center_x / distance
                    dir_y = -to_center_y / distance
                else:
                    dir_x, dir_y = 1.0, 0.0
                return (
                    dir_x * self.parameters["orbit_speed"],
                    dir_y * self.parameters["orbit_speed"],
                )
            elif distance > self.parameters["orbit_radius"] * 1.3:
                # Move toward center
                if distance > 0.001:
                    dir_x = to_center_x / distance
                    dir_y = to_center_y / distance
                else:
                    dir_x, dir_y = 1.0, 0.0
                return (
                    dir_x * self.parameters["orbit_speed"],
                    dir_y * self.parameters["orbit_speed"],
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
        # Use spatial query with mirror_distance (O(N) instead of O(N²))
        # This eliminates the double O(N²) problem: get_all + distance_filter
        allies = _get_nearby_fish(fish, int(self.parameters["mirror_distance"]))

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
        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Use 200 radius to match predator detection range and boid interaction range
        QUERY_RADIUS = 200
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]

        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Check for predators - school tightens when threatened (use squared distance)
        nearest_predator = self._find_nearest(fish, Crab)
        predator_dist_sq = float("inf")
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            predator_dist_sq = dx * dx + dy * dy
        in_danger = predator_dist_sq < 40000  # 200^2

        # Check for food opportunities (use squared distance)
        nearest_food = self._find_nearest_food(fish)
        food_dist_sq = float("inf")
        if nearest_food:
            dx = nearest_food.pos.x - fish_x
            dy = nearest_food.pos.y - fish_y
            food_dist_sq = dx * dx + dy * dy
        food_nearby = food_dist_sq < 10000  # 100^2

        if not allies:
            # Alone - seek food or flee
            if in_danger and predator_dist_sq < 22500:  # 150^2
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3
            elif food_nearby:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7
            return 0, 0

        # Allies are already filtered by spatial query (within 200 radius)
        # Further filter to 150 for boid calculations using squared distance
        nearby_allies = []
        for f in allies:
            dx = f.pos.x - fish_x
            dy = f.pos.y - fish_y
            if dx * dx + dy * dy < 22500:  # 150^2
                nearby_allies.append(f)
        if not nearby_allies:
            nearby_allies = allies[:5]  # Use closest 5 if none nearby

        # Separation - avoid crowding
        sep_x, sep_y = 0.0, 0.0
        separation_distance = 40 if in_danger else 50  # Tighter when threatened
        sep_dist_sq = separation_distance * separation_distance
        for ally in nearby_allies:
            dx = ally.pos.x - fish_x
            dy = ally.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if 0 < dist_sq < sep_dist_sq:
                distance = math.sqrt(dist_sq)
                direction = self._safe_normalize(fish.pos - ally.pos)
                # Stronger separation when very close
                strength = (separation_distance - distance) / separation_distance
                sep_x += direction.x * strength / max(distance, 1)
                sep_y += direction.y * strength / max(distance, 1)

        # Alignment - match velocity (use inline sum)
        avg_vel_x, avg_vel_y = 0.0, 0.0
        for f in nearby_allies:
            avg_vel_x += f.vel.x
            avg_vel_y += f.vel.y
        n_allies = len(nearby_allies)
        avg_vel_x /= n_allies
        avg_vel_y /= n_allies
        avg_vel_len = math.sqrt(avg_vel_x * avg_vel_x + avg_vel_y * avg_vel_y)
        if avg_vel_len > 0:
            avg_vel_x /= avg_vel_len
            avg_vel_y /= avg_vel_len
        align_x, align_y = avg_vel_x, avg_vel_y

        # Cohesion - move toward center (use inline sum)
        center_x, center_y = 0.0, 0.0
        for f in nearby_allies:
            center_x += f.pos.x
            center_y += f.pos.y
        center_x /= n_allies
        center_y /= n_allies
        coh_dir = self._safe_normalize(Vector2(center_x - fish_x, center_y - fish_y))

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

        # Add predator avoidance (use squared distance)
        if in_danger and predator_dist_sq < 22500:  # 150^2
            avoid_dir = self._safe_normalize(fish.pos - nearest_predator.pos)
            predator_distance = math.sqrt(predator_dist_sq)
            threat_strength = (150 - predator_distance) / 150
            vx += avoid_dir.x * threat_strength * 2.0
            vy += avoid_dir.y * threat_strength * 2.0

        # Add food attraction for whole school (use squared distance)
        if food_nearby and food_dist_sq < 6400:  # 80^2
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
        nearest_food = self._find_nearest_food(fish)
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

        # Use spatial query to only check nearby fish (O(N) instead of O(N²))
        # Use danger_threshold as radius since that's the maximum interaction range
        QUERY_RADIUS = int(self.parameters["danger_threshold"] * 1.5)
        allies = [
            f
            for f in _get_nearby_fish(fish, QUERY_RADIUS)
            if f.species == fish.species
        ]
        if allies:
            # OPTIMIZATION: Inline center calculation
            center_x, center_y = 0.0, 0.0
            for f in allies:
                center_x += f.pos.x
                center_y += f.pos.y
            n = len(allies)
            center_x /= n
            center_y /= n
            direction = self._safe_normalize(Vector2(center_x - fish.pos.x, center_y - fish.pos.y))

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
