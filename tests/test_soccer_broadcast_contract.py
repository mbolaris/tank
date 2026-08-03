"""PR 2 wire fields used by the Soccer Arena broadcast presenter."""

from __future__ import annotations

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
    assert state["play_mode"] == "before_kick_off"


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
