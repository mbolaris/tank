"""Snapshot builder package for world-agnostic entity serialization.

This package provides:
- SnapshotBuilder: Protocol for building entity snapshots from world entities
- TankSnapshotBuilder: Implementation for tank world (Fish, Plant, Crab, etc.)

Other world implementations (Petri, Soccer) will add their own snapshot builders.
"""

from backend.snapshots.interfaces import SnapshotBuilder
from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder

__all__ = ["SnapshotBuilder", "TankSnapshotBuilder"]
