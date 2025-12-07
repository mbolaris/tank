"""Lightweight data transfer objects for simulation state serialization."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Ensure consistent module aliasing whether imported as `state_payloads` or `backend.state_payloads`
sys.modules.setdefault("state_payloads", sys.modules[__name__])
sys.modules.setdefault("backend.state_payloads", sys.modules[__name__])

try:  # Prefer faster serializer when available
    import orjson
except ImportError:
    orjson = None


def _compact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *data* with None values removed."""
    return {k: v for k, v in data.items() if v is not None}


def _to_dict(dataclass_obj: Any) -> Dict[str, Any]:
    """Dictionary representation for dataclasses (slots or regular)."""
    slots = getattr(dataclass_obj, "__slots__", None)
    if slots:
        return {name: getattr(dataclass_obj, name) for name in slots}
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
    # Crab hunt state
    can_hunt: Optional[bool] = None

    def to_full_dict(self) -> Dict[str, Any]:
        """Return the full payload used on sync frames."""

        data = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
        }

        if self.energy is not None:
            data["energy"] = self.energy
        if self.generation is not None:
            data["generation"] = self.generation
        if self.age is not None:
            data["age"] = self.age
        if self.species is not None:
            data["species"] = self.species
        if self.genome_data is not None:
            data["genome_data"] = self.genome_data
        if self.food_type is not None:
            data["food_type"] = self.food_type
        if self.plant_type is not None:
            data["plant_type"] = self.plant_type
        if self.genome is not None:
            data["genome"] = self.genome
        if self.max_energy is not None:
            data["max_energy"] = self.max_energy
        if self.size_multiplier is not None:
            data["size_multiplier"] = self.size_multiplier
        if self.iterations is not None:
            data["iterations"] = self.iterations
        if self.nectar_ready is not None:
            data["nectar_ready"] = self.nectar_ready
        if self.source_plant_id is not None:
            data["source_plant_id"] = self.source_plant_id
        if self.source_plant_x is not None:
            data["source_plant_x"] = self.source_plant_x
        if self.source_plant_y is not None:
            data["source_plant_y"] = self.source_plant_y
        if self.floral_type is not None:
            data["floral_type"] = self.floral_type
        if self.floral_petals is not None:
            data["floral_petals"] = self.floral_petals
        if self.floral_layers is not None:
            data["floral_layers"] = self.floral_layers
        if self.floral_spin is not None:
            data["floral_spin"] = self.floral_spin
        if self.floral_hue is not None:
            data["floral_hue"] = self.floral_hue
        if self.floral_saturation is not None:
            data["floral_saturation"] = self.floral_saturation
        if self.poker_effect_state is not None:
            data["poker_effect_state"] = self.poker_effect_state
        if self.birth_effect_timer is not None:
            data["birth_effect_timer"] = self.birth_effect_timer
        if self.can_hunt is not None:
            data["can_hunt"] = self.can_hunt

        return data

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
    food_energy: float  # Total energy of all regular food
    live_food_count: int
    live_food_energy: float  # Total energy of all live food
    fish_energy: float  # Total energy of all fish
    plant_energy: float  # Total energy of all plants
    energy_sources: Dict[str, float] = field(default_factory=dict)
    energy_sources_recent: Dict[str, float] = field(default_factory=dict)
    energy_from_nectar: float = 0.0
    energy_from_live_food: float = 0.0
    energy_from_falling_food: float = 0.0
    energy_from_poker: float = 0.0
    energy_from_poker_plant: float = 0.0
    energy_from_auto_eval: float = 0.0
    energy_burn_recent: Dict[str, float] = field(default_factory=dict)
    energy_burn_total: float = 0.0
    # Fish energy distribution
    avg_fish_energy: float = 0.0
    min_fish_energy: float = 0.0
    max_fish_energy: float = 0.0
    # Fish health status counts (by energy ratio)
    fish_health_critical: int = 0  # <15% energy
    fish_health_low: int = 0       # 15-30% energy
    fish_health_healthy: int = 0   # 30-80% energy
    fish_health_full: int = 0      # >80% energy
    poker_stats: PokerStatsPayload = field(default_factory=lambda: PokerStatsPayload(
        total_games=0,
        total_fish_games=0,
        total_plant_games=0,
        total_plant_energy_transferred=0.0,
        total_wins=0,
        total_losses=0,
        total_ties=0,
        total_energy_won=0.0,
        total_energy_lost=0.0,
        net_energy=0.0,
        best_hand_rank=0,
        best_hand_name="",
    ))
    total_sexual_births: int = 0
    total_asexual_births: int = 0
    fps: float = 0.0
    fast_forward: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "frame": self.frame,
            "population": self.population,
            "generation": self.generation,
            "max_generation": self.max_generation,
            "births": self.births,
            "deaths": self.deaths,
            "capacity": self.capacity,
            "time": self.time,
            "death_causes": self.death_causes,
            "fish_count": self.fish_count,
            "food_count": self.food_count,
            "plant_count": self.plant_count,
            "total_energy": self.total_energy,
            "food_energy": self.food_energy,
            "live_food_count": self.live_food_count,
            "live_food_energy": self.live_food_energy,
            "fish_energy": self.fish_energy,
            "plant_energy": self.plant_energy,
            "energy_sources": self.energy_sources,
            "energy_sources_recent": self.energy_sources_recent,
            "energy_from_nectar": self.energy_from_nectar,
            "energy_from_live_food": self.energy_from_live_food,
            "energy_from_falling_food": self.energy_from_falling_food,
            "energy_from_poker": self.energy_from_poker,
            "energy_from_poker_plant": self.energy_from_poker_plant,
            "energy_from_auto_eval": self.energy_from_auto_eval,
            "energy_burn_recent": self.energy_burn_recent,
            "energy_burn_total": self.energy_burn_total,
            "avg_fish_energy": self.avg_fish_energy,
            "min_fish_energy": self.min_fish_energy,
            "max_fish_energy": self.max_fish_energy,
            "fish_health_critical": self.fish_health_critical,
            "fish_health_low": self.fish_health_low,
            "fish_health_healthy": self.fish_health_healthy,
            "fish_health_full": self.fish_health_full,
            "total_sexual_births": self.total_sexual_births,
            "total_asexual_births": self.total_asexual_births,
            "fps": self.fps,
            "fast_forward": self.fast_forward,
        }

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
        data = {
            "type": self.type,
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "entities": [e.to_full_dict() for e in self.entities],
            "stats": self.stats.to_dict(),
            "poker_events": [e.to_dict() for e in self.poker_events],
            "poker_leaderboard": [e.to_dict() for e in self.poker_leaderboard],
        }
        if self.tank_id is not None:
            data["tank_id"] = self.tank_id
        if self.auto_evaluation:
            data["auto_evaluation"] = self.auto_evaluation.to_dict()
        return data

    def to_json(self) -> str:
        data = self.to_dict()
        if orjson:
            return orjson.dumps(data).decode("utf-8")
        return json.dumps(data, separators=(",", ":"))


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
        data = {
            "type": self.type,
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "updates": self.updates,
            "added": self.added,
            "removed": self.removed,
            "poker_events": [e.to_dict() for e in self.poker_events],
        }
        if self.tank_id is not None:
            data["tank_id"] = self.tank_id
        if self.stats:
            data["stats"] = self.stats.to_dict()
        return data

    def to_json(self) -> str:
        data = self.to_dict()
        if orjson:
            return orjson.dumps(data).decode("utf-8")
        return json.dumps(data, separators=(",", ":"))
