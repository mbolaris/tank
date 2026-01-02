"""Locomotion component for agent movement and navigation.

This component manages an agent's movement mechanics, boundary handling,
and energy costs associated with locomotion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Tuple

if TYPE_CHECKING:
    from core.math_utils import Vector2


class LocomotionComponent:
    """Movement and navigation for agents.

    This component encapsulates:
    - Direction tracking for turn cost calculations
    - Boundary collision handling with optional migration
    - Movement strategy application

    The component is designed to be stateless except for direction tracking,
    making it easy to compose into different agent types.
    """

    def __init__(self) -> None:
        """Initialize locomotion component."""
        self._last_direction: Optional[Vector2] = None

    @property
    def last_direction(self) -> Optional[Vector2]:
        """Get the last recorded movement direction."""
        return self._last_direction

    @last_direction.setter
    def last_direction(self, value: Optional[Vector2]) -> None:
        """Set the last movement direction."""
        self._last_direction = value

    def update_direction(self, velocity: Vector2) -> Optional[Vector2]:
        """Update direction tracking from current velocity.

        Args:
            velocity: Current velocity vector

        Returns:
            Previous direction before update (for turn cost calculation)
        """
        previous = self._last_direction

        if velocity.length_squared() == 0:
            self._last_direction = None
        else:
            self._last_direction = velocity.normalize()

        return previous

    def calculate_turn_cost(
        self,
        previous_direction: Optional[Vector2],
        new_direction: Optional[Vector2],
        size: float,
        base_cost: float,
        size_multiplier: float,
        threshold: float = 0.1,
    ) -> float:
        """Calculate energy cost for a direction change.

        The energy cost increases with:
        - Sharper turns (more angle change)
        - Larger agent size (bigger agents use more energy to turn)

        Args:
            previous_direction: Direction before the turn
            new_direction: Direction after the turn
            size: Agent size multiplier
            base_cost: Base energy cost for turning
            size_multiplier: Exponent for size scaling
            threshold: Minimum turn intensity to apply cost

        Returns:
            Energy cost for this turn (0.0 if no significant turn)
        """
        if previous_direction is None or new_direction is None:
            return 0.0

        # Calculate dot product (-1 = 180° turn, 0 = 90° turn, 1 = no turn)
        dot_product = previous_direction.dot(new_direction)

        # Convert to turn intensity (0 = no turn, 1 = slight turn, 2 = 180° turn)
        turn_intensity = 1.0 - dot_product

        # Only apply cost if there's a noticeable direction change
        if turn_intensity <= threshold:
            return 0.0

        # Base energy cost scaled by turn intensity and agent size
        size_factor = size**size_multiplier
        return base_cost * turn_intensity * size_factor

    def handle_boundaries(
        self,
        pos: Vector2,
        vel: Vector2,
        bounds: Tuple[Tuple[float, float], Tuple[float, float]],
        visual_offsets: Tuple[float, float, float, float],
        top_margin: float = 0.0,
        attempt_migration: Optional[Callable[[str], bool]] = None,
    ) -> Tuple[bool, str]:
        """Handle agent hitting screen/world boundaries.

        Args:
            pos: Agent position (will be modified in place)
            vel: Agent velocity (will be modified in place)
            bounds: ((min_x, min_y), (max_x, max_y)) world bounds
            visual_offsets: (min_x_offset, max_x_offset, min_y_offset, max_y_offset)
            top_margin: Extra margin at top for UI elements
            attempt_migration: Optional callback for migration on boundary hit

        Returns:
            Tuple of (migrated, direction) where migrated is True if agent left
            the world through migration, and direction is "left", "right", or ""
        """
        (env_min_x, env_min_y), (env_max_x, env_max_y) = bounds
        min_x_offset, max_x_offset, min_y_offset, max_y_offset = visual_offsets

        adjusted_min_y = max(env_min_y, top_margin)

        # Horizontal boundaries - check for migration first, then bounce
        if pos.x + min_x_offset < env_min_x:
            if attempt_migration is not None and attempt_migration("left"):
                return (True, "left")
            pos.x = env_min_x - min_x_offset
            vel.x = abs(vel.x)  # Bounce right

        elif pos.x + max_x_offset > env_max_x:
            if attempt_migration is not None and attempt_migration("right"):
                return (True, "right")
            pos.x = env_max_x - max_x_offset
            vel.x = -abs(vel.x)  # Bounce left

        # Vertical boundaries with top margin
        if pos.y + min_y_offset < adjusted_min_y:
            pos.y = adjusted_min_y - min_y_offset
            vel.y = abs(vel.y)  # Bounce down

        elif pos.y + max_y_offset > env_max_y:
            pos.y = env_max_y - max_y_offset
            vel.y = -abs(vel.y)  # Bounce up

        return (False, "")
