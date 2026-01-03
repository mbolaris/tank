"""Petri world observation builder registration.

Allows Petri mode to register contracts without importing Tank wiring directly.
"""
from core.worlds.tank.movement_observations import TankMovementObservationBuilder
from core.policies.observation_registry import register_observation_builder

def register_petri_movement_observation_builder(world_type: str = "petri") -> None:
    """Register the Petri movement observation builder."""
    # Petri reuses Tank observations for now
    builder = TankMovementObservationBuilder()
    register_observation_builder(world_type, "movement", builder)
