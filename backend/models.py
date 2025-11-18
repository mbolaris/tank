"""Data models for WebSocket communication."""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


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
    genome_data: Optional[Dict[str, Any]] = None

    # Food-specific fields
    food_type: Optional[str] = None

    # Plant-specific fields
    plant_type: Optional[int] = None


class PokerEventData(BaseModel):
    """A single poker game event."""
    frame: int
    winner_id: int  # -1 for tie
    loser_id: int
    winner_hand: str
    loser_hand: str
    energy_transferred: float
    message: str


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


class Command(BaseModel):
    """Command from client to server."""
    command: str  # 'add_food', 'spawn_fish', 'pause', 'resume', 'reset'
    data: Optional[Dict[str, Any]] = None
