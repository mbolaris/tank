"""Petri dish geometry and physics helpers.

Defines the circular boundary of the Petri dish and provides helper functions
for collision resolution and point generation.
"""

import math
from typing import List, Tuple

from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH

# Geometry constants
# Center the dish in the screen
PETRI_CENTER_X = SCREEN_WIDTH / 2
PETRI_CENTER_Y = SCREEN_HEIGHT / 2

# Radius is half the smaller dimension minus a margin for the rim
PETRI_RIM_MARGIN = 10.0
PETRI_RADIUS = (min(SCREEN_WIDTH, SCREEN_HEIGHT) / 2) - PETRI_RIM_MARGIN


def reflect_velocity(vx: float, vy: float, nx: float, ny: float) -> Tuple[float, float]:
    """Reflect velocity vector v about a unit normal n.
    
    Args:
        vx, vy: Velocity vector components
        nx, ny: Unit normal vector components (pointing inward)
        
    Returns:
        (vx', vy') reflected velocity
    """
    # v' = v - 2*(v·n)*n
    dot = vx * nx + vy * ny
    return (vx - 2.0 * dot * nx, vy - 2.0 * dot * ny)


def circle_perimeter_points(
    cx: float,
    cy: float,
    r: float,
    count: int,
) -> List[Tuple[float, float, float, float]]:
    """Generate points distributed around a circle perimeter.
    
    Args:
        cx, cy: Circle center
        r: Radius
        count: Number of points to generate
        
    Returns:
        List of (x, y, nx, ny) tuples where (nx, ny) is the inward-facing normal
    """
    pts: List[Tuple[float, float, float, float]] = []
    for i in range(count):
        a = (2.0 * math.pi * i) / count
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        # inward normal points toward center
        nx = (cx - x)
        ny = (cy - y)
        inv_len = 1.0 / max(1e-9, math.hypot(nx, ny))
        pts.append((x, y, nx * inv_len, ny * inv_len))
    return pts
