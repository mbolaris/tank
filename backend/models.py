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
    species: Optional[str] = None  # 'solo', 'algorithmic', 'neural', 'schooling'
    generation: Optional[int] = None
    age: Optional[int] = None
    genome_data: Optional[Dict[str, Any]] = None

    # Food-specific fields
    food_type: Optional[str] = None

    # Plant-specific fields
    plant_type: Optional[int] = None


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
    poker_stats: PokerStatsData


class SimulationUpdate(BaseModel):
    """Complete simulation state update."""
    type: str = "update"
    frame: int
    elapsed_time: int
    entities: List[EntityData]
    stats: StatsData


class Command(BaseModel):
    """Command from client to server."""
    command: str  # 'add_food', 'pause', 'resume', 'reset'
    data: Optional[Dict[str, Any]] = None
