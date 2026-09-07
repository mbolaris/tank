"""Structured story events: the deterministic facts a narrative surface renders.

This is the storage/contract half of the story-event service (roadmap item E3 /
U6). The simulation produces *facts* — "population entered danger", "generation
25 reached", "one lineage now holds most of the tank" — and this module records
them in a bounded, monotonically-numbered, persistable buffer that a feed,
timeline, or recap can render without inventing meaning.

It mirrors the service shape of :mod:`backend.metrics_history` and
:mod:`backend.commentary_store`: a bounded per-world store, monotonic ids,
``to_payload`` / ``load`` persistence, and incremental ``since_id`` retrieval for
sparse polling.

**Every stored field is deterministic.** There is deliberately no wall-clock
timestamp: two runs that produce the same samples produce byte-identical event
records, which is what lets a replay or a re-run be compared against a recorded
feed. Clients order events by ``id`` and place them in time with ``frame`` /
``simulation_time``; recaps are computed from the last-seen ``id``
(see E5 in ``docs/EXPERIENCE_ROADMAP.md``).

Detection itself lives in :mod:`backend.story_detectors`; ``StoryEventService``
below is the seam that joins detectors to the store and is what the
``SimulationRunner`` owns.

A stored record (schema v1)::

    {
        "id": int,                  # monotonic, per-store
        "schema_version": int,
        "event_type": str,          # one of EVENT_TYPES
        "frame": int,               # simulation frame the fact was observed at
        "simulation_time": float,   # seconds of simulated time at that frame
        "severity": str,            # one of SEVERITIES (shared with the Board)
        "title": str,               # short deterministic label for a feed row
        "entity_ids": list[int],    # involved entities, capped and sorted
        "lineage_ids": list[str],   # involved founder-lineage ids
        "metrics_before": dict,     # the measurement that preceded the change
        "metrics_after": dict,      # the measurement that triggered it
        "detector_name": str,
        "detector_threshold": dict, # the explicit numbers that fired
        "replay_ref": str | None,   # set only when replay data really exists
    }
"""

from __future__ import annotations

import logging
import threading
from typing import Any

# The Board and the story feed render into the same surface (U7), so they share
# one closed severity vocabulary rather than inventing a parallel one.
from backend.commentary_store import VALID_SEVERITIES

logger = logging.getLogger(__name__)

# Bumped on breaking changes to the record shape above. ``load()`` refuses
# payloads it does not know how to migrate rather than guessing (see below).
SCHEMA_VERSION = 1

SEVERITIES = VALID_SEVERITIES
DEFAULT_SEVERITY = "info"

# The three detectors E3 ships with. Kept a closed set so the UI can rely on it;
# growing it is a deliberate, versioned change, not a drive-by addition.
EVENT_TYPES = (
    "population_danger",
    "population_recovered",
    "generation_milestone",
    "lineage_dominant",
)

# Bounds that keep the buffer small and each poll cheap.
DEFAULT_MAX_EVENTS = 500
MAX_TITLE_LEN = 200
MAX_METRIC_KEYS = 16


def _clean_metrics(metrics: Any) -> dict[str, Any]:
    """Keep a small dict of scalar measurements attached to an event."""
    if not isinstance(metrics, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in metrics.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (int, float, str, bool)) or value is None:
            cleaned[key] = value
        if len(cleaned) >= MAX_METRIC_KEYS:
            break
    return cleaned


