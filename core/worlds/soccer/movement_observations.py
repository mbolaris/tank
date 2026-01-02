"""Soccer-specific movement observation builder (stub).

This module provides a minimal observation builder for Soccer world movement
policies. It returns a default observation structure that won't crash when
the Soccer world runs.

The builder is registered automatically when this module is imported.
"""

from __future__ import annotations

from typing import Any, Dict

from core.policies.observation_registry import register_observation_builder

Observation = Dict[str, Any]


class SoccerMovementObservationBuilder:
    """Minimal observation builder for Soccer world movement policies.
    
    This is a stub that returns default values. Soccer agents typically use
    the SoccerPolicy interface rather than movement policies, but this ensures
    the observation registry doesn't crash if movement observation is requested.
    """

    def build(self, agent: Any, env: Any) -> Observation:
        """Build a minimal movement observation for soccer agents."""
        # Soccer agents may have different attributes than Fish
        pos = getattr(agent, "pos", None)
        vel = getattr(agent, "vel", None)
        
        pos_x = getattr(pos, "x", 0.0) if pos else 0.0
        pos_y = getattr(pos, "y", 0.0) if pos else 0.0
        vel_x = getattr(vel, "x", 0.0) if vel else 0.0
        vel_y = getattr(vel, "y", 0.0) if vel else 0.0
        
        return {
            "position": {"x": pos_x, "y": pos_y},
            "velocity": {"x": vel_x, "y": vel_y},
            "nearest_food_vector": {"x": 0.0, "y": 0.0},  # N/A for soccer
            "nearest_threat_vector": {"x": 0.0, "y": 0.0},  # N/A for soccer
            "energy": getattr(agent, "stamina", 1.0),  # Soccer uses stamina
            "age": 0,  # N/A for soccer
            "can_play_poker": False,  # N/A for soccer
        }


# =============================================================================
# Auto-registration
# =============================================================================

_soccer_movement_builder = SoccerMovementObservationBuilder()
register_observation_builder("soccer", "movement", _soccer_movement_builder)
register_observation_builder("soccer_training", "movement", _soccer_movement_builder)
