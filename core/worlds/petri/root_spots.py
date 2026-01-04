"""Circular root spot manager for Petri dish.

Generates root spots along the circular perimeter of the dish.
"""

import math
import random
from typing import Optional

from core.root_spots import RootSpot, RootSpotManager
from core.worlds.petri.geometry import PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS


class CircularRootSpotManager(RootSpotManager):
    """Manages root spots distributed along a circular perimeter."""

    def _initialize_spots(self, count: int) -> None:
        """Create root spots around the circular dish perimeter.
        
        Args:
            count: Number of spots to create
        """
        # Place spots EXACTLY on the radius.
        # Anchor mode "radial_inward" will handle growing them inward so they don't clip out.
        r = PETRI_RADIUS
        cx = PETRI_CENTER_X
        cy = PETRI_CENTER_Y

        for i in range(count):
            # Distribute evenly around circle
            angle = (2.0 * math.pi * i) / count
            
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            
            spot = RootSpot(spot_id=i, x=x, y=y)
            spot.manager = self
            spot.anchor_mode = "radial_inward"
            spot.angle = angle
            
            self.spots.append(spot)
