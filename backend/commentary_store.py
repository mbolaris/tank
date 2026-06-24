"""Commentary store for agent observations about a running simulation.

This is the storage backend for the **Insights** feature. AI agents (or humans)
studying a *live* simulation POST short, evidence-backed observations about its
state and progress, and the web UI shows them as a live feed - a colour
commentator narrating the evolution. It mirrors the ring-buffer + REST-poll
shape of :mod:`backend.metrics_history`.

The store is deliberately tiny and dependency-free: it holds a bounded list of
comment dicts, assigns each a monotonic ``id``, and stamps the simulation frame
and wall-clock time at which the comment was added. It only *records annotations
about* the simulation; it never reads or mutates simulation state, so posting a
comment can never perturb a running experiment.

Each comment is a plain JSON-serializable dict::

    {
        "id": int,            # monotonic, per-store
        "created_at": float,  # epoch seconds when posted
        "frame": int,         # simulation frame at post time
        "author": str,        # agent / model name (free text)
        "text": str,          # the observation itself
        "tags": list[str],    # e.g. ["selection", "foraging"]
        "severity": str,      # one of VALID_SEVERITIES
        "metrics": dict|None, # optional small numbers the agent attached
    }
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Bumped only on breaking changes to the comment shape below.
SCHEMA_VERSION = 1

# Severity an agent may attach, ordered low -> high importance. Anything else
# is coerced to DEFAULT_SEVERITY so the UI can rely on a closed set.
VALID_SEVERITIES = ("info", "insight", "warning", "concern")
DEFAULT_SEVERITY = "info"

# Bounds that keep the buffer small and each poll cheap. These are generous
# enough for a multi-day run (the oldest comments scroll off, like metrics).
DEFAULT_MAX_COMMENTS = 200
MAX_TEXT_LEN = 2000
MAX_AUTHOR_LEN = 80
MAX_TAGS = 8
MAX_TAG_LEN = 40
MAX_METRICS_KEYS = 24


class CommentaryStore:
    """Bounded ring buffer of agent commentary for a single world."""

    def __init__(
        self,
        world_id: str | None = None,
        max_comments: int = DEFAULT_MAX_COMMENTS,
    ) -> None:
        self.schema_version = SCHEMA_VERSION
        self.world_id = world_id or "unknown"
        self.max_comments = max_comments
        self.comments: list[dict[str, Any]] = []
        self._next_id = 1

    def add(
        self,
        text: str,
        *,
        author: str | None = None,
        tags: Any = None,
        severity: str | None = None,
        metrics: Any = None,
        frame: int = 0,
        created_at: float | None = None,
    ) -> dict[str, Any]:
        """Validate and append a comment, returning the stored dict.

        Raises ``ValueError`` if ``text`` is empty/whitespace. All other fields
        are sanitized (clamped, coerced, defaulted) rather than rejected so a
        slightly-malformed agent payload still lands as a usable comment.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("comment text must not be empty")
        clean_text = clean_text[:MAX_TEXT_LEN]

        clean_author = ((author or "").strip()[:MAX_AUTHOR_LEN]) or "agent"

        clean_severity = (severity or DEFAULT_SEVERITY).strip().lower()
        if clean_severity not in VALID_SEVERITIES:
            clean_severity = DEFAULT_SEVERITY

        comment = {
            "id": self._next_id,
            "created_at": float(created_at) if created_at is not None else time.time(),
            "frame": int(frame) if frame is not None else 0,
            "author": clean_author,
            "text": clean_text,
            "tags": self._clean_tags(tags),
            "severity": clean_severity,
            "metrics": self._clean_metrics(metrics),
        }
        self._next_id += 1
        self.comments.append(comment)

        # Keep the buffer within capacity (drop oldest first).
        if len(self.comments) > self.max_comments:
            self.comments.pop(0)

        return comment

    @staticmethod
    def _clean_tags(tags: Any) -> list[str]:
        """Normalize tags to a short list of non-empty strings.

        Accepts a list/tuple of strings or a single comma/space-separated
        string; anything else yields an empty list.
        """
        if not tags:
            return []
        if isinstance(tags, str):
            tags = tags.replace(",", " ").split()
        if not isinstance(tags, (list, tuple)):
            return []

        result: list[str] = []
        for raw in tags:
            if not isinstance(raw, str):
                continue
            tag = raw.strip()[:MAX_TAG_LEN]
            if tag:
                result.append(tag)
            if len(result) >= MAX_TAGS:
                break
        return result

    @staticmethod
    def _clean_metrics(metrics: Any) -> dict[str, Any] | None:
        """Keep an optional small dict of scalar metrics the agent attached."""
        if not isinstance(metrics, dict) or not metrics:
            return None
        cleaned: dict[str, Any] = {}
        for key, value in metrics.items():
            if not isinstance(key, str):
                continue
            if isinstance(value, (int, float, str, bool)) or value is None:
                cleaned[key[:MAX_TAG_LEN]] = value
            if len(cleaned) >= MAX_METRICS_KEYS:
                break
        return cleaned or None

    def recent(self, limit: int | None = None, since_id: int | None = None) -> list[dict[str, Any]]:
        """Return stored comments, newest last.

        ``since_id`` returns only comments with a larger id (incremental polling);
        ``limit`` caps the result to the most recent N.
        """
        items = self.comments
        if since_id is not None:
            items = [c for c in items if c.get("id", 0) > since_id]
        if limit is not None and limit >= 0:
            items = items[-limit:]
        return list(items)

    def clear(self) -> int:
        """Drop all comments; returns how many were removed."""
        count = len(self.comments)
        self.comments = []
        return count

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the REST API and for world save/restore."""
        return {
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "max_comments": self.max_comments,
            "next_id": self._next_id,
            "comments": self.comments,
        }

    def load(self, payload: dict[str, Any] | None) -> None:
        """Restore from a payload, tolerating missing/invalid formats."""
        if not payload or not isinstance(payload, dict):
            return
        try:
            self.schema_version = payload.get("schema_version", SCHEMA_VERSION)
            self.world_id = payload.get("world_id", self.world_id)
            self.max_comments = payload.get("max_comments", self.max_comments)
            self.comments = payload.get("comments", []) or []
            # Keep ids monotonic across a restart even if next_id was absent.
            self._next_id = payload.get("next_id") or (
                max((c.get("id", 0) for c in self.comments), default=0) + 1
            )
            logger.info(
                "CommentaryStore: loaded %d comments for world %s",
                len(self.comments),
                self.world_id,
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("CommentaryStore: failed to load payload (%s); starting empty.", e)
