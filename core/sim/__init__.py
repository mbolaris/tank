"""Core simulation contracts and data structures.

This package contains mode-agnostic interfaces for multi-agent simulations.
"""

from core.sim.contracts import Action, EntityId, Observation, WorldTickResult

__all__ = [
    "Observation",
    "Action",
    "WorldTickResult",
    "EntityId",
]
