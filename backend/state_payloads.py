"""Lightweight data transfer objects for simulation state serialization."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Ensure consistent module aliasing whether imported as `state_payloads` or `backend.state_payloads`
sys.modules.setdefault("state_payloads", sys.modules[__name__])
sys.modules.setdefault("backend.state_payloads", sys.modules[__name__])


def _compact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *data* with None values removed."""
    return {k: v for k, v in data.items() if v is not None}


def _to_dict(dataclass_obj: Any) -> Dict[str, Any]:
    """Dictionary representation for slot-based dataclasses without __dict__."""

    return {field.name: getattr(dataclass_obj, field.name) for field in dataclass_obj.__dataclass_fields__.values()}


@dataclass
class EntitySnapshot:
    """Minimal snapshot of an entity for client rendering."""

    id: int
    type: str
    x: float
    y: float
    width: float
    height: float
    vel_x: float = 0.0
    vel_y: float = 0.0
    energy: Optional[float] = None
    generation: Optional[int] = None
    age: Optional[int] = None
    species: Optional[str] = None
    genome_data: Optional[Dict[str, Any]] = None
    food_type: Optional[str] = None
    plant_type: Optional[int] = None
    # Fractal plant fields
    genome: Optional[Dict[str, Any]] = None
    max_energy: Optional[float] = None
    size_multiplier: Optional[float] = None
    iterations: Optional[int] = None
    nectar_ready: Optional[bool] = None
    # Plant nectar fields
    source_plant_id: Optional[int] = None
    source_plant_x: Optional[float] = None
    source_plant_y: Optional[float] = None
    # Floral genome for nectar rendering
    floral_type: Optional[str] = None
    floral_petals: Optional[int] = None
    floral_layers: Optional[int] = None
    floral_spin: Optional[float] = None
    floral_hue: Optional[float] = None
    floral_saturation: Optional[float] = None
    # Poker effects
    poker_effect_state: Optional[Dict[str, Any]] = None
    # Birth effects
    birth_effect_timer: Optional[int] = None

    def to_full_dict(self) -> Dict[str, Any]:
        """Return the full payload used on sync frames."""

        return _compact_dict(
            {
                "id": self.id,
                "type": self.type,
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "vel_x": self.vel_x,
                "vel_y": self.vel_y,
                "energy": self.energy,
                "generation": self.generation,
                "age": self.age,
                "species": self.species,
                "genome_data": self.genome_data,
                "food_type": self.food_type,
                "plant_type": self.plant_type,
                "genome": self.genome,
                "max_energy": self.max_energy,
                "size_multiplier": self.size_multiplier,
                "iterations": self.iterations,
                "nectar_ready": self.nectar_ready,
                "source_plant_id": self.source_plant_id,
                "source_plant_x": self.source_plant_x,
                "source_plant_y": self.source_plant_y,
                "floral_type": self.floral_type,
                "floral_petals": self.floral_petals,
                "floral_layers": self.floral_layers,
                "floral_spin": self.floral_spin,
                "floral_hue": self.floral_hue,
                "floral_saturation": self.floral_saturation,
                "poker_effect_state": self.poker_effect_state,
                "birth_effect_timer": self.birth_effect_timer,
            }
        )

    def to_delta_dict(self) -> Dict[str, Any]:
        """Return only fast-changing fields for delta frames."""

        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "poker_effect_state": self.poker_effect_state,
            "birth_effect_timer": self.birth_effect_timer,
        }


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

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


@dataclass
class StatsPayload:
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
    fish_energy: float  # Total energy of all fish
    plant_energy: float  # Total energy of all plants
    poker_stats: PokerStatsPayload
    fps: float = 0.0
    fast_forward: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = _to_dict(self)
        data["poker_stats"] = self.poker_stats.to_dict()
        return data


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
    plant_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


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

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


@dataclass
class AutoEvaluateStatsPayload:
    hands_played: int
    hands_remaining: int
    players: List[Dict[str, Any]]
    game_over: bool
    winner: Optional[str]
    reason: str
    performance_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


@dataclass
class FullStatePayload:
    """Full snapshot with complete entity data."""

    frame: int
    elapsed_time: int
    entities: List[EntitySnapshot]
    stats: StatsPayload
    poker_events: List[PokerEventPayload]
    poker_leaderboard: List[PokerLeaderboardEntryPayload]
    auto_evaluation: Optional[AutoEvaluateStatsPayload] = None
    type: str = "update"
    tank_id: Optional[str] = None  # Tank World Net identifier

    def to_dict(self) -> Dict[str, Any]:
        return _compact_dict(
            {
                "type": self.type,
                "tank_id": self.tank_id,
                "frame": self.frame,
                "elapsed_time": self.elapsed_time,
                "entities": [e.to_full_dict() for e in self.entities],
                "stats": self.stats.to_dict(),
                "poker_events": [e.to_dict() for e in self.poker_events],
                "poker_leaderboard": [e.to_dict() for e in self.poker_leaderboard],
                "auto_evaluation": self.auto_evaluation.to_dict()
                if self.auto_evaluation
                else None,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass
class DeltaStatePayload:
    """Delta update that only carries incremental changes."""

    frame: int
    elapsed_time: int
    updates: List[Dict[str, Any]]
    added: List[Dict[str, Any]]
    removed: List[int]
    poker_events: List[PokerEventPayload]
    stats: Optional[StatsPayload]
    type: str = "delta"
    tank_id: Optional[str] = None  # Tank World Net identifier

    def to_dict(self) -> Dict[str, Any]:
        return _compact_dict(
            {
                "type": self.type,
                "tank_id": self.tank_id,
                "frame": self.frame,
                "elapsed_time": self.elapsed_time,
                "updates": self.updates,
                "added": self.added,
                "removed": self.removed,
                "poker_events": [e.to_dict() for e in self.poker_events],
                "stats": self.stats.to_dict() if self.stats else None,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))
