"""Core simulation contracts and data structures.

This package contains mode-agnostic interfaces for multi-agent simulations.

NOTE: The canonical location for these contracts is now core.brains.contracts.
This module re-exports them for backward compatibility.
"""

# Re-export from new canonical location
from core.brains.contracts import (
    # Backward-compatibility aliases
    Action,
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
    # Backward-compatibility (deprecated)
    "Observation",
    "Action",
    "ObservationMap",
    "ActionMap",
]
