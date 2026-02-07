"""Tank-specific movement observation builder.

This module provides the Tank-specific observation builder by configuring
the shared TankLikeMovementObservationBuilder with Tank entity types.
"""

from __future__ import annotations

from core.entities import Crab, Food
from core.policies.observation_registry import register_observation_builder
from core.worlds.shared.movement_observations import \
    TankLikeMovementObservationBuilder


class TankMovementObservationBuilder(TankLikeMovementObservationBuilder):
    """Tank-specific observation builder.

    Pre-configured with Tank entity types (Food, Crab).
    This class exists so code can import
    TankMovementObservationBuilder directly from this module.
    """

    def __init__(self) -> None:
        """Initialize with Tank-specific entity types."""
        super().__init__(
            food_type=Food,
            threat_type=Crab,
            threat_detection_range=200.0,
        )


# =============================================================================
# Registration
# =============================================================================


def register_tank_movement_observation_builder(world_type: str = "tank") -> None:
    """Register the tank movement observation builder."""
    builder = TankMovementObservationBuilder()
    register_observation_builder(world_type, "movement", builder)
