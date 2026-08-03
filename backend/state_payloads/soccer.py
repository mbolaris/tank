"""Soccer minigame wire payload (per-match event)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.state_payloads._common import to_dict


@dataclass
class SoccerParticipantPayload:
    """Wire identity contract for one soccer participant."""

    participant_id: str
    side: str
    team_id: str
    uniform_number: int
    avatar_kind: str
    display_name: str | None = None
    fish_id: int | None = None
    tank_id: str | None = None
    generation: int | None = None
    parent_id: int | None = None
    policy_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in to_dict(self).items() if value is not None}


@dataclass
class SoccerMatchEventPayload:
    frame: int
    seq: int
    kind: str
    event_id: str | None = None
    side: str | None = None
    actor: str | None = None
    assist: str | None = None
    detail: dict[str, str | int | float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in to_dict(self).items() if value is not None}


# Public wire names used by API consumers.
SoccerParticipant = SoccerParticipantPayload
SoccerMatchEvent = SoccerMatchEventPayload


@dataclass
class SoccerEventPayload:
    frame: int
    match_id: str
    match_counter: int
    winner_team: str | None
    score_left: int
    score_right: int
    frames: int
    seed: int | None = None
    selection_seed: int | None = None
    message: str | None = None
    rewarded: dict[str, float] = field(default_factory=dict)
    entry_fees: dict[str, float] = field(default_factory=dict)
    energy_deltas: dict[str, float] = field(default_factory=dict)
    repro_credit_deltas: dict[str, float] = field(default_factory=dict)
    teams: dict[str, list[int | str]] = field(default_factory=dict)
    last_goal: dict[str, Any] | None = None
    skipped: bool = False
    skip_reason: str | None = None
    # Additive PR 0 match-state contract fields. Legacy fields above remain
    # unchanged for the existing frontend and history consumers.
    participants: list[SoccerParticipantPayload] | None = None
    geometry: dict[str, Any] | None = None
    coord_space: str | None = None
    events: list[SoccerMatchEventPayload] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = to_dict(self)
        if self.participants is not None:
            data["participants"] = [
                participant.to_dict() if hasattr(participant, "to_dict") else participant
                for participant in self.participants
            ]
        if self.events is not None:
            data["events"] = [
                event.to_dict() if hasattr(event, "to_dict") else event for event in self.events
            ]
        return data
