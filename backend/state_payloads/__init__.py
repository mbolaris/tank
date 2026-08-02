"""Lightweight data transfer objects for simulation state serialization.

Split into per-concern modules (metrics, entities, poker, soccer, stats,
frames); this package re-exports the full public surface so
``from backend.state_payloads import X`` keeps working unchanged.
"""

from __future__ import annotations

from backend.state_payloads._common import orjson
from backend.state_payloads.entities import EntitySnapshot
from backend.state_payloads.frames import STATE_SCHEMA_VERSION, DeltaStatePayload, FullStatePayload
from backend.state_payloads.metrics import (
    MetricsHistoryPayload,
    MetricsPokerSamplePayload,
    MetricsSamplePayload,
    MetricsSoccerSamplePayload,
)
from backend.state_payloads.poker import (
    AutoEvaluateStatsPayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
    PokerStatsPayload,
)
from backend.state_payloads.soccer import (
    SoccerEventPayload,
    SoccerMatchEventPayload,
    SoccerParticipantPayload,
)
from backend.state_payloads.stats import StatsPayload

__all__ = [
    "STATE_SCHEMA_VERSION",
    "orjson",
    "AutoEvaluateStatsPayload",
    "DeltaStatePayload",
    "EntitySnapshot",
    "FullStatePayload",
    "MetricsHistoryPayload",
    "MetricsPokerSamplePayload",
    "MetricsSamplePayload",
    "MetricsSoccerSamplePayload",
    "PokerEventPayload",
    "PokerLeaderboardEntryPayload",
    "PokerStatsPayload",
    "SoccerEventPayload",
    "SoccerMatchEventPayload",
    "SoccerParticipantPayload",
    "StatsPayload",
]
