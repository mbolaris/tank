from __future__ import annotations

"""Contract version constants for TankWorld.

This module defines the single source of truth for all schema versions
used in persistence, WebSocket payloads, and entity transfer.

Version Mismatch Policy:
    - Any version mismatch should raise a clear error
    - No silent inference or fallback behavior
    - Pre-release policy: old saves may not load
"""

# Snapshot/persistence schema version
# v3.0: Strict schema, no legacy compatibility
#   - All entities must have explicit "type" field
#   - No entity type inference
#   - No legacy ID restoration
SNAPSHOT_VERSION = "3.0"

# WebSocket world update payload version
# v1.0: WorldUpdateV1 unified contract
WS_PAYLOAD_VERSION = "1.0"

# Entity transfer/serialization version
# v1.0: Full genome_data, explicit type, motion state
ENTITY_TRANSFER_VERSION = "1.0"


class VersionMismatchError(Exception):
    """Raised when a schema version mismatch is detected."""

    def __init__(self, expected: str, actual: str, context: str = ""):
        self.expected = expected
        self.actual = actual
        self.context = context
        msg = f"Version mismatch: expected {expected}, got {actual}"
        if context:
            msg += f" ({context})"
        super().__init__(msg)


def validate_snapshot_version(version: str | None) -> None:
    """Validate snapshot version, raising on mismatch.

    Args:
        version: Version string from snapshot, or None if missing

    Raises:
        VersionMismatchError: If version doesn't match SNAPSHOT_VERSION
    """
    if version is None:
        raise VersionMismatchError(
            SNAPSHOT_VERSION,
            "None",
            "Snapshot missing version field - likely from pre-v3.0",
        )
    if version != SNAPSHOT_VERSION:
        raise VersionMismatchError(SNAPSHOT_VERSION, version, "Snapshot version incompatible")
