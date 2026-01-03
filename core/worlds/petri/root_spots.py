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
        # Place spots slightly inside the radius so plants aren't half-clipped
        # Determine strict or loose placement?
        # User requested: "plants anchored to dish perimeter"
        # We'll put them on the radius but maybe inset slightly
        inset = 5.0
        r = PETRI_RADIUS - inset
        cx = PETRI_CENTER_X
        cy = PETRI_CENTER_Y

        for i in range(count):
            # Distribute evenly around circle
            angle = (2.0 * math.pi * i) / count
            
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            
            spot = RootSpot(spot_id=i, x=x, y=y)
            spot.manager = self
            # Use 'center' anchor so plant center is on the perimeter?
            # Or rotated?
            # User suggested: "root_spot.anchor_mode: Literal['bottom', 'center']"
            # If we use 'center', the plant grows out from that center point in all directions?
            # Plants in tank currently grow UP.
            # In Petri top-down, "up" is just -Y. But plants are now 2D top-down blobs or still trees?
            # Plants are drawn as "Colony" circles in top-down renderer.
            # So 'center' anchoring makes perfect sense for top-down blobs.
            spot.anchor_mode = "center"
            
            self.spots.append(spot)
