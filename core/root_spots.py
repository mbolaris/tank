"""Root spot management for fractal plants.

This module manages the 100 fixed positions along the tank bottom
where fractal plants can sprout and grow.
"""

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH

if TYPE_CHECKING:
    from core.entities.fractal_plant import FractalPlant


# Root spot configuration
ROOT_SPOT_COUNT = 100
ROOT_SPOT_Y_BASE = SCREEN_HEIGHT - 40  # Position near tank bottom
ROOT_SPOT_Y_VARIANCE = 8  # Slight y variation for natural look
ROOT_SPOT_MIN_SPACING = 8  # Minimum pixels between spots


@dataclass
class RootSpot:
    """A single position where a fractal plant can grow.

    Attributes:
        spot_id: Unique identifier for this spot
        x: X position in tank
        y: Y position in tank (near bottom)
        occupied: Whether a plant is currently growing here
        occupant: Reference to the plant occupying this spot
    """

    spot_id: int
    x: float
    y: float
    occupied: bool = False
    occupant: Optional["FractalPlant"] = field(default=None, repr=False)

    def claim(self, plant: "FractalPlant") -> bool:
        """Claim this spot for a plant.

        Args:
            plant: The plant to place here

        Returns:
            True if successfully claimed, False if already occupied
        """
        if self.occupied:
            return False
        self.occupied = True
        self.occupant = plant
        return True

    def release(self) -> None:
        """Release this spot when a plant dies."""
        self.occupied = False
        self.occupant = None


class RootSpotManager:
    """Manages all root spots in the tank.

    Handles allocation, deallocation, and queries for root spots
    where fractal plants can grow.
    """

    def __init__(
        self,
        screen_width: int = SCREEN_WIDTH,
        screen_height: int = SCREEN_HEIGHT,
        spot_count: int = ROOT_SPOT_COUNT,
    ):
        """Initialize root spot manager.

        Args:
            screen_width: Tank width in pixels
            screen_height: Tank height in pixels
            spot_count: Number of root spots to create
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.spots: List[RootSpot] = []
        self._initialize_spots(spot_count)

    def _initialize_spots(self, count: int) -> None:
        """Create all root spots distributed along tank bottom.

        Args:
            count: Number of spots to create
        """
        # Calculate spacing to distribute spots evenly
        margin = 20  # Margin from tank edges
        available_width = self.screen_width - (2 * margin)
        spacing = available_width / (count - 1) if count > 1 else 0

        for i in range(count):
            x = margin + (i * spacing)
            # Add slight random variation to y for natural look
            y_offset = random.uniform(-ROOT_SPOT_Y_VARIANCE, ROOT_SPOT_Y_VARIANCE)
            y = ROOT_SPOT_Y_BASE + y_offset

            spot = RootSpot(spot_id=i, x=x, y=y)
            self.spots.append(spot)

    def get_random_empty_spot(self) -> Optional[RootSpot]:
        """Get a random unoccupied spot.

        Returns:
            Random empty RootSpot, or None if all spots are occupied
        """
        empty_spots = [s for s in self.spots if not s.occupied]
        if not empty_spots:
            return None
        return random.choice(empty_spots)

    def get_nearest_empty_spot(self, x: float, y: float) -> Optional[RootSpot]:
        """Get the nearest unoccupied spot to a position.

        Args:
            x: X position to search from
            y: Y position to search from

        Returns:
            Nearest empty RootSpot, or None if all occupied
        """
        empty_spots = [s for s in self.spots if not s.occupied]
        if not empty_spots:
            return None

        def distance_sq(spot: RootSpot) -> float:
            dx = spot.x - x
            dy = spot.y - y
            return dx * dx + dy * dy

        return min(empty_spots, key=distance_sq)

    def get_spot_by_id(self, spot_id: int) -> Optional[RootSpot]:
        """Get a spot by its ID.

        Args:
            spot_id: The spot's unique identifier

        Returns:
            The RootSpot, or None if not found
        """
        if 0 <= spot_id < len(self.spots):
            return self.spots[spot_id]
        return None

    def claim_spot(self, spot_id: int, plant: "FractalPlant") -> bool:
        """Claim a specific spot for a plant.

        Args:
            spot_id: ID of the spot to claim
            plant: The plant to place

        Returns:
            True if successfully claimed
        """
        spot = self.get_spot_by_id(spot_id)
        if spot is None:
            return False
        return spot.claim(plant)

    def release_spot(self, spot_id: int) -> None:
        """Release a spot when its plant dies.

        Args:
            spot_id: ID of the spot to release
        """
        spot = self.get_spot_by_id(spot_id)
        if spot is not None:
            spot.release()

    def get_occupied_count(self) -> int:
        """Get number of occupied spots.

        Returns:
            Count of spots with plants
        """
        return sum(1 for s in self.spots if s.occupied)

    def get_empty_count(self) -> int:
        """Get number of empty spots.

        Returns:
            Count of available spots
        """
        return sum(1 for s in self.spots if not s.occupied)

    def get_occupancy_ratio(self) -> float:
        """Get ratio of occupied to total spots.

        Returns:
            Occupancy ratio (0.0 to 1.0)
        """
        if not self.spots:
            return 0.0
        return self.get_occupied_count() / len(self.spots)

    def get_all_occupied_spots(self) -> List[RootSpot]:
        """Get all spots that have plants.

        Returns:
            List of occupied RootSpots
        """
        return [s for s in self.spots if s.occupied]

    def get_all_empty_spots(self) -> List[RootSpot]:
        """Get all available spots.

        Returns:
            List of empty RootSpots
        """
        return [s for s in self.spots if not s.occupied]

    def get_spots_in_range(
        self, x: float, y: float, radius: float, only_empty: bool = False
    ) -> List[RootSpot]:
        """Get all spots within a radius of a position.

        Args:
            x: Center X position
            y: Center Y position
            radius: Search radius in pixels
            only_empty: If True, only return unoccupied spots

        Returns:
            List of spots within range
        """
        radius_sq = radius * radius
        result = []

        for spot in self.spots:
            if only_empty and spot.occupied:
                continue
            dx = spot.x - x
            dy = spot.y - y
            if dx * dx + dy * dy <= radius_sq:
                result.append(spot)

        return result

    def find_spot_for_sprouting(
        self, parent_x: float, parent_y: float, max_distance: float = 200.0
    ) -> Optional[RootSpot]:
        """Find a suitable spot for a new plant to sprout.

        Prefers spots near the parent plant but not too close.

        Args:
            parent_x: Parent plant X position
            parent_y: Parent plant Y position
            max_distance: Maximum distance from parent

        Returns:
            Suitable RootSpot for sprouting, or None
        """
        # First try to find spots within preferred range
        nearby_spots = self.get_spots_in_range(
            parent_x, parent_y, max_distance, only_empty=True
        )

        if nearby_spots:
            # Prefer spots at medium distance (not too close, not too far)
            min_preferred_distance = 50.0

            def score_spot(spot: RootSpot) -> float:
                dx = spot.x - parent_x
                dy = spot.y - parent_y
                dist = (dx * dx + dy * dy) ** 0.5
                # Score higher for medium distances
                if dist < min_preferred_distance:
                    return dist  # Too close, lower score
                return min_preferred_distance + (max_distance - dist) * 0.5

            # Sort by score and pick from top candidates with some randomness
            nearby_spots.sort(key=score_spot, reverse=True)
            top_candidates = nearby_spots[: min(5, len(nearby_spots))]
            return random.choice(top_candidates)

        # Fall back to any empty spot
        return self.get_random_empty_spot()
