"""Tank state schema definition.

This module re-exports the canonical snapshot version from core/contracts.
The version constant is maintained in core/contracts/version.py as the
single source of truth for all schema versioning.
"""

from core.contracts import SNAPSHOT_VERSION

# Re-export as SCHEMA_VERSION for existing code
SCHEMA_VERSION = SNAPSHOT_VERSION