def make_event(
    *,
    event_type: str,
    frame: int,
    simulation_time: float,
    severity: str,
    title: str,
    detector_name: str,
    detector_threshold: dict[str, Any] | None = None,
    entity_ids: Any = None,
    lineage_ids: Any = None,
    metrics_before: Any = None,
    metrics_after: Any = None,
    replay_ref: str | None = None,
) -> dict[str, Any]:
    """Build an un-numbered event record with every field normalized.

    Detectors call this so the record shape is defined in exactly one place.
    The ``id`` and ``schema_version`` are stamped by :meth:`StoryEventStore.add`.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown story event_type: {event_type!r}")
    clean_severity = severity if severity in SEVERITIES else DEFAULT_SEVERITY
    return {
        "event_type": event_type,
        "frame": int(frame),
        "simulation_time": round(float(simulation_time), 3),
        "severity": clean_severity,
        "title": (title or event_type).strip()[:MAX_TITLE_LEN],
        "entity_ids": sorted(int(e) for e in (entity_ids or [])),
        "lineage_ids": sorted(str(lid) for lid in (lineage_ids or [])),
        "metrics_before": _clean_metrics(metrics_before),
        "metrics_after": _clean_metrics(metrics_after),
        "detector_name": detector_name,
        "detector_threshold": _clean_metrics(detector_threshold),
        "replay_ref": replay_ref,
    }


class StoryEventStore:
    """Bounded ring buffer of structured story events for a single world."""

    def __init__(
        self,
        world_id: str | None = None,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        self.schema_version = SCHEMA_VERSION
        self.world_id = world_id or "unknown"
        self.max_events = max(1, int(max_events))
        self.events: list[dict[str, Any]] = []
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, event: dict[str, Any]) -> dict[str, Any]:
        """Stamp an event from :func:`make_event` with an id and store it."""
        with self._lock:
            record = dict(event)
            record["id"] = self._next_id
            record["schema_version"] = SCHEMA_VERSION
            self._next_id += 1
            self.events.append(record)

            # Keep the buffer within capacity (drop oldest first). ``_next_id``
            # keeps climbing, so a client polling with ``since_id`` never sees
            # a reused id even after events have scrolled off.
            while len(self.events) > self.max_events:
                self.events.pop(0)
            return record

    def recent(
        self,
        limit: int | None = None,
        since_id: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return stored events, oldest first.

        ``since_id`` returns only events with a larger id (incremental polling);
        ``limit`` caps the result to the most recent N; ``event_type`` filters to
        a single type.
        """
        items = self.events
        if since_id is not None:
            items = [e for e in items if e.get("id", 0) > since_id]
        if event_type is not None:
            items = [e for e in items if e.get("event_type") == event_type]
        if limit is not None and limit >= 0:
            items = items[-limit:]
        return list(items)

    def clear(self) -> int:
        """Drop all events; returns how many were removed. Ids stay monotonic."""
        with self._lock:
            count = len(self.events)
            self.events = []
            return count

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the REST API and for world save/restore."""
        return {
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "max_events": self.max_events,
            "next_id": self._next_id,
            "events": self.events,
        }

    def load(self, payload: dict[str, Any] | None) -> bool:
        """Restore from a payload. Returns True when events were adopted.

        Unknown schema versions **fail safe**: the store is left empty and the
        payload is ignored, rather than half-reading a record shape this code
        does not understand. When a v2 arrives, migrate it explicitly here.
        """
        if not payload or not isinstance(payload, dict):
            return False
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            logger.warning(
                "StoryEventStore: ignoring payload with unsupported schema_version %r "
                "(this build understands %d); starting empty.",
                version,
                SCHEMA_VERSION,
            )
            return False
        try:
            self.world_id = payload.get("world_id", self.world_id)
            self.max_events = max(1, int(payload.get("max_events", self.max_events)))
            events = payload.get("events") or []
            self.events = [dict(e) for e in events if isinstance(e, dict)]
            while len(self.events) > self.max_events:
                self.events.pop(0)
            # Keep ids monotonic across a restart even if next_id was absent, so
            # a restored world never re-issues an id a client has already seen.
            self._next_id = int(payload.get("next_id") or 0) or (
                max((e.get("id", 0) for e in self.events), default=0) + 1
            )
            logger.info(
                "StoryEventStore: loaded %d events for world %s",
                len(self.events),
                self.world_id,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("StoryEventStore: failed to load payload (%s); starting empty.", exc)
            self.events = []
            return False
