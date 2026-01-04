"""PetriDish value object for Petri mode geometry.

Provides a single source of truth for dish geometry and physics helpers.
All Petri systems should consume this object rather than using global constants.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple, List


@dataclass(frozen=True)
class PetriDish:
    """Immutable value object representing a circular Petri dish.
    
    Attributes:
        cx: Center X coordinate
        cy: Center Y coordinate
        r: Radius of the dish
    """
    cx: float
    cy: float
    r: float

    def contains_circle(self, x: float, y: float, radius: float) -> bool:
        """Check if a circle is fully contained within the dish.
        
        Args:
            x: Center X of the circle to check
            y: Center Y of the circle to check
            radius: Radius of the circle to check
            
        Returns:
            True if the circle is fully inside the dish
        """
        dx = x - self.cx
        dy = y - self.cy
        dist = math.hypot(dx, dy)
        return dist + radius <= self.r

    def clamp_and_reflect(
        self,
        pos_x: float,
        pos_y: float,
        vel_x: float,
        vel_y: float,
        radius: float,
    ) -> Tuple[float, float, float, float, bool]:
        """Clamp a circle inside the dish and reflect velocity if needed.
        
        If the circle extends beyond the dish boundary, it is pushed back in
        and its velocity is reflected off the circular wall.
        
        Args:
            pos_x: Center X of the agent circle
            pos_y: Center Y of the agent circle
            vel_x: Velocity X component
            vel_y: Velocity Y component
            radius: Radius of the agent circle
            
        Returns:
            Tuple of (new_x, new_y, new_vx, new_vy, collided)
        """
        dx = pos_x - self.cx
        dy = pos_y - self.cy
        dist = math.hypot(dx, dy)
        
        # Maximum allowed distance from center for the agent's center
        max_dist = self.r - radius
        
        if max_dist <= 0:
            # Agent is too big for the dish, clamp to center
            return self.cx, self.cy, 0.0, 0.0, True
        
        if dist <= max_dist:
            # No collision
            return pos_x, pos_y, vel_x, vel_y, False
        
        # Collision detected - push back and reflect
        if dist < 0.001:
            # Agent at center but still showing collision (shouldn't happen)
            return pos_x, pos_y, vel_x, vel_y, False
        
        # Calculate inward normal (pointing toward center)
        nx = -dx / dist
        ny = -dy / dist
        
        # Push agent back inside
        overlap = dist - max_dist
        new_x = pos_x + nx * overlap
        new_y = pos_y + ny * overlap
        
        # Reflect velocity if moving outward
        # v dot n < 0 means moving against inward normal (i.e., outward)
        dot = vel_x * nx + vel_y * ny
        if dot < 0:
            # Reflect: v' = v - 2*(v·n)*n
            new_vx = vel_x - 2.0 * dot * nx
            new_vy = vel_y - 2.0 * dot * ny
        else:
            new_vx = vel_x
            new_vy = vel_y
        
        return new_x, new_y, new_vx, new_vy, True

    def sample_point(
        self,
        rng: random.Random,
        margin: float = 0.0,
    ) -> Tuple[float, float]:
        """Sample a uniformly random point inside the dish.
        
        Uses polar coordinates with sqrt(random) for uniform distribution.
        
        Args:
            rng: Random number generator
            margin: Distance to stay away from the edge
            
        Returns:
            Tuple of (x, y) coordinates
        """
        spawn_radius = self.r - margin
        if spawn_radius <= 0:
            return self.cx, self.cy
        
        # Uniform distribution in circle: r = R * sqrt(uniform)
        r = spawn_radius * math.sqrt(rng.random())
        theta = rng.random() * 2.0 * math.pi
        
        x = self.cx + r * math.cos(theta)
        y = self.cy + r * math.sin(theta)
        
        return x, y

    def perimeter_points(self, count: int) -> List[Tuple[float, float, float]]:
        """Generate evenly distributed points on the dish perimeter.
        
        Args:
            count: Number of points to generate
            
        Returns:
            List of (x, y, angle) tuples where angle is in radians
        """
        if count <= 0:
            return []
        
        pts: List[Tuple[float, float, float]] = []
        for i in range(count):
            angle = (2.0 * math.pi * i) / count
            x = self.cx + self.r * math.cos(angle)
            y = self.cy + self.r * math.sin(angle)
            pts.append((x, y, angle))
        
        return pts
