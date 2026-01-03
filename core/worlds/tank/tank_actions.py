"""Tank world action translator.

Defines the action space for Tank entities (Fish) and translates
raw actions from external brains to domain Actions.

Action Space:
    - movement: Continuous (vx, vy) target velocity
    - (future) interact: Discrete interaction triggers

The Tank action space is designed for fish movement:
- Velocities are bounded by fish max_speed (typically ±5.0)
- Actions affect the target velocity, not acceleration
"""

from __future__ import annotations

from typing import Any, Dict

from core.actions.action_registry import ActionSpace, register_action_translator
from core.sim.contracts import Action


class TankActionTranslator:
    """Action translator for Tank world.

    Provides action space definition and translation for fish agents.
    """

    def __init__(
        self,
        max_velocity: float = 5.0,
    ) -> None:
        """Initialize the Tank action translator.

        Args:
            max_velocity: Maximum velocity magnitude for fish
        """
        self.max_velocity = max_velocity

    def get_action_space(self) -> ActionSpace:
        """Get the Tank action space descriptor.

        Returns:
            Action space with movement as continuous velocity control
        """
        return {
            "movement": {
                "type": "continuous",
                "shape": (2,),
                "low": (-self.max_velocity, -self.max_velocity),
                "high": (self.max_velocity, self.max_velocity),
                "description": "Target velocity (vx, vy) in pixels/frame",
            },
        }

    def translate_action(self, agent_id: str, raw_action: Any) -> Action:
        """Translate raw action to Tank Action.

        Handles multiple input formats:
        - Action object: pass through
        - dict with "target_velocity" or "velocity": extract velocity
        - tuple/list of 2 floats: treat as (vx, vy)

        Args:
            agent_id: Fish ID as string
            raw_action: Raw action data from external brain

        Returns:
            Action object for the simulation pipeline
        """
        # Pass through if already an Action
        if isinstance(raw_action, Action):
            return raw_action

        # Extract velocity from dict
        if isinstance(raw_action, dict):
            # Support both "target_velocity" and "velocity" keys
            velocity = raw_action.get(
                "target_velocity",
                raw_action.get("velocity", (0.0, 0.0)),
            )
            extra = raw_action.get("extra", {})

            # Ensure velocity is a tuple of floats
            if isinstance(velocity, (list, tuple)) and len(velocity) >= 2:
                vx = self._clamp(float(velocity[0]))
                vy = self._clamp(float(velocity[1]))
            else:
                vx, vy = 0.0, 0.0

            return Action(
                entity_id=agent_id,
                target_velocity=(vx, vy),
                extra=extra,
            )

        # Handle tuple/list directly as velocity
        if isinstance(raw_action, (list, tuple)) and len(raw_action) >= 2:
            vx = self._clamp(float(raw_action[0]))
            vy = self._clamp(float(raw_action[1]))
            return Action(
                entity_id=agent_id,
                target_velocity=(vx, vy),
            )

        # Fallback: no movement
        return Action(entity_id=agent_id, target_velocity=(0.0, 0.0))

    def _clamp(self, value: float) -> float:
        """Clamp velocity component to valid range."""
        return max(-self.max_velocity, min(self.max_velocity, value))


# =============================================================================
# Registration
# =============================================================================

def register_tank_action_translator(world_type: str = "tank") -> None:
    """Register the Tank action translator for the specified world type."""
    translator = TankActionTranslator()
    register_action_translator(world_type, translator)

