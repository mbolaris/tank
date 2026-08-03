"""Optional match metadata consumed by the Soccer Arena broadcast UI."""

from __future__ import annotations

from typing import Protocol, cast


class _TeamTelemetry(Protocol):
    possession_frames: int


class _Telemetry(Protocol):
    teams: dict[str, _TeamTelemetry]


class _Engine(Protocol):
    play_mode: str

    def last_touch_info(self) -> dict[str, str | None]: ...


class _Match(Protocol):
    _engine: _Engine
    _telemetry_collector: _TelemetryCollector
    current_frame: int
    duration_frames: int


class _TelemetryCollector(Protocol):
    def get_telemetry(self) -> _Telemetry: ...


def build_match_broadcast_metadata(match: object) -> dict[str, object]:
    """Build deterministic, presentation-friendly metadata from a match."""
    typed_match = cast(_Match, match)
    telemetry = typed_match._telemetry_collector.get_telemetry()
    left = telemetry.teams["left"].possession_frames
    right = telemetry.teams["right"].possession_frames
    total = left + right
    period_frames = max(1, typed_match.duration_frames // 2)
    return {
        "half": 2 if typed_match.current_frame >= period_frames else 1,
        "period_frames": period_frames,
        "possession": {
            "left": left / total if total else 0.0,
            "right": right / total if total else 0.0,
        },
        "ball_owner": typed_match._engine.last_touch_info().get("player_id"),
        "play_mode": typed_match._engine.play_mode,
    }
