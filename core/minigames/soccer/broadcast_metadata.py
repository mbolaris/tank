"""Optional match metadata consumed by the Soccer Arena broadcast UI.

Everything here is presentation-only: it is derived by *reading* engine state
after a cycle has been resolved. It consumes no RNG, queues no commands, and
feeds nothing back into physics or policy inputs.
"""

from __future__ import annotations

from typing import Protocol, cast


class _TeamTelemetry(Protocol):
    possession_frames: int


class _Telemetry(Protocol):
    teams: dict[str, _TeamTelemetry]


class _Vector(Protocol):
    x: float
    y: float


class _Player(Protocol):
    player_id: str

    def distance_to(self, other_pos: _Vector, /) -> float: ...


class _Ball(Protocol):
    position: _Vector


class _Params(Protocol):
    kickable_margin: float
    player_size: float


class _Engine(Protocol):
    play_mode: str
    params: _Params
    swapped_sides: bool

    def get_ball(self) -> _Ball: ...

    def iter_players(self) -> object: ...

    def last_touch_info(self) -> dict[str, str | None]: ...


class _Match(Protocol):
    _engine: _Engine
    _telemetry_collector: _TelemetryCollector
    current_frame: int
    duration_frames: int


class _TelemetryCollector(Protocol):
    def get_telemetry(self) -> _Telemetry: ...


def compute_ball_owner(engine: _Engine) -> str | None:
    """The participant *currently controlling* the ball, or None if it is loose.

    Control means "close enough to kick it this cycle" - the same
    ``kickable_margin + player_size`` threshold ``RCSSLiteEngine._apply_kick``
    enforces, so the possession ring can never highlight a player who could not
    actually play the ball.

    This is deliberately **not** last touch. Last touch stays available via
    ``last_touch_info()`` for goal and assist attribution; calling it
    "ownership" would leave the ring stuck on a player who passed the ball away
    several seconds ago.

    Ties resolve deterministically: nearest first, then lowest ``player_id``.
    """
    ball = engine.get_ball()
    params = engine.params
    kickable_distance = params.kickable_margin + params.player_size

    best: tuple[float, str] | None = None
    for player in cast(list[_Player], engine.iter_players()):
        distance = player.distance_to(ball.position)
        if distance > kickable_distance:
            continue
        candidate = (distance, player.player_id)
        if best is None or candidate < best:
            best = candidate
    return best[1] if best is not None else None


def build_match_broadcast_metadata(match: object) -> dict[str, object]:
    """Build deterministic, presentation-friendly metadata from a match."""
    typed_match = cast(_Match, match)
    engine = typed_match._engine
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
        "ball_owner": compute_ball_owner(engine),
        # Authoritative side assignment. The engine swaps halves at half-time,
        # which is what decides who occupies the left half of the pitch and
        # which way each team attacks. The renderer must read this rather than
        # assuming home is forever on the left.
        "sides_swapped": bool(engine.swapped_sides),
        "play_mode": engine.play_mode,
    }
