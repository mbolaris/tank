"""Shared dataclasses for soccer evaluation outputs."""

from __future__ import annotations

from dataclasses import dataclass

from core.minigames.soccer.match import SoccerMatch


@dataclass(frozen=True)
class SoccerMinigameOutcome:
    """Summary of a completed soccer minigame run."""

    match_id: str
    match_counter: int
    winner_team: str | None
    score_left: int
    score_right: int
    frames: int
    seed: int | None
    selection_seed: int | None
    message: str
    rewarded: dict[str, float]
    entry_fees: dict[int, float]
    energy_deltas: dict[int, float]
    repro_credit_deltas: dict[int, float]
    teams: dict[str, list[int]]
    skipped: bool = False
    skip_reason: str = ""


@dataclass(frozen=True)
class SoccerMatchSetup:
    """Created match plus deterministic metadata for logging."""

    match: SoccerMatch
    seed: int | None
    match_id: str
    selected_count: int
    match_counter: int
    selection_seed: int | None
    entry_fees: dict[int, float]
