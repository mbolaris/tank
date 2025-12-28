"""Territory and exploration behavior algorithms.

This module contains 8 algorithms focused on spatial behavior and exploration:
- TerritorialDefender: Defend a territory from other fish
- RandomExplorer: Explore randomly, covering new ground
- WallFollower: Follow along tank walls
- CornerSeeker: Prefer staying in corners
- CenterHugger: Stay near the center of the tank
- RoutePatroller: Patrol between specific waypoints
- BoundaryExplorer: Explore edges and boundaries
- NomadicWanderer: Wander continuously without a home base
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.config.display import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.entities import Crab
from core.entities import Fish as FishClass


@dataclass
class TerritorialDefender(BehaviorAlgorithm):
    """Defend a territory from other fish."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="territorial_defender",
            parameters={
                "territory_radius": rng.uniform(80, 150),
                "aggression": rng.uniform(0.5, 1.0),
            },
            rng=rng,
        )
        self.territory_center = None

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        from core.math_utils import Vector2

        if self.territory_center is None:
            self.territory_center = Vector2(fish.pos.x, fish.pos.y)

        # Performance: Use squared distances to avoid sqrt and Vector2 allocations
        territory_radius_sq = self.parameters["territory_radius"] ** 2
        center_x = self.territory_center.x
        center_y = self.territory_center.y
        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Chase away intruders - use inline distance calculations
        intruders = []
        for f in fish.environment.get_agents_of_type(FishClass):
            if f is fish:
                continue
            dx = f.pos.x - center_x
            dy = f.pos.y - center_y
            if dx * dx + dy * dy < territory_radius_sq:
                intruders.append(f)

        if intruders:
            # Find nearest intruder using squared distance
            min_dist_sq = float('inf')
            nearest = None
            for f in intruders:
                dx = f.pos.x - fish_x
                dy = f.pos.y - fish_y
                dist_sq = dx * dx + dy * dy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest = f

            direction = self._safe_normalize(nearest.pos - fish.pos)
            return (
                direction.x * self.parameters["aggression"],
                direction.y * self.parameters["aggression"],
            )

        # Return to territory center
        direction = self.territory_center - fish.pos
        if direction.length() > self.parameters["territory_radius"]:
            direction = self._safe_normalize(direction)
            return direction.x * 0.5, direction.y * 0.5

        return 0, 0


@dataclass
class RandomExplorer(BehaviorAlgorithm):
    """Explore randomly, covering new ground."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="random_explorer",
            parameters={
                "change_frequency": rng.uniform(0.02, 0.08),
                "exploration_speed": rng.uniform(0.5, 0.9),
            },
            rng=rng,
        )
        self.current_direction = Vector2(rng.uniform(-1, 1), rng.uniform(-1, 1)).normalize()

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        from core.math_utils import Vector2

        # Check for important stimuli
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest_food(fish)

        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Predator avoidance - use squared distance
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            if dx * dx + dy * dy < 14400:  # 120^2
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.2, direction.y * 1.2

        # Food opportunism - use squared distance
        if nearest_food:
            dx = nearest_food.pos.x - fish_x
            dy = nearest_food.pos.y - fish_y
            if dx * dx + dy * dy < 4900:  # 70^2
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 1.0, direction.y * 1.0

        # Boundary avoidance - don't explore into walls
        edge_margin = 60
        avoid_x, avoid_y = 0, 0
        if fish_x < edge_margin:
            avoid_x = 0.5
        elif fish_x > SCREEN_WIDTH - edge_margin:
            avoid_x = -0.5
        if fish_y < edge_margin:
            avoid_y = 0.5
        elif fish_y > SCREEN_HEIGHT - edge_margin:
            avoid_y = -0.5

        # Change direction periodically or when hitting boundaries
        if self.rng.random() < self.parameters["change_frequency"] or (avoid_x != 0 or avoid_y != 0):
            # Bias new direction away from edges
            new_x = self.rng.uniform(-1, 1) + avoid_x
            new_y = self.rng.uniform(-1, 1) + avoid_y
            self.current_direction = self._safe_normalize(Vector2(new_x, new_y))

        # Sometimes explore toward unexplored areas (away from other fish)
        if self.rng.random() < 0.1:
            allies = fish.environment.get_agents_of_type(FishClass)
            if len(allies) > 1:
                # Find average position of other fish using inline math
                sum_x, sum_y, count = 0.0, 0.0, 0
                for f in allies:
                    if f is not fish:
                        sum_x += f.pos.x
                        sum_y += f.pos.y
                        count += 1
                if count > 0:
                    # Explore away from the crowd
                    away_x = fish_x - sum_x / count
                    away_y = fish_y - sum_y / count
                    self.current_direction = self._safe_normalize(Vector2(away_x, away_y))

        return (
            self.current_direction.x * self.parameters["exploration_speed"],
            self.current_direction.y * self.parameters["exploration_speed"],
        )


@dataclass
class WallFollower(BehaviorAlgorithm):
    """Follow along tank walls."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="wall_follower",
            parameters={
                "wall_distance": rng.uniform(20, 60),
                "follow_speed": rng.uniform(0.5, 0.8),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Find nearest wall
        dist_to_left = fish.pos.x
        dist_to_right = SCREEN_WIDTH - fish.pos.x
        dist_to_top = fish.pos.y
        dist_to_bottom = SCREEN_HEIGHT - fish.pos.y

        min_dist = min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)

        # Move parallel to nearest wall
        if min_dist in (dist_to_left, dist_to_right):
            return 0, self.rng.choice([-1, 1]) * self.parameters["follow_speed"]
        else:
            return self.rng.choice([-1, 1]) * self.parameters["follow_speed"], 0


