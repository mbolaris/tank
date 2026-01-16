"""Behavior execution for fish entities.

This module provides the BehaviorExecutor class which handles:
- Movement strategy execution
- Direction change energy costs
- Poker cooldown management

Design Philosophy:
-----------------
The BehaviorExecutor separates "how the fish behaves" from "what the fish is".
Fish holds the state and properties; BehaviorExecutor coordinates behavior execution.

This separation provides:
- Easier testing of behavior logic in isolation
- Clear ownership of behavior-related state (last_direction, poker_cooldown)
- Single place to modify behavior execution logic
- Reduced complexity in Fish class

Example:
    executor = BehaviorExecutor(movement_strategy)

    # In Fish.update():
    executor.execute(fish, frame_count)
"""

from typing import TYPE_CHECKING, Optional

from core.config.fish import (
    DIRECTION_CHANGE_ENERGY_BASE,
    DIRECTION_CHANGE_SIZE_MULTIPLIER,
)
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities.fish import Fish
    from core.movement_strategy import MovementStrategy


class BehaviorExecutor:
    """Coordinates behavior execution for a fish entity.

    Responsibilities:
        - Execute movement strategy each frame
        - Calculate and apply turn energy costs
        - Track direction changes for energy calculation
        - Manage poker cooldown timer

    Attributes:
        movement_strategy: The movement strategy to execute
        last_direction: Previous frame's normalized velocity (for turn cost)
        poker_cooldown: Frames until fish can play poker again
    """

    def __init__(self, movement_strategy: "MovementStrategy") -> None:
        """Initialize the behavior executor.

        Args:
            movement_strategy: The movement strategy that controls fish movement
        """
        self._movement_strategy = movement_strategy
        self._last_direction: Optional[Vector2] = None
        self._poker_cooldown: int = 0

    @property
    def movement_strategy(self) -> "MovementStrategy":
        """Get the current movement strategy."""
        return self._movement_strategy

    @movement_strategy.setter
    def movement_strategy(self, strategy: "MovementStrategy") -> None:
        """Set the movement strategy."""
        self._movement_strategy = strategy

    @property
    def last_direction(self) -> Optional[Vector2]:
        """Get the last movement direction (for turn cost calculation)."""
        return self._last_direction

    @last_direction.setter
    def last_direction(self, direction: Optional[Vector2]) -> None:
        """Set the last movement direction."""
        self._last_direction = direction

    @property
    def poker_cooldown(self) -> int:
        """Get remaining poker cooldown frames."""
        return self._poker_cooldown

    @poker_cooldown.setter
    def poker_cooldown(self, value: int) -> None:
        """Set poker cooldown frames."""
        self._poker_cooldown = max(0, value)

    def execute(self, fish: "Fish") -> None:
        """Execute one frame of behavior for the fish.

        This method:
        1. Captures previous direction for turn cost calculation
        2. Executes the movement strategy
        3. Applies energy cost for direction changes
        4. Decrements poker cooldown

        Args:
            fish: The fish entity to execute behavior for
        """
        # Capture previous direction before movement
        previous_direction = self._last_direction

        # Execute movement strategy
        self._movement_strategy.move(fish)

        # Apply turn energy cost
        self._apply_turn_energy_cost(fish, previous_direction)

        # Decrement poker cooldown
        if self._poker_cooldown > 0:
            self._poker_cooldown -= 1

    def _apply_turn_energy_cost(
        self, fish: "Fish", previous_direction: Optional[Vector2]
    ) -> None:
        """Apply energy penalty for direction changes.

        The energy cost increases with:
        - Sharper turns (more angle change)
        - Larger fish size (bigger fish use more energy to turn)

        Args:
            fish: The fish to apply the cost to
            previous_direction: The direction before this frame's movement
        """
        if fish.vel.length_squared() == 0:
            self._last_direction = None
            return

        new_direction = fish.vel.normalize()

        if previous_direction is not None:
            # Calculate dot product (-1 = 180° turn, 0 = 90° turn, 1 = no turn)
            dot_product = previous_direction.dot(new_direction)

            # Convert to turn intensity (0 = no turn, 1 = slight turn, 2 = 180° turn)
            turn_intensity = 1 - dot_product

            # Only apply cost if there's a noticeable direction change
            if turn_intensity > 0.1:  # Threshold to ignore tiny wobbles
                # Base energy cost scaled by turn intensity and fish size
                # Access size through lifecycle component
                size = fish._lifecycle_component.size
                size_factor = size ** DIRECTION_CHANGE_SIZE_MULTIPLIER
                energy_cost = DIRECTION_CHANGE_ENERGY_BASE * turn_intensity * size_factor

                fish.energy = max(0, fish.energy - energy_cost)

        self._last_direction = new_direction

    def initialize_direction(self, velocity: Vector2) -> None:
        """Initialize the last direction from current velocity.

        Call this after fish creation to set initial direction.

        Args:
            velocity: The fish's initial velocity
        """
        if velocity.length_squared() > 0:
            self._last_direction = velocity.normalize()
        else:
            self._last_direction = None
