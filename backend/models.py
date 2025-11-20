"""Data models for WebSocket communication."""

import sys
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# Ensure consistent module aliasing whether imported as `models` or `backend.models`
sys.modules.setdefault("models", sys.modules[__name__])
sys.modules.setdefault("backend.models", sys.modules[__name__])


class EntityData(BaseModel):
    """Represents an entity in the simulation."""

    id: int
    type: str  # 'fish', 'food', 'plant', 'crab', 'castle'
    x: float
    y: float
    width: float
    height: float

    # Velocity for animation
    vel_x: Optional[float] = None
    vel_y: Optional[float] = None

    # Fish-specific fields
    energy: Optional[float] = None
    generation: Optional[int] = None
    age: Optional[int] = None
    species: Optional[str] = None
    genome_data: Optional[Dict[str, Any]] = None

    # Food-specific fields
    food_type: Optional[str] = None

    # Plant-specific fields
    plant_type: Optional[int] = None


class PokerEventData(BaseModel):
    """A single poker game event."""

    frame: int
    winner_id: int  # -1 for tie, -2 for jellyfish
    loser_id: int  # -2 for jellyfish
    winner_hand: str
    loser_hand: str
    energy_transferred: float
    message: str
    is_jellyfish: bool = False


class PokerLeaderboardEntry(BaseModel):
    """A single entry in the poker leaderboard."""

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
    win_rate: float  # Percentage (0-100)
    net_energy: float
    roi: float
    current_streak: int
    best_streak: int
    best_hand: str
    best_hand_rank: int
    showdown_win_rate: float  # Percentage (0-100)
    fold_rate: float  # Percentage (0-100)
    positional_advantage: float  # Percentage (0-100)
    recent_win_rate: float = 0.0  # Recent win rate (0-100)
    skill_trend: str = "stable"  # "improving", "declining", or "stable"


class PokerStatsData(BaseModel):
    """Poker game statistics."""

    total_games: int
    total_wins: int
    total_losses: int
    total_ties: int
    total_energy_won: float
    total_energy_lost: float
    net_energy: float
    best_hand_rank: int
    best_hand_name: str
    # Advanced metrics for evaluating poker skill
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


class StatsData(BaseModel):
    """Ecosystem statistics."""

    frame: int
    population: int
    generation: int
    births: int
    deaths: int
    capacity: str
    time: str
    death_causes: Dict[str, int]
    fish_count: int
    food_count: int
    plant_count: int
    total_energy: float
    poker_stats: PokerStatsData


class SimulationUpdate(BaseModel):
    """Complete simulation state update."""

    type: str = "update"
    frame: int
    elapsed_time: int
    entities: List[EntityData]
    stats: StatsData
    poker_events: List[PokerEventData] = []
    poker_leaderboard: List[PokerLeaderboardEntry] = []


class Command(BaseModel):
    """Command from client to server."""

    command: str  # 'add_food', 'spawn_fish', 'pause', 'resume', 'reset'
    data: Optional[Dict[str, Any]] = None
