"""Data models for WebSocket communication."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class EntityData(BaseModel):
    """Represents an entity in the simulation."""

    id: int
    type: str  # 'fish', 'food', 'plant', 'crab', 'castle', 'plant', 'plant_nectar'
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

    # Plant-specific fields (original static plants)
    plant_type: Optional[int] = None

    # Fractal plant-specific fields
    genome: Optional[Dict[str, Any]] = None  # L-system genome for rendering
    max_energy: Optional[float] = None
    size_multiplier: Optional[float] = None
    iterations: Optional[int] = None
    nectar_ready: Optional[bool] = None

    # Plant nectar-specific fields
    source_plant_id: Optional[int] = None


class PokerEventData(BaseModel):
    """A single poker game event."""

    frame: int
    winner_id: int  # -1 for tie
    loser_id: int
    winner_hand: str
    loser_hand: str
    energy_transferred: float
    message: str


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


class AutoEvaluatePlayerStats(BaseModel):
    """Player statistics from an auto-evaluation poker series."""

    player_id: str
    name: str
    is_standard: bool
    fish_id: Optional[int] = None
    fish_generation: Optional[int] = None
    plant_id: Optional[int] = None
    species: Optional[str] = "fish"
    energy: float
    hands_won: int
    hands_lost: int
    total_energy_won: float
    total_energy_lost: float
    net_energy: float
    win_rate: Optional[float] = None
    bb_per_100: Optional[float] = None
    showdowns_played: Optional[int] = None
    showdowns_won: Optional[int] = None
    showdown_win_rate: Optional[float] = None


class PokerPerformanceSnapshot(BaseModel):
    """Net energy snapshot for all players after a hand."""

    hand: int
    players: List[Dict[str, Any]]


class AutoEvaluateStats(BaseModel):
    """Aggregate stats for a static benchmark run."""

    hands_played: int
    hands_remaining: int
    players: List[AutoEvaluatePlayerStats]
    game_over: bool
    winner: Optional[str]
    reason: str
    performance_history: List[PokerPerformanceSnapshot] = []


class StatsData(BaseModel):
    """Ecosystem statistics."""

    model_config = ConfigDict(extra="allow")

    frame: int
    population: int
    generation: int
    max_generation: int
    births: int
    deaths: int
    capacity: str
    time: str
    death_causes: Dict[str, int]
    fish_count: int
    food_count: int
    plant_count: int
    total_energy: float
    energy_from_poker_plant: float = 0.0
    energy_burn_recent: Dict[str, float] = {}
    poker_stats: PokerStatsData
    min_fish_energy: float = 0.0
    max_fish_energy: float = 0.0
    poker_score: Optional[float] = None
    poker_score_history: List[float] = []


class SimulationUpdate(BaseModel):
    """Complete simulation state update."""

    type: str = "update"
    frame: int
    elapsed_time: int
    entities: List[EntityData]
    stats: StatsData
    poker_events: List[PokerEventData] = []
    poker_leaderboard: List[PokerLeaderboardEntry] = []
    auto_evaluation: Optional[AutoEvaluateStats] = None


class Command(BaseModel):
    """Command from client to server."""

    command: str  # 'add_food', 'spawn_fish', 'pause', 'resume', 'reset'
    data: Optional[Dict[str, Any]] = None


class ServerInfo(BaseModel):
    """Information about a Tank World Net server.

    Represents a server instance that can host multiple tank simulations.
    In the current single-server implementation, there will only be one server.
    This model is designed to support future multi-server distributed architectures.
    """

    server_id: str  # Unique identifier for this server
    hostname: str  # Hostname or display name
    host: str  # IP address or hostname for connections
    port: int  # Port number for API/WebSocket connections
    status: str  # "online" | "offline" | "degraded"
    world_count: int  # Number of worlds currently running on this server
    version: str  # Server version
    uptime_seconds: float = 0.0  # How long the server has been running
    cpu_percent: Optional[float] = None  # CPU usage percentage (0-100)
    memory_mb: Optional[float] = None  # Memory usage in MB
    is_local: bool = True  # Whether this is the local server
    platform: Optional[str] = None  # OS family name (Linux, Windows, Darwin)
    architecture: Optional[str] = None  # CPU architecture (x86_64, arm64, etc.)
    hardware_model: Optional[str] = None  # Optional hardware descriptor
    logical_cpus: Optional[int] = None  # Logical CPU count for load estimation
    physical_cpus: Optional[int] = None  # Physical core count when available


class ServerWithWorlds(BaseModel):
    """Server information with list of worlds running on it."""

    server: ServerInfo
    worlds: List[Dict[str, Any]]  # List of world status dictionaries


class RemoteTransferRequest(BaseModel):
    """Request body for cross-server entity transfer."""

    destination_world_id: str
    entity_data: Dict[str, Any]
    source_server_id: str
    source_world_id: str
