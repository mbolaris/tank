"""Petri world observation builder registration.

Uses the shared TankLikeMovementObservationBuilder configured for Tank-like entities.
"""

from core.entities import Crab, Food
from core.policies.observation_registry import register_observation_builder
from core.worlds.shared.movement_observations import \
    TankLikeMovementObservationBuilder


def register_petri_movement_observation_builder(world_type: str = "petri") -> None:
    """Register the Petri movement observation builder."""
    # Petri uses same entity types as Tank
    builder = TankLikeMovementObservationBuilder(
        food_type=Food,
        threat_type=Crab,
        threat_detection_range=200.0,
    )
    register_observation_builder(world_type, "movement", builder)
