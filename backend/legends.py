"""In-world legends: the organisms and lineages this tank will remember (U8b/E6).

A legend is a *promotion*, not a leaderboard entry. Something happened that met
an explicit, published criterion — a fish outlived every fish before it, a
founder's line took root, a survivor came through a collapse — and the tank
records who it was and why they qualified.

**Legends are not benchmark champions.** The ``champions/`` registry records the
best known *solution* to a benchmark: reproducible, seeded, comparable across
runs. A legend is a thing that happened inside one particular world's history
and means nothing outside it. The two are deliberately unconnected — nothing in
this module reads the champion registry, and a test enforces that — because
conflating them would let a lucky in-world fish look like a validated result.

Names are a pure function of the subject's id, so a legend called "Patient
Drifter" is still called that after a reload, a restore, or a server restart.
Promotion is deduplicated by (kind, subject), so a fish cannot be crowned twice
for the same reason.

A stored record (schema v1)::

    {
        "id": int,               # monotonic, per-store
        "schema_version": int,
        "kind": str,             # which criterion promoted it (LEGEND_KINDS)
        "subject_type": str,     # "fish" | "lineage"
        "subject_id": str,
        "name": str,             # stable, derived from subject_id alone
        "title": str,            # short label for a feed row
        "reason": str,           # why it qualified, in words
        "evidence": dict,        # the measured numbers behind that reason
        "frame": int,
        "simulation_time": float,
    }
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# The closed set of promotion criteria. Growing it is a versioned change.
LEGEND_KINDS = (
    "longevity_record",
    "lineage_founder",
    "collapse_survivor",
)

SUBJECT_TYPES = ("fish", "lineage")

# Bounded so a long run cannot grow the store without limit. Legends are meant
# to be rare; if this cap is ever reached the criteria are too generous.
DEFAULT_MAX_LEGENDS = 200

MAX_REASON_LEN = 300
MAX_EVIDENCE_KEYS = 12

# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------
# Two fixed word lists. A name is a pure function of the subject id, which is
# what makes it stable across reloads - there is no RNG and no dependence on
# promotion order. 24 x 24 = 576 distinct names before the cycle suffix starts.

_ADJECTIVES = (
    "Patient",
    "Restless",
    "Quiet",
    "Stubborn",
    "Bright",
    "Wary",
    "Bold",
    "Ancient",
    "Swift",
    "Steady",
    "Hidden",
    "Lucky",
    "Grim",
    "Gentle",
    "Fierce",
    "Curious",
    "Solemn",
    "Nimble",
    "Ragged",
    "Radiant",
    "Silent",
    "Weathered",
    "Keen",
    "Humble",
)

_NOUNS = (
    "Drifter",
    "Sentinel",
    "Wanderer",
    "Forager",
    "Elder",
    "Pioneer",
    "Survivor",
    "Nomad",
    "Warden",
    "Scout",
    "Anchor",
    "Voyager",
    "Keeper",
    "Seeker",
    "Runner",
    "Watcher",
    "Founder",
    "Strider",
    "Dweller",
    "Ranger",
    "Shade",
    "Current",
    "Ember",
    "Tide",
)

_ROMAN = ("", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X")


def legend_name(subject_id: str) -> str:
    """A stable display name derived from the subject id alone.

    Deterministic by construction: the same id always yields the same name, so
    a legend keeps its name across reloads and restores. Distinct ids yield
    distinct names — the cycle suffix guarantees it past the first 576.
    """
    seed = _stable_index(subject_id)
    adjective = _ADJECTIVES[seed % len(_ADJECTIVES)]
    noun = _NOUNS[(seed // len(_ADJECTIVES)) % len(_NOUNS)]
    cycle = seed // (len(_ADJECTIVES) * len(_NOUNS))
    suffix = _ROMAN[cycle] if cycle < len(_ROMAN) else f" ({cycle + 1})"
    return f"{adjective} {noun}{suffix}"


def _stable_index(subject_id: str) -> int:
    """A non-negative index for an id.

    Numeric ids map to themselves so consecutive fish get spread-out names.
    Python's ``hash()`` is deliberately avoided: it is salted per process, so
    names built on it would change on every server restart.
    """
    try:
        return abs(int(subject_id))
    except (TypeError, ValueError):
        total = 0
        for char in str(subject_id):
            total = (total * 31 + ord(char)) % 1_000_003
        return total


def _clean_evidence(evidence: Any) -> dict[str, Any]:
    """Keep a small dict of the scalar measurements behind a promotion."""
    if not isinstance(evidence, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in evidence.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (int, float, str, bool)) or value is None:
            cleaned[key] = value
        if len(cleaned) >= MAX_EVIDENCE_KEYS:
            break
    return cleaned


def make_legend(
    *,
    kind: str,
    subject_type: str,
    subject_id: str,
    title: str,
    reason: str,
    frame: int,
    simulation_time: float,
    evidence: Any = None,
) -> dict[str, Any]:
    """Build an un-numbered legend record with every field normalized."""
    if kind not in LEGEND_KINDS:
        raise ValueError(f"unknown legend kind: {kind!r}")
    if subject_type not in SUBJECT_TYPES:
        raise ValueError(f"unknown subject_type: {subject_type!r}")
    clean_subject = str(subject_id)
    return {
        "kind": kind,
        "subject_type": subject_type,
        "subject_id": clean_subject,
        "name": legend_name(clean_subject),
        "title": (title or kind).strip()[:MAX_REASON_LEN],
        "reason": (reason or "").strip()[:MAX_REASON_LEN],
        "evidence": _clean_evidence(evidence),
        "frame": int(frame),
        "simulation_time": round(float(simulation_time), 3),
    }


def dedup_key(kind: str, subject_type: str, subject_id: str) -> str:
    """The identity a promotion is deduplicated on."""
    return f"{kind}:{subject_type}:{subject_id}"


class LegendStore:
    """Bounded, deduplicated store of a single world's legends."""

    def __init__(
        self,
        world_id: str | None = None,
        max_legends: int = DEFAULT_MAX_LEGENDS,
    ) -> None:
        self.schema_version = SCHEMA_VERSION
        self.world_id = world_id or "unknown"
        self.max_legends = max(1, int(max_legends))
        self.legends: list[dict[str, Any]] = []
        self._next_id = 1
        self._promoted: set[str] = set()
        self._lock = threading.Lock()

    def add(self, legend: dict[str, Any]) -> dict[str, Any] | None:
        """Stamp and store a legend, or return None if already promoted.

        The dedup set is the whole point: a fish that holds the longevity
        record for a thousand frames must be crowned once, not once per sample.
        """
        key = dedup_key(legend["kind"], legend["subject_type"], legend["subject_id"])
        with self._lock:
            if key in self._promoted:
                return None
            record = dict(legend)
            record["id"] = self._next_id
            record["schema_version"] = SCHEMA_VERSION
            self._next_id += 1
            self._promoted.add(key)
            self.legends.append(record)

            # Drop oldest first, but keep its dedup key: a legend that scrolled
            # out of the buffer must not be promotable again.
            while len(self.legends) > self.max_legends:
                self.legends.pop(0)
            return record

    def has(self, kind: str, subject_type: str, subject_id: str) -> bool:
        return dedup_key(kind, subject_type, subject_id) in self._promoted

    def recent(
        self,
        limit: int | None = None,
        since_id: int | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return stored legends, oldest first."""
        items = self.legends
        if since_id is not None:
            items = [x for x in items if x.get("id", 0) > since_id]
        if kind is not None:
            items = [x for x in items if x.get("kind") == kind]
        if limit is not None and limit >= 0:
            items = items[-limit:]
        return list(items)

    def clear(self) -> int:
        """Drop all legends and allow re-promotion. Ids stay monotonic."""
        with self._lock:
            count = len(self.legends)
            self.legends = []
            self._promoted = set()
            return count

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "max_legends": self.max_legends,
            "next_id": self._next_id,
            "legends": self.legends,
            # Persisted separately from the records: dropped legends still
            # occupy their dedup key, so the set outlives the buffer.
            "promoted": sorted(self._promoted),
        }

    def load(self, payload: dict[str, Any] | None) -> bool:
        """Restore from a payload. Unknown schema versions fail safe."""
        if not payload or not isinstance(payload, dict):
            return False
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            logger.warning(
                "LegendStore: ignoring payload with unsupported schema_version %r "
                "(this build understands %d); starting empty.",
                version,
                SCHEMA_VERSION,
            )
            return False
        try:
            self.world_id = payload.get("world_id", self.world_id)
            self.max_legends = max(1, int(payload.get("max_legends", self.max_legends)))
            legends = payload.get("legends") or []
            self.legends = [dict(x) for x in legends if isinstance(x, dict)]
            while len(self.legends) > self.max_legends:
                self.legends.pop(0)
            stored_keys = payload.get("promoted")
            self._promoted = (
                {str(k) for k in stored_keys}
                if isinstance(stored_keys, list)
                else {
                    dedup_key(x.get("kind", ""), x.get("subject_type", ""), x.get("subject_id", ""))
                    for x in self.legends
                }
            )
            self._next_id = int(payload.get("next_id") or 0) or (
                max((x.get("id", 0) for x in self.legends), default=0) + 1
            )
            logger.info(
                "LegendStore: loaded %d legends for world %s", len(self.legends), self.world_id
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("LegendStore: failed to load payload (%s); starting empty.", exc)
            self.legends = []
            self._promoted = set()
            return False
