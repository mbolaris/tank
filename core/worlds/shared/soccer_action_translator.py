"""Soccer action translator for ball-based gameplay modes.

Translates raw agent actions into soccer-specific commands including
movement, kicking, and optional RCSS-Lite physics near the ball.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple
import math

from core.actions.soccer_action import (
    SoccerAction,
    KickCommand,
    MovementMode,
    create_soccer_action,
    clamp_value,
)
from core.actions.action_registry import ActionSpace


class SoccerActionTranslator:
    """Translates raw actions to soccer-specific actions.

    Supports both velocity-based movement and RCSS-Lite style commands
    when agents are near the ball.
    """

    def __init__(
        self,
        max_velocity: float = 5.0,
        max_kick_power: float = 100.0,
        auto_rcss_near_ball: bool = False,
        rcss_activation_distance: float = 50.0,
    ) -> None:
        """Initialize the soccer action translator.

        Args:
            max_velocity: Maximum velocity magnitude for normal movement
            max_kick_power: Maximum kick power value
            auto_rcss_near_ball: Activate RCSS-Lite mode when near ball
            rcss_activation_distance: Distance threshold for RCSS activation
        """
        self.max_velocity = max_velocity
        self.max_kick_power = max_kick_power
        self.auto_rcss_near_ball = auto_rcss_near_ball
        self.rcss_activation_distance = rcss_activation_distance

    def get_action_space(self) -> ActionSpace:
        """Get the soccer action space descriptor.

        Returns:
            Action space definition for external agents
        """
        return {
            "movement": {
                "type": "continuous",
                "shape": (2,),
                "low": (-self.max_velocity, -self.max_velocity),
                "high": (self.max_velocity, self.max_velocity),
                "description": "Target velocity (vx, vy) in pixels/frame",
            },
            "kick": {
                "type": "continuous",
                "shape": (2,),
                "low": (0.0, -math.pi),
                "high": (self.max_kick_power, math.pi),
                "description": "Kick power [0-100] and direction [radians]",
            },
            "rcss_mode": {
                "type": "discrete",
                "values": ["normal", "rcss_lite", "auto"],
                "description": "Movement mode: normal velocity or RCSS-Lite physics",
            },
        }

    def translate_action(self, agent_id: str, raw_action: Any) -> SoccerAction:
        """Translate raw action to SoccerAction.

        Supports multiple input formats:
        - SoccerAction: pass through
        - dict with movement/kick/mode keys
        - tuple/list with velocity and kick info

        Args:
            agent_id: Agent ID as string
            raw_action: Raw action from external brain

        Returns:
            SoccerAction instance
        """
        # Pass through if already a SoccerAction
        if isinstance(raw_action, SoccerAction):
            return raw_action

        # Default values
        target_velocity: Tuple[float, float] = (0.0, 0.0)
        kick_power: Optional[float] = None
        kick_direction: Optional[float] = None
        movement_mode = MovementMode.NORMAL

        # Extract from dict
        if isinstance(raw_action, dict):
            # Movement
            velocity = raw_action.get("movement", raw_action.get("velocity", (0.0, 0.0)))
            if isinstance(velocity, (list, tuple)) and len(velocity) >= 2:
                vx = clamp_value(float(velocity[0]), -self.max_velocity, self.max_velocity)
                vy = clamp_value(float(velocity[1]), -self.max_velocity, self.max_velocity)
                target_velocity = (vx, vy)

            # Kick
            kick = raw_action.get("kick", None)
            if kick is not None:
                if isinstance(kick, (list, tuple)) and len(kick) >= 2:
                    kick_power = clamp_value(float(kick[0]), 0.0, self.max_kick_power)
                    kick_direction = float(kick[1])
                elif isinstance(kick, dict):
                    kick_power = clamp_value(
                        float(kick.get("power", 0)), 0.0, self.max_kick_power
                    )
                    kick_direction = float(kick.get("direction", 0))

            # Movement mode
            mode_str = raw_action.get("rcss_mode", "normal")
            if mode_str == "rcss_lite":
                movement_mode = MovementMode.RCSS_LITE
            elif mode_str == "auto":
                # Auto will be determined by proximity (handled by agent/world)
                movement_mode = MovementMode.NORMAL  # Default, updated at apply time

        # Handle tuple/list format: (vx, vy) or (vx, vy, kick_power, kick_dir)
        elif isinstance(raw_action, (list, tuple)):
            if len(raw_action) >= 2:
                vx = clamp_value(float(raw_action[0]), -self.max_velocity, self.max_velocity)
                vy = clamp_value(float(raw_action[1]), -self.max_velocity, self.max_velocity)
                target_velocity = (vx, vy)

            if len(raw_action) >= 4:
                kick_power = clamp_value(float(raw_action[2]), 0.0, self.max_kick_power)
                kick_direction = float(raw_action[3])

        return create_soccer_action(
            entity_id=agent_id,
            target_velocity=target_velocity,
            kick_power=kick_power,
            kick_direction=kick_direction,
            movement_mode=movement_mode,
        )

    def determine_movement_mode(
        self,
        agent_id: str,
        requested_mode: MovementMode,
        distance_to_ball: Optional[float] = None,
    ) -> MovementMode:
        """Determine the actual movement mode based on context.

        Args:
            agent_id: Agent identifier
            requested_mode: Mode requested in action
            distance_to_ball: Distance to ball (if available)

        Returns:
            Final movement mode to use
        """
        if requested_mode == MovementMode.RCSS_LITE:
            return MovementMode.RCSS_LITE

        if self.auto_rcss_near_ball and distance_to_ball is not None:
            if distance_to_ball <= self.rcss_activation_distance:
                return MovementMode.RCSS_LITE

        return MovementMode.NORMAL
