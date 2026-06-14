"""Schema version constant and validation for TankWorld persistence.

This module is the single source of truth for the **snapshot/persistence**
schema version -- the one cross-cutting contract that decides whether a saved
world can be loaded. Other subsystems version their own payloads independently
and validate them at their own boundaries:

    - Genome serialization: ``GENOME_SCHEMA_VERSION`` (``core.genetics``)
    - WebSocket state payloads: ``STATE_SCHEMA_VERSION`` (``backend``)

Version Mismatch Policy:
    - Any version mismatch raises a clear error -- no silent inference or
      fallback behaviour.
    - Pre-release policy: old saves are not migrated and will not load.
"""

from __future__ import annotations

from core.exceptions import PersistenceError

# Snapshot/persistence schema version.
# v3.0: Strict schema with explicit contracts.
#   - Every entity carries an explicit "type" field (no type inference).
#   - No legacy id restoration and no field-level migration of old saves.
SNAPSHOT_VERSION = "3.0"


class VersionMismatchError(PersistenceError):
    """Raised when a schema version mismatch is detected.

    Subclasses PersistenceError so it is catchable as part of the TankError
    hierarchy (e.g. ``except PersistenceError``) per ADR-007, while remaining
    catchable as VersionMismatchError for existing handlers.
    """

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
