"""Brain integration contracts and adapters.

This package contains contracts for external brain/RL integration pipelines.
The contracts here (BrainObservation, BrainAction) are distinct from genome
policy observations which use plain dicts via ObservationRegistry.
"""

from core.brains.contracts import (
    BrainAction,
    BrainActionMap,
    BrainObservation,
    BrainObservationMap,
    EntityId,
    WorldTickResult,
    # Backward-compatibility aliases
    Action,
    ActionMap,
    Observation,
    ObservationMap,
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
