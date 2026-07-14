"""Commentary store for agent observations about a running simulation.

This is the storage backend for the **Board** feature (formerly "Insights").
AI agents (or humans) studying a *live* simulation POST short, evidence-backed
observations about its state and progress, and the web UI shows them as a live
feed - a colour commentator narrating the evolution. It mirrors the ring-buffer
+ REST-poll shape of :mod:`backend.metrics_history`.

The store is deliberately tiny and dependency-free: it holds a bounded list of
comment dicts, assigns each a monotonic ``id``, and stamps the simulation frame
and wall-clock time at which the comment was added. It only *records annotations
about* the simulation; it never reads or mutates simulation state, so posting a
comment can never perturb a running experiment.

Each comment is a plain JSON-serializable dict (schema v2)::

    {
        "id": int,            # monotonic, per-store
        "created_at": float,  # epoch seconds when posted
        "frame": int,         # simulation frame at post time
        "author": str,        # agent / model name (free text)
        "text": str,          # the observation itself
        "tags": list[str],    # e.g. ["selection", "foraging"]
        "severity": str,      # one of VALID_SEVERITIES
        "metrics": dict|None, # optional small numbers the agent attached
        "topic": str,         # one of TOPICS (v2)
        "reactions": dict,    # emoji -> list[reactor_name] (v2)
    }
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Bumped on breaking changes to the comment shape below.
SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# Topics (v2) - see docs/DISCUSSION_BOARD.md §3.1
# ---------------------------------------------------------------------------
TOPICS = ("ecosystem", "substrate", "environment", "ui")
DEFAULT_TOPIC = "ecosystem"

# ---------------------------------------------------------------------------
# Emoji reactions (v2) - see docs/DISCUSSION_BOARD.md §3.2
# ---------------------------------------------------------------------------
REACTION_EMOJI = ("👍", "👎", "❤️", "😂", "🎉", "💡", "👀", "⚠️")
MAX_REACTORS_PER_EMOJI = 40

# Severity an agent may attach, ordered low -> high importance. Anything else
# is coerced to DEFAULT_SEVERITY so the UI can rely on a closed set.
VALID_SEVERITIES = ("info", "insight", "warning", "concern")
DEFAULT_SEVERITY = "info"

# Bounds that keep the buffer small and each poll cheap. These are generous
# enough for a multi-day run (the oldest comments scroll off, like metrics).
DEFAULT_MAX_COMMENTS = 500
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
        self._lock = threading.Lock()

    def add(
        self,
        text: str,
        *,
        author: str | None = None,
        tags: Any = None,
        severity: str | None = None,
        metrics: Any = None,
        topic: str | None = None,
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

        clean_topic = (topic or DEFAULT_TOPIC).strip().lower()
        if clean_topic not in TOPICS:
            clean_topic = DEFAULT_TOPIC

        comment = {
            "id": self._next_id,
            "created_at": float(created_at) if created_at is not None else time.time(),
            "frame": int(frame) if frame is not None else 0,
            "author": clean_author,
            "text": clean_text,
            "tags": self._clean_tags(tags),
            "severity": clean_severity,
            "metrics": self._clean_metrics(metrics),
            "topic": clean_topic,
            "reactions": {},
        }

        with self._lock:
            self._next_id += 1
            self.comments.append(comment)

            # Keep the buffer within capacity (drop oldest first).
            if len(self.comments) > self.max_comments:
                self.comments.pop(0)

        return comment

    def react(self, comment_id: int, emoji: str, reactor: str) -> dict[str, Any] | None:
        """Add a reaction to a comment. Returns the updated comment or None.

        Raises ``ValueError`` if the emoji is not in REACTION_EMOJI.
        Returns ``None`` if the comment_id is not found.
        """
        if emoji not in REACTION_EMOJI:
            raise ValueError(f"invalid emoji: {emoji!r}")
        clean_reactor = ((reactor or "").strip()[:MAX_AUTHOR_LEN]) or "anon"

        with self._lock:
            comment = self._find_comment(comment_id)
            if comment is None:
                return None
            reactors = comment["reactions"].setdefault(emoji, [])
            if clean_reactor not in reactors:
                if len(reactors) < MAX_REACTORS_PER_EMOJI:
                    reactors.append(clean_reactor)
            return comment

    def unreact(self, comment_id: int, emoji: str, reactor: str) -> dict[str, Any] | None:
        """Remove a reaction from a comment. Returns the updated comment or None.

        Raises ``ValueError`` if the emoji is not in REACTION_EMOJI.
        Returns ``None`` if the comment_id is not found.
        """
        if emoji not in REACTION_EMOJI:
            raise ValueError(f"invalid emoji: {emoji!r}")
        clean_reactor = ((reactor or "").strip()[:MAX_AUTHOR_LEN]) or "anon"

        with self._lock:
            comment = self._find_comment(comment_id)
            if comment is None:
                return None
            reactors = comment["reactions"].get(emoji, [])
            if clean_reactor in reactors:
                reactors.remove(clean_reactor)
                # Clean up empty lists
                if not reactors:
                    comment["reactions"].pop(emoji, None)
            return comment

    def _find_comment(self, comment_id: int) -> dict[str, Any] | None:
        """Find a comment by id (caller must hold _lock)."""
        for c in self.comments:
            if c.get("id") == comment_id:
                return c
        return None

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

    def recent(
        self,
        limit: int | None = None,
        since_id: int | None = None,
        topic: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return stored comments, newest last.

        ``since_id`` returns only comments with a larger id (incremental polling);
        ``limit`` caps the result to the most recent N; ``topic`` filters to a
        single topic slug.
        """
        items = self.comments
        if since_id is not None:
            items = [c for c in items if c.get("id", 0) > since_id]
        if topic is not None:
            items = [c for c in items if c.get("topic") == topic]
        if limit is not None and limit >= 0:
            items = items[-limit:]
        return list(items)

    def clear(self) -> int:
        """Drop all comments; returns how many were removed."""
        with self._lock:
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
        """Restore from a payload, tolerating missing/invalid formats.

        Migrates v1 comments in place: adds default ``topic`` and ``reactions``
        fields so the store always reports schema version 2 after loading.
        """
        if not payload or not isinstance(payload, dict):
            return
        try:
            self.world_id = payload.get("world_id", self.world_id)
            self.max_comments = payload.get("max_comments", self.max_comments)
            self.comments = payload.get("comments", []) or []

            # v1 -> v2 migration: ensure every comment has topic + reactions
            for c in self.comments:
                c.setdefault("topic", DEFAULT_TOPIC)
                c.setdefault("reactions", {})

            # Always report v2 after loading (migration complete)
            self.schema_version = SCHEMA_VERSION

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
