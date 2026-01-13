"""Soccer action and command types for ball-based gameplay.

This module defines actions specific to soccer/sports gameplay,
extending the basic movement actions with kick commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MovementMode(Enum):
    """Movement modes for agents near the ball."""

    NORMAL = "normal"  # Standard tank movement
    RCSS_LITE = "rcss_lite"  # RCSS-Lite physics when near ball


@dataclass
class KickCommand:
    """Command to kick the ball.

    Attributes:
        power: Kick power [0-100]
        direction: Kick direction in radians (relative to agent body angle)
        relative_to_body: If True, direction is relative to agent facing angle
    """

    power: float  # [0-100]
    direction: float  # Radians or angle
    relative_to_body: bool = True  # Direction relative to agent facing


@dataclass
class SoccerAction:
    """Soccer-specific action combining movement and ball interaction.

    Attributes:
        entity_id: Agent ID
        movement_mode: Movement physics to use (normal or RCSS-Lite)
        target_velocity: Desired velocity (for normal mode)
        dash_command: RCSS-Lite dash command (power, direction)
        turn_command: RCSS-Lite turn command (moment in degrees)
        kick_command: Ball kick command if applicable
        extra: Additional data for extensibility
    """

    entity_id: str
    movement_mode: MovementMode = MovementMode.NORMAL
    target_velocity: tuple[float, float] = (0.0, 0.0)  # For normal mode
    dash_command: tuple[float, float] | None = None  # (power, direction) for RCSS-Lite
    turn_command: float | None = None  # Moment (degrees) for RCSS-Lite
    kick_command: KickCommand | None = None  # Ball kick
    extra: dict = field(default_factory=dict)


def create_soccer_action(
    entity_id: str,
    target_velocity: tuple[float, float] = (0.0, 0.0),
    kick_power: float | None = None,
    kick_direction: float | None = None,
    movement_mode: MovementMode = MovementMode.NORMAL,
) -> SoccerAction:
    """Factory function to create a soccer action.

    Args:
        entity_id: Agent identifier
        target_velocity: Target velocity (vx, vy)
        kick_power: Kick power [0-100], or None to skip kick
        kick_direction: Kick direction (radians), or None to use agent facing
        movement_mode: Which physics model to use

    Returns:
        SoccerAction instance
    """
    kick_cmd = None
    if kick_power is not None and kick_power > 0:
        kick_direction = kick_direction if kick_direction is not None else 0.0
        kick_cmd = KickCommand(power=kick_power, direction=kick_direction)

    return SoccerAction(
        entity_id=entity_id,
        movement_mode=movement_mode,
        target_velocity=target_velocity,
        kick_command=kick_cmd,
    )


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value to a range.

    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))
