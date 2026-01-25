"""Shared dataclasses for soccer evaluation outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.minigames.soccer.match import SoccerMatch


@dataclass
class PlayerTelemetry:
    """Per-player telemetry for a soccer match.

    All values are deterministic and derived from engine state each cycle.
    """

    player_id: str
    team: str
    touches: int = 0  # Number of times player kicked the ball
    kicks: int = 0  # Alias for touches (kick is the only way to touch)
    distance_run: float = 0.0  # Approximate distance traveled (sum of position deltas)


@dataclass
class TeamTelemetry:
    """Per-team telemetry for a soccer match.

    All values are deterministic and derived from engine state each cycle.
    """

    team: str
    possession_frames: int = 0  # Cycles where team had last touch
    touches: int = 0  # Total touches by team
    shots: int = 0  # Kicks toward opponent goal (within angle threshold)
    shots_on_target: int = 0  # Shots that would score if not blocked
    ball_progress: float = 0.0  # Net x-displacement of ball toward opponent goal
    goals: int = 0


@dataclass
class SoccerTelemetry:
    """Complete telemetry for a soccer match.

    This is deterministic: same seed produces identical telemetry.
    Useful for evolution fitness shaping beyond sparse goal rewards.
    """

    teams: dict[str, TeamTelemetry] = field(default_factory=dict)
    players: dict[str, PlayerTelemetry] = field(default_factory=dict)
    total_cycles: int = 0

    def get_team(self, team: str) -> TeamTelemetry:
        """Get or create team telemetry."""
        if team not in self.teams:
            self.teams[team] = TeamTelemetry(team=team)
        return self.teams[team]

    def get_player(self, player_id: str, team: str) -> PlayerTelemetry:
        """Get or create player telemetry."""
        if player_id not in self.players:
            self.players[player_id] = PlayerTelemetry(player_id=player_id, team=team)
        return self.players[player_id]


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
    last_goal: dict[str, Any] | None = None
    telemetry: SoccerTelemetry | None = None


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
