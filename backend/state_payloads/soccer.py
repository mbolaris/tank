"""Soccer minigame wire payload (per-match event)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.state_payloads._common import to_dict


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
    teams: dict[str, list[int]] = field(default_factory=dict)
    last_goal: dict[str, Any] | None = None
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)
