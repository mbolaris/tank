"""The telemetry stores a ``SimulationRunner`` carries: construction and I/O.

Metrics history, Board commentary, story events, and in-world legends are all
the same shape: an attribute on the runner with ``to_payload()`` / ``load()``,
constructed per world. Listing them once here keeps both the runner and
``backend.world_persistence`` from growing a near-identical block every time a
store is added.

These stores hold *telemetry about* a world, never simulation state, so a
missing or unreadable payload is never fatal — the store just starts empty.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.commentary_store import CommentaryStore
from backend.legend_service import LegendService
from backend.metrics_history import MetricsHistory
from backend.story_event_service import StoryEventService

logger = logging.getLogger(__name__)

# ``(runner attribute, snapshot key)``. The snapshot keys are a persisted
# format: rename one only with a migration.
RUNNER_STORES: tuple[tuple[str, str], ...] = (
    ("metrics_history", "metrics_history"),
    ("commentary", "commentary"),
    ("story_events", "story_events"),
    ("legends", "legends"),
)


def init_runner_stores(runner: Any, world_id: str) -> None:
    """Construct every telemetry store on ``runner`` for ``world_id``.

    Used by both ``__init__`` and ``reset()``, which would otherwise drift: a
    store added to one and forgotten in the other survives a reset it should
    not have.
    """
    runner.metrics_history = MetricsHistory(world_id=world_id)
    runner.commentary = CommentaryStore(world_id=world_id)
    runner.story_events = StoryEventService(world_id=world_id)
    runner.legends = LegendService(world_id=world_id)


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
