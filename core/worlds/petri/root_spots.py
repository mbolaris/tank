"""Circular root spot manager for Petri dish.

Generates root spots along the circular perimeter of the dish.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Optional

from core.root_spots import RootSpot, RootSpotManager

if TYPE_CHECKING:
    from core.worlds.petri.dish import PetriDish


class CircularRootSpotManager(RootSpotManager):
    """Manages root spots distributed along a circular perimeter."""

    def __init__(
        self,
        dish: "PetriDish",
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize with dish geometry.

        Args:
            dish: PetriDish object defining the circular boundary
            rng: Random number generator (optional)
        """
        self.dish = dish
        # Calculate appropriate spot count for the circumference to match Tank density
        # Tank: ~25 spots / 1088px width ~= 43px spacing
        # Petri: Use 45px spacing as a reasonable target
        circumference = 2 * math.pi * dish.r
        target_spacing = 45.0
        calculated_count = max(20, int(circumference / target_spacing))

        super().__init__(
            screen_width=int(dish.cx * 2),
            screen_height=int(dish.cy * 2),
            spot_count=calculated_count,
            rng=rng,
        )

    def _initialize_spots(self, count: int) -> None:
        """Create root spots around the circular dish perimeter.

        Args:
            count: Number of spots to create
        """
        # Use dish.perimeter_points to get evenly distributed points
        perimeter = self.dish.perimeter_points(count)

        for i, (x, y, angle) in enumerate(perimeter):
            spot = RootSpot(spot_id=i, x=x, y=y)
            spot.manager = self
            spot.anchor_mode = "radial_inward"
            spot.angle = angle

            self.spots.append(spot)
