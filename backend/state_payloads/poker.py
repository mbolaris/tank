"""Poker-related wire payloads: stats, hand events, leaderboard, auto-eval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.state_payloads._common import to_dict


@dataclass
class PokerStatsPayload:
    total_games: int
    total_fish_games: int
    total_plant_games: int
    total_plant_energy_transferred: float
    total_wins: int
    total_losses: int
    total_ties: int
    total_energy_won: float
    total_energy_lost: float
    net_energy: float
    best_hand_rank: int
    best_hand_name: str
    # Plant vs fish win tracking
    plant_poker_wins: int = 0
    fish_poker_wins: int = 0
    plant_win_rate: float = 0.0
    plant_win_rate_pct: str = "0.0%"
    win_rate: float = 0.0
    win_rate_pct: str = "0.0%"
    roi: float = 0.0
    vpip: float = 0.0
    vpip_pct: str = "0.0%"
    bluff_success_rate: float = 0.0
    bluff_success_pct: str = "0.0%"
    button_win_rate: float = 0.0
    button_win_rate_pct: str = "0.0%"
    off_button_win_rate: float = 0.0
    off_button_win_rate_pct: str = "0.0%"
    positional_advantage: float = 0.0
    positional_advantage_pct: str = "0.0%"
    aggression_factor: float = 0.0
    avg_hand_rank: float = 0.0
    total_folds: int = 0
    preflop_folds: int = 0
    postflop_folds: int = 0
    showdown_win_rate: str = "0.0%"
    avg_fold_rate: str = "0.0%"

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class PokerEventPayload:
    frame: int
    winner_id: int
    loser_id: int
    winner_hand: str
    loser_hand: str
    energy_transferred: float
    message: str
    is_plant: bool = False
    plant_id: int | None = None
    # Per-fish reward detail (keys are stringified fish ids)
    energy_deltas: dict[str, float] = field(default_factory=dict)
    pot: float = 0.0
    house_cut: float = 0.0
    reproduction: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class PokerLeaderboardEntryPayload:
    rank: int
    fish_id: int
    generation: int
    algorithm: str
    energy: float
    age: int
    total_games: int
    wins: int
    losses: int
    ties: int
    win_rate: float
    net_energy: float
    roi: float
    current_streak: int
    best_streak: int
    best_hand: str
    best_hand_rank: int
    showdown_win_rate: float
    fold_rate: float
    positional_advantage: float
    recent_win_rate: float = 0.0
    skill_trend: str = "stable"
    tank_name: str = "Unknown Tank"
    tank_id: str = "unknown"
    offspring_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class AutoEvaluateStatsPayload:
    hands_played: int
    hands_remaining: int
    players: list[dict[str, Any]]
    game_over: bool
    winner: str | None
    reason: str
    performance_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)
