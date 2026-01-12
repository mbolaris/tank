"""Core simulation contracts and data structures.

This package contains mode-agnostic interfaces for multi-agent simulations.

NOTE: The canonical location for these contracts is now core.brains.contracts.
This module re-exports them for convenience.
"""

# Re-export from new canonical location
from core.brains.contracts import (
    Action,  # Backward-compatibility alias
    ActionMap,
    BrainAction,
    BrainActionMap,
    BrainObservation,
    BrainObservationMap,
    EntityId,
    Observation,
    ObservationMap,
    WorldTickResult,
)

__all__ = [
    # Primary names
    "BrainObservation",
    "BrainAction",
    "BrainObservationMap",
    "BrainActionMap",
    "WorldTickResult",
    "EntityId",
    # Deprecated aliases
    "Observation",
    "Action",
    "ObservationMap",
    "ActionMap",
]
