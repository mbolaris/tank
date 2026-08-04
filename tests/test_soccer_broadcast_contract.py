"""PR 2 wire fields used by the Soccer Arena broadcast presenter."""

from __future__ import annotations

from core.minigames.soccer.engine import RCSSVector
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.participant import SoccerParticipant


def _match(duration_frames: int = 10) -> SoccerMatch:
    return SoccerMatch(
        match_id="broadcast-contract",
        entities=[
            SoccerParticipant(participant_id="left_1", team="left"),
            SoccerParticipant(participant_id="right_1", team="right"),
        ],
        duration_frames=duration_frames,
        seed=42,
    )


def test_match_state_exposes_optional_broadcast_metadata() -> None:
    match = _match()
    state = match.get_state()

    assert state["half"] == 1
    assert state["period_frames"] == 5
    assert state["possession"] == {"left": 0.0, "right": 0.0}
    assert state["ball_owner"] is None
    assert state["sides_swapped"] is False
    assert state["play_mode"] == "before_kick_off"


def test_ball_owner_tracks_current_control_not_last_touch() -> None:
    """The possession ring must follow who can play the ball *now*."""
    match = _match()
    engine = match._engine
    kickable = engine.params.kickable_margin + engine.params.player_size

    # Walk a player onto the ball: it becomes theirs.
    ball = engine.get_ball()
    holder = engine.get_player("left_1")
    holder.position = RCSSVector(ball.position.x, ball.position.y)
    assert match.get_state()["ball_owner"] == "left_1"

    # Record a last touch, then move that player well clear of the ball. Last
    # touch is retained for attribution, but nobody is controlling it now.
    engine._last_touch_player_id = "left_1"
    holder.position = RCSSVector(ball.position.x + kickable * 5, ball.position.y)
    state = match.get_state()
    assert engine.last_touch_info()["player_id"] == "left_1"
    assert state["ball_owner"] is None


def test_sides_swapped_follows_the_engine_at_half_time() -> None:
    match = _match()
    assert match.get_state()["sides_swapped"] is False

    match.step(5)  # Half time: the engine swaps which half each team occupies.
    state = match.get_state()
    assert state["sides_swapped"] is True
    assert state["half"] == 2


def test_half_and_full_time_events_remain_ordered_and_stable() -> None:
    match = _match()
    match.step(5)
    halftime = match.get_state()
    match.step(5)
    full_time = match.get_state()

    assert halftime["half"] == 2
    assert halftime["events"][-1]["kind"] == "half_time"
    assert full_time["events"][-1]["kind"] == "full_time"
    pairs = [(event["seq"], event["event_id"]) for event in full_time["events"]]
    assert pairs == sorted(pairs)
    assert len({event_id for _, event_id in pairs}) == len(pairs)
