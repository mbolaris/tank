"""Snapshot builder package for world-agnostic entity serialization.

This package provides:
- SnapshotBuilder: Protocol for building entity snapshots from world entities
- TankSnapshotBuilder: Implementation for tank world (Fish, Plant, Crab, etc.)

Petri mode reuses TankSnapshotBuilder with a different view_mode overlay.
Soccer uses a dedicated minigame snapshot path.
"""

from backend.snapshots.interfaces import SnapshotBuilder
from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from backend.snapshots.world_snapshot import WorldSnapshot, WorldUpdatePayload

__all__ = [
    "SnapshotBuilder",
    "TankSnapshotBuilder",
    "WorldSnapshot",
    "WorldUpdatePayload",
]
