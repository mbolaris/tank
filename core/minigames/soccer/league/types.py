"""Core types for the Strict Soccer League."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TeamSource(str, Enum):
    """Source of the team (Tank or Bot)."""

    TANK = "tank"
    BOT = "bot"


@dataclass(frozen=True)
class TeamAvailability:
    """Availability status for a team."""

    is_available: bool
    eligible_count: int
    reason: str = "ok"
    min_energy_threshold: float = 0.0


@dataclass(frozen=True)
class LeagueTeam:
    """A team in the soccer league."""

    team_id: str
    display_name: str
    source: TeamSource
    tank_id: str | None = None  # None for bots
    # Legacy alias: older code passed `source_id` into LeagueTeam(...)
    # Keep as optional to remain backwards-compatible.
    source_id: str | None = None
    roster: list[int] = field(default_factory=list)  # List of Entity IDs


@dataclass
class LeagueMatch:
    """A match fixture in the league."""

    match_id: str
    home_team_id: str
    away_team_id: str
    round_index: int
    match_index: int
    home_score: int = 0
    away_score: int = 0
    winner_team_id: str | None = None
    played: bool = False
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class LeagueLeaderboardEntry:
    """Leaderboard statistics for a team."""

    team_id: str
    display_name: str
    source: TeamSource
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    rating: float = 1200.0  # Elo rating

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against