@dataclass
class CornerSeeker(BehaviorAlgorithm):
    """Prefer staying in corners."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="corner_seeker",
            parameters={
                "preferred_corner": rng.choice(
                    ["top_left", "top_right", "bottom_left", "bottom_right"]
                ),
                "approach_speed": rng.uniform(0.4, 0.7),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Determine corner position
        corners = {
            "top_left": Vector2(50, 50),
            "top_right": Vector2(SCREEN_WIDTH - 50, 50),
            "bottom_left": Vector2(50, SCREEN_HEIGHT - 50),
            "bottom_right": Vector2(SCREEN_WIDTH - 50, SCREEN_HEIGHT - 50),
        }

        target = corners[self.parameters["preferred_corner"]]
        direction = self._safe_normalize(target - fish.pos)
        return (
            direction.x * self.parameters["approach_speed"],
            direction.y * self.parameters["approach_speed"],
        )


@dataclass
class CenterHugger(BehaviorAlgorithm):
    """Stay near the center of the tank."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="center_hugger",
            parameters={
                "orbit_radius": rng.uniform(50, 120),
                "return_strength": rng.uniform(0.5, 0.9),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        distance = (center - fish.pos).length()

        if distance > self.parameters["orbit_radius"]:
            direction = self._safe_normalize(center - fish.pos)
            return (
                direction.x * self.parameters["return_strength"],
                direction.y * self.parameters["return_strength"],
            )
        return 0, 0


@dataclass
class RoutePatroller(BehaviorAlgorithm):
    """Patrol between specific waypoints."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="route_patroller",
            parameters={
                "patrol_speed": rng.uniform(0.5, 0.8),
                "waypoint_threshold": rng.uniform(30, 60),
            },
            rng=rng,
        )
        self.waypoints: List[Vector2] = []
        self.current_waypoint_idx = 0
        self.initialized = False

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        if not self.initialized:
            # Create strategic waypoints - cover different areas of tank
            num_waypoints = self.rng.randint(4, 7)
            for i in range(num_waypoints):
                # Distribute waypoints in a pattern
                angle = (2 * math.pi * i) / num_waypoints
                radius = self.rng.uniform(120, 250)
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
        nearest_food = self._find_nearest_food(fish)

        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Interrupt patrol for immediate threats - use squared distance
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            if dx * dx + dy * dy < 10000:  # 100^2
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Interrupt patrol for close food - use squared distance
        if nearest_food:
            dx = nearest_food.pos.x - fish_x
            dy = nearest_food.pos.y - fish_y
            if dx * dx + dy * dy < 3600:  # 60^2
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

        # Continue patrol
        target = self.waypoints[self.current_waypoint_idx]
        target_dx = target.x - fish_x
        target_dy = target.y - fish_y
        distance_sq = target_dx * target_dx + target_dy * target_dy
        threshold_sq = self.parameters["waypoint_threshold"] ** 2

        # Reached waypoint
        if distance_sq < threshold_sq:
            # Look for food near this waypoint before moving on - use squared distance
            if nearest_food:
                food_dx = nearest_food.pos.x - target.x
                food_dy = nearest_food.pos.y - target.y
                if food_dx * food_dx + food_dy * food_dy < 10000:  # 100^2
                    # Food near waypoint - pursue it
                    direction = self._safe_normalize(nearest_food.pos - fish.pos)
                    return (
                        direction.x * self.parameters["patrol_speed"],
                        direction.y * self.parameters["patrol_speed"],
                    )

            # Move to next waypoint
            self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
            target = self.waypoints[self.current_waypoint_idx]
            target_dx = target.x - fish_x
            target_dy = target.y - fish_y
            distance_sq = target_dx * target_dx + target_dy * target_dy

        # Move toward current waypoint
        direction = self._safe_normalize(target - fish.pos)

        # Vary speed based on distance - slow down when approaching
        speed_multiplier = 1.0
        if distance_sq < 6400:  # 80^2
            distance = math.sqrt(distance_sq)
            speed_multiplier = 0.7 + (distance / 80) * 0.3

        return (
            direction.x * self.parameters["patrol_speed"] * speed_multiplier,
            direction.y * self.parameters["patrol_speed"] * speed_multiplier,
        )


@dataclass
class BoundaryExplorer(BehaviorAlgorithm):
    """Explore edges and boundaries."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="boundary_explorer",
            parameters={
                "edge_preference": rng.uniform(0.6, 1.0),
                "exploration_speed": rng.uniform(0.5, 0.8),
            },
            rng=rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Move toward edges
        center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        direction = self._safe_normalize(fish.pos - center)
        return (
            direction.x * self.parameters["exploration_speed"] * self.parameters["edge_preference"],
            direction.y * self.parameters["exploration_speed"] * self.parameters["edge_preference"],
        )


@dataclass
class NomadicWanderer(BehaviorAlgorithm):
    """Wander continuously without a home base."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="nomadic_wanderer",
            parameters={
                "wander_strength": rng.uniform(0.5, 0.9),
                "direction_change_rate": rng.uniform(0.01, 0.05),
            },
            rng=rng,
        )
        self.wander_angle = rng.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check for threats and opportunities
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest_food(fish)

        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Immediate threat response - use squared distance
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            if dx * dx + dy * dy < 12100:  # 110^2
                # Flee but maintain nomadic unpredictability
                base_escape = self._safe_normalize(fish.pos - nearest_predator.pos)
                perp_x, perp_y = -base_escape.y, base_escape.x
                randomness = self.rng.uniform(-0.4, 0.4)
                vx = base_escape.x * 1.0 + perp_x * randomness
                vy = base_escape.y * 1.0 + perp_y * randomness
                return vx, vy

        # Opportunistic food grab - use squared distance
        if nearest_food:
            dx = nearest_food.pos.x - fish_x
            dy = nearest_food.pos.y - fish_y
            if dx * dx + dy * dy < 2500:  # 50^2
                # Close food - grab it
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 1.0, direction.y * 1.0

        # Boundary awareness - avoid getting stuck in corners
        edge_margin = 70
        if (
            fish_x < edge_margin
            or fish_x > SCREEN_WIDTH - edge_margin
            or fish_y < edge_margin
            or fish_y > SCREEN_HEIGHT - edge_margin
        ):
            # Turn toward center - inline calculation
            center_x = SCREEN_WIDTH / 2
            center_y = SCREEN_HEIGHT / 2
            to_center_x = center_x - fish_x
            to_center_y = center_y - fish_y
            # Blend turn toward center with random wandering
            self.wander_angle = math.atan2(to_center_y, to_center_x) + self.rng.gauss(0, 0.3)

        # Gradually change direction with smooth random walk
        angle_change = self.rng.gauss(0, self.parameters["direction_change_rate"])
        self.wander_angle += angle_change

        # Add some Perlin-like noise for more natural wandering
        # Use fish position to add spatial variation
        spatial_influence = math.sin(fish_x * 0.01) * 0.05 + math.cos(fish_y * 0.01) * 0.05
        self.wander_angle += spatial_influence

        vx = math.cos(self.wander_angle) * self.parameters["wander_strength"]
        vy = math.sin(self.wander_angle) * self.parameters["wander_strength"]

        # Energy-based activity
        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < 0.4:
            # Lower energy = more purposeful toward food - use squared distance
            if nearest_food:
                dx = nearest_food.pos.x - fish_x
                dy = nearest_food.pos.y - fish_y
                if dx * dx + dy * dy < 22500:  # 150^2
                    food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                    # Blend wandering with food seeking
                    vx = vx * 0.4 + food_dir.x * 0.6
                    vy = vy * 0.4 + food_dir.y * 0.6

        return vx, vy
