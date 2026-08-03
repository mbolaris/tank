"""Bounded snapshot store for live simulation skill progression.

This module provides data structures for capturing, storing, and persisting
skill ladder snapshots evaluated on live evolving fish populations in tank worlds.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.skill.ladder import SkillLadderSummary


@dataclass
class SkillSnapshot:
    """A snapshot of a live tank population's skill evaluation."""

    domain: str
    generation: int
    frame: int
    subject_fish_ids: list[int]
    subject_lineage_ids: list[str]
    summary: SkillLadderSummary
    previous_score: float | None
    personal_best: float
    tank_best: float
    sample_size: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to JSON-serializable dictionary."""
        return {
            "domain": self.domain,
            "generation": self.generation,
            "frame": self.frame,
            "subject_fish_ids": list(self.subject_fish_ids),
            "subject_lineage_ids": list(self.subject_lineage_ids),
            "summary": self.summary.to_dict(),
            "previous_score": self.previous_score,
            "personal_best": self.personal_best,
            "tank_best": self.tank_best,
            "sample_size": self.sample_size,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillSnapshot:
        """Construct a SkillSnapshot from a dictionary representation."""
        summary_data = data.get("summary", {})
        summary = SkillLadderSummary.from_dict(summary_data)
        prev_score = data.get("previous_score")
        return cls(
            domain=str(data.get("domain", summary.domain)),
            generation=int(data.get("generation", 0)),
            frame=int(data.get("frame", 0)),
            subject_fish_ids=[int(x) for x in data.get("subject_fish_ids", [])],
            subject_lineage_ids=[str(x) for x in data.get("subject_lineage_ids", [])],
            summary=summary,
            previous_score=float(prev_score) if prev_score is not None else None,
            personal_best=float(data.get("personal_best", 0.0)),
            tank_best=float(data.get("tank_best", 0.0)),
            sample_size=int(data.get("sample_size", 0)),
            timestamp=float(data.get("timestamp", 0.0)),
        )


@dataclass(frozen=True)
class BreakthroughRecord:
    """A backend-authored, deterministic milestone for one tank."""

    event_id: str
    kind: str
    source_id: str
    frame: int
    detail: dict[str, object] = field(default_factory=dict)
    match_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "event_id": self.event_id,
            "kind": self.kind,
            "source_id": self.source_id,
            "frame": self.frame,
            "detail": dict(self.detail),
        }
        if self.match_id is not None:
            data["match_id"] = self.match_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BreakthroughRecord:
        raw_detail = data.get("detail", {})
        raw_frame = data.get("frame", 0)
        frame = int(raw_frame) if isinstance(raw_frame, (int, float, str)) else 0
        return cls(
            event_id=str(data.get("event_id", "")),
            kind=str(data.get("kind", "")),
            source_id=str(data.get("source_id", "tank")),
            frame=frame,
            detail=dict(raw_detail) if isinstance(raw_detail, dict) else {},
            match_id=str(data["match_id"]) if data.get("match_id") is not None else None,
        )


@dataclass
class SkillSnapshotStore:
    """Bounded in-memory store for skill progression snapshots.

    Defensive cap prevents unbounded growth in long-running simulations.
    Tracks all-time tank_best and per-subject personal_best in O(1) time.
    """

    MAX_SNAPSHOTS: int = 50

    _snapshots: list[SkillSnapshot] = field(default_factory=list)
    _tank_best: float = 0.0
    _tank_bests: dict[str, float] = field(default_factory=dict)
    _personal_bests: dict[str, float] = field(default_factory=dict)
    _breakthroughs: list[BreakthroughRecord] = field(default_factory=list)

    @property
    def tank_best(self) -> float:
        """The highest skill_index recorded in this tank."""
        return self._tank_best

    def add_snapshot(self, snapshot: SkillSnapshot) -> None:
        """Add a new snapshot, updating O(1) best tracking and maintaining capacity."""
        score = snapshot.summary.skill_index

        # Update tank best
        if score > self._tank_best:
            self._tank_best = score
        if score > self._tank_bests.get(snapshot.domain, 0.0):
            self._tank_bests[snapshot.domain] = score

        # Update team personal best
        team_key = ",".join(str(i) for i in sorted(snapshot.subject_fish_ids))
        if team_key:
            domain_key = f"{snapshot.domain}:{team_key}"
            current_pb = self._personal_bests.get(
                domain_key, self._personal_bests.get(team_key, 0.0)
            )
            if score > current_pb:
                self._personal_bests[domain_key] = score

        self._snapshots.append(snapshot)

        # Enforce the cap independently for each domain. Older S1 stores used
        # one global list; retaining the same list keeps their JSON readable,
        # while pruning by domain prevents poker from evicting soccer history.
        for domain in {s.domain for s in self._snapshots}:
            domain_snapshots = [s for s in self._snapshots if s.domain == domain]
            if len(domain_snapshots) <= self.MAX_SNAPSHOTS:
                continue
            keep = {id(s) for s in domain_snapshots[-self.MAX_SNAPSHOTS :]}
            self._snapshots = [s for s in self._snapshots if s.domain != domain or id(s) in keep]

    def get_snapshots(
        self, limit: int | None = None, domain: str | None = None
    ) -> list[SkillSnapshot]:
        """Get recent snapshots, optionally filtered by domain and limited."""
        result = self._snapshots
        if domain is not None:
            result = [s for s in result if s.domain == domain]
        if limit is not None:
            result = result[-limit:]
        return list(result)

    def get_latest_snapshot(self, domain: str | None = None) -> SkillSnapshot | None:
        """Get the most recent snapshot."""
        matches = self.get_snapshots(domain=domain)
        return matches[-1] if matches else None

    def get_personal_best_for_team(
        self, subject_fish_ids: list[int], domain: str | None = None
    ) -> float:
        """Return personal best score recorded for a subject fish set.

        The optional domain keeps poker and soccer scores independent. The
        legacy no-domain lookup remains compatible with S1 callers and old
        persisted ``personal_bests`` keys.
        """
        return self.get_personal_best(subject_fish_ids, domain=domain)

    def get_personal_best(self, subject_fish_ids: list[int], domain: str | None = None) -> float:
        """Return a personal best, optionally restricted to one domain."""
        team_key = ",".join(str(i) for i in sorted(subject_fish_ids))
        if not team_key:
            return 0.0
        if domain is not None:
            return self._personal_bests.get(
                f"{domain}:{team_key}", self._personal_bests.get(team_key, 0.0)
            )

        legacy = self._personal_bests.get(team_key)
        if legacy is not None:
            return legacy
        prefix = ":" + team_key
        return max(
            (value for key, value in self._personal_bests.items() if key.endswith(prefix)),
            default=0.0,
        )

    def get_tank_best(self, domain: str | None = None) -> float:
        """Return the all-time tank best for one domain or for the whole tank."""
        if domain is None:
            return self._tank_best
        return self._tank_bests.get(domain, 0.0)

    def add_breakthrough(self, record: BreakthroughRecord) -> bool:
        """Persist a breakthrough once, keyed by its stable event id."""
        if not record.event_id or any(
            item.event_id == record.event_id for item in self._breakthroughs
        ):
            return False
        self._breakthroughs.append(record)
        self._breakthroughs = self._breakthroughs[-100:]
        return True

    def get_breakthroughs(self, limit: int | None = None) -> list[BreakthroughRecord]:
        """Return persisted breakthroughs in emission order."""
        result = list(self._breakthroughs)
        return result[-limit:] if limit is not None else result

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot store for world persistence."""
        return {
            "max_snapshots": self.MAX_SNAPSHOTS,
            "tank_best": self._tank_best,
            "tank_bests": dict(self._tank_bests),
            "personal_bests": dict(self._personal_bests),
            "snapshots": [s.to_dict() for s in self._snapshots],
            "breakthroughs": [item.to_dict() for item in self._breakthroughs],
        }

    def load(self, data: dict[str, Any]) -> None:
        """Load state into snapshot store from a serialized dictionary."""
        if not isinstance(data, dict):
            return
        self.MAX_SNAPSHOTS = int(data.get("max_snapshots", self.MAX_SNAPSHOTS))
        self._tank_best = float(data.get("tank_best", 0.0))
        raw_tank_bests = data.get("tank_bests", {})
        self._tank_bests = (
            {str(k): float(v) for k, v in raw_tank_bests.items()}
            if isinstance(raw_tank_bests, dict)
            else {}
        )
        self._personal_bests = {str(k): float(v) for k, v in data.get("personal_bests", {}).items()}
        raw_snapshots = data.get("snapshots", [])
        self._snapshots = [SkillSnapshot.from_dict(s) for s in raw_snapshots if isinstance(s, dict)]
        raw_breakthroughs = data.get("breakthroughs", [])
        self._breakthroughs = [
            BreakthroughRecord.from_dict(item)
            for item in raw_breakthroughs
            if isinstance(item, dict)
        ][-100:]
        if not self._tank_bests:
            for snapshot in self._snapshots:
                self._tank_bests[snapshot.domain] = max(
                    self._tank_bests.get(snapshot.domain, 0.0), snapshot.summary.skill_index
                )
        for domain in {s.domain for s in self._snapshots}:
            domain_snapshots = [s for s in self._snapshots if s.domain == domain]
            if len(domain_snapshots) > self.MAX_SNAPSHOTS:
                keep = {id(s) for s in domain_snapshots[-self.MAX_SNAPSHOTS :]}
                self._snapshots = [
                    s for s in self._snapshots if s.domain != domain or id(s) in keep
                ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillSnapshotStore:
        """Construct a SkillSnapshotStore from a serialized dictionary."""
        store = cls()
        store.load(data)
        return store
