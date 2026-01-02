"""Entity -> snapshot conversion for websocket state payloads.

This module provides backward compatibility for the EntitySnapshotBuilder class.
The actual implementation has been moved to backend.snapshots.tank_snapshot_builder
as part of the world-agnostic backend refactoring.

For new code, import from backend.snapshots directly:
    from backend.snapshots import TankSnapshotBuilder, SnapshotBuilder

This module re-exports the TankSnapshotBuilder as EntitySnapshotBuilder for
compatibility with existing code that imports from this module.
"""

from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder

# Backward compatibility alias
EntitySnapshotBuilder = TankSnapshotBuilder

__all__ = ["EntitySnapshotBuilder"]
