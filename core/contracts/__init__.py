"""Contract definitions for TankWorld.

This package owns the snapshot/persistence schema version and its validation.
"""

from core.contracts.version import SNAPSHOT_VERSION, VersionMismatchError, validate_snapshot_version

__all__ = [
    "SNAPSHOT_VERSION",
    "VersionMismatchError",
    "validate_snapshot_version",
]
