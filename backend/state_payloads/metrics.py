"""Metrics-history payloads (per-sample trend data for the web UI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.state_payloads._common import to_dict


@dataclass
class MetricsPokerSamplePayload:
    auto_eval_elo: float
    total_games: int
    showdown_win_rate: float
    net_energy_total: float

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class MetricsSoccerSamplePayload:
    goals_total: int
    goals_per_1k_frames: float
    matches_completed: int
    matches_skipped: int
    baseline_match_score_diff: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class MetricsSamplePayload:
    frame: int
    max_generation: int
    population: int
    births_total: int
    deaths_total: int
    fish_energy: float
    poker: MetricsPokerSamplePayload
    soccer: MetricsSoccerSamplePayload
    diversity_score: float = 0.0
    # Population mean of tracked heritable traits at this sample (may be empty
    # for pre-trait history or non-fish worlds). See trait_trends.py.
    traits: dict[str, float] = field(default_factory=dict)
    death_causes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = to_dict(self)
        data["poker"] = self.poker.to_dict()
        data["soccer"] = self.soccer.to_dict()
        return data


@dataclass
class MetricsHistoryPayload:
    schema_version: int
    world_id: str
    sample_interval_frames: int
    max_samples: int
    samples: list[MetricsSamplePayload]
    selection_quality: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = to_dict(self)
        data["samples"] = [s.to_dict() for s in self.samples]
        if self.selection_quality is not None:
            data["selection_quality"] = self.selection_quality
        return data
