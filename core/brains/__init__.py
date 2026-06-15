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
)

__all__ = [
    "BrainObservation",
    "BrainAction",
    "BrainObservationMap",
    "BrainActionMap",
    "WorldTickResult",
    "EntityId",
]
