"""Save/restore for the telemetry stores a ``SimulationRunner`` carries.

Metrics history, Board commentary, and story events are all the same shape from
the persistence layer's point of view: an optional attribute on the runner with
``to_payload()`` / ``load()``. Listing them once here keeps
``backend.world_persistence`` from growing another near-identical block every
time a store is added.

These stores hold *telemetry about* a world, never simulation state, so a
missing or unreadable payload is never fatal — the store just starts empty.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ``(runner attribute, snapshot key)``. The snapshot keys are a persisted
# format: rename one only with a migration.
RUNNER_STORES: tuple[tuple[str, str], ...] = (
    ("metrics_history", "metrics_history"),
    ("commentary", "commentary"),
    ("story_events", "story_events"),
)


def capture_runner_stores(runner: Any, snapshot: dict[str, Any]) -> None:
    """Write each present store's payload into ``snapshot`` in place."""
    for attr, key in RUNNER_STORES:
        store = getattr(runner, attr, None)
        if store is not None:
            snapshot[key] = store.to_payload()


def restore_runner_stores(runner: Any, snapshot: dict[str, Any]) -> None:
    """Load each store from ``snapshot``, skipping the ones it has no data for."""
    if runner is None:
        return
    for attr, key in RUNNER_STORES:
        store = getattr(runner, attr, None)
        if store is not None and key in snapshot:
            store.load(snapshot[key])


def rebind_runner_stores(runner: Any, world_id: str) -> None:
    """Point every store at ``world_id`` after a world is restored or renamed."""
    for attr, _key in RUNNER_STORES:
        store = getattr(runner, attr, None)
        if store is not None:
            store.world_id = world_id
