"""Full and delta frame payloads: the top-level WebSocket wire messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.state_payloads._common import serialize
from backend.state_payloads.entities import EntitySnapshot
from backend.state_payloads.metrics import MetricsHistoryPayload, MetricsSamplePayload
from backend.state_payloads.poker import (
    AutoEvaluateStatsPayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
)
from backend.state_payloads.soccer import SoccerEventPayload
from backend.state_payloads.stats import StatsPayload

STATE_SCHEMA_VERSION = 2


@dataclass
class FullStatePayload:
    """Full snapshot with complete entity data."""

    frame: int
    elapsed_time: int
    entities: list[EntitySnapshot]
    stats: StatsPayload
    poker_events: list[PokerEventPayload]
    soccer_events: list[SoccerEventPayload]
    poker_leaderboard: list[PokerLeaderboardEntryPayload]
    soccer_league_live: dict[str, Any] | None = None
    auto_evaluation: AutoEvaluateStatsPayload | None = None
    schema_version: int = STATE_SCHEMA_VERSION
    type: str = "update"
    world_id: str | None = None  # World identifier for multi-world mode
    mode_id: str | None = "tank"
    world_type: str | None = "tank"
    view_mode: str | None = "side"
    tank_soccer_enabled: bool | None = None  # Whether tank practice soccer (ball/goals) is enabled
    metrics_history: MetricsHistoryPayload | None = None

    def to_dict(self) -> dict[str, Any]:
        # Build snapshot containing all simulation state
        snapshot = {
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "entities": [e.to_full_dict() for e in self.entities],
            "stats": self.stats.to_dict(),
            "poker_events": [e.to_dict() for e in self.poker_events],
            "soccer_events": [e.to_dict() for e in self.soccer_events],
            "soccer_league_live": self.soccer_league_live,
            "poker_leaderboard": [e.to_dict() for e in self.poker_leaderboard],
        }
        if self.auto_evaluation:
            snapshot["auto_evaluation"] = self.auto_evaluation.to_dict()
        if self.metrics_history is not None:
            snapshot["metrics_history"] = self.metrics_history.to_dict()

        # Top-level payload with metadata and nested snapshot
        data: dict[str, Any] = {
            "type": self.type,
            "schema_version": self.schema_version,
            "snapshot": snapshot,
        }
        if self.world_id is not None:
            data["world_id"] = self.world_id
        if self.mode_id is not None:
            data["mode_id"] = self.mode_id
        if self.world_type is not None:
            data["world_type"] = self.world_type
        if self.view_mode is not None:
            data["view_mode"] = self.view_mode
        if self.tank_soccer_enabled is not None:
            data["tank_soccer_enabled"] = self.tank_soccer_enabled
        return data

    def to_json(self) -> str:
        return serialize(self.to_dict())


@dataclass
class DeltaStatePayload:
    """Delta update that only carries incremental changes."""

    frame: int
    elapsed_time: int
    updates: list[dict[str, Any]]
    added: list[dict[str, Any]]
    removed: list[int]
    poker_events: list[PokerEventPayload] | None = None
    soccer_events: list[SoccerEventPayload] | None = None
    soccer_league_live: dict[str, Any] | None = None
    stats: StatsPayload | None = None
    schema_version: int = STATE_SCHEMA_VERSION
    type: str = "delta"
    world_id: str | None = None  # World identifier for multi-world mode
    mode_id: str | None = "tank"
    world_type: str | None = "tank"
    view_mode: str | None = "side"
    tank_soccer_enabled: bool | None = None  # Whether tank practice soccer (ball/goals) is enabled
    new_metrics_sample: MetricsSamplePayload | None = None

    def to_dict(self) -> dict[str, Any]:
        # Build snapshot containing delta simulation state
        snapshot: dict[str, Any] = {
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "updates": self.updates,
            "added": self.added,
            "removed": self.removed,
        }
        if self.poker_events is not None:
            snapshot["poker_events"] = [e.to_dict() for e in self.poker_events]
        if self.soccer_events is not None:
            snapshot["soccer_events"] = [e.to_dict() for e in self.soccer_events]
        snapshot["soccer_league_live"] = self.soccer_league_live
        if self.stats:
            snapshot["stats"] = self.stats.to_dict()
        if self.new_metrics_sample is not None:
            snapshot["new_metrics_sample"] = self.new_metrics_sample.to_dict()

        # Top-level payload with metadata and nested snapshot
        data: dict[str, Any] = {
            "type": self.type,
            "schema_version": self.schema_version,
            "snapshot": snapshot,
        }
        if self.world_id is not None:
            data["world_id"] = self.world_id
        if self.mode_id is not None:
            data["mode_id"] = self.mode_id
        if self.world_type is not None:
            data["world_type"] = self.world_type
        if self.view_mode is not None:
            data["view_mode"] = self.view_mode
        if self.tank_soccer_enabled is not None:
            data["tank_soccer_enabled"] = self.tank_soccer_enabled
        return data

    def to_json(self) -> str:
        return serialize(self.to_dict())
