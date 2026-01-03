"""Lightweight data transfer objects for simulation state serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

try:  # Prefer faster serializer when available
    import orjson
except ImportError:
    orjson = None


def _compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with None values removed."""
    return {k: v for k, v in data.items() if v is not None}


def _to_dict(dataclass_obj: Any) -> dict[str, Any]:
    """Dictionary representation for dataclasses (slots or regular)."""
    slots = getattr(dataclass_obj, "__slots__", None)
    if slots:
        return {name: getattr(dataclass_obj, name) for name in slots}
    return {
        field.name: getattr(dataclass_obj, field.name)
        for field in dataclass_obj.__dataclass_fields__.values()
    }


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
    energy: float | None = None
    generation: int | None = None
    age: int | None = None
    species: str | None = None
    genome_data: dict[str, Any] | None = None
    food_type: str | None = None
    plant_type: int | None = None
    # Fractal plant fields
    genome: dict[str, Any] | None = None
    max_energy: float | None = None
    size_multiplier: float | None = None
    iterations: int | None = None
    nectar_ready: bool | None = None
    # Plant nectar fields
    source_plant_id: int | None = None
    source_plant_x: float | None = None
    source_plant_y: float | None = None
    # Floral genome for nectar rendering
    floral_type: str | None = None
    floral_petals: int | None = None
    floral_layers: int | None = None
    floral_spin: float | None = None
    floral_hue: float | None = None
    floral_saturation: float | None = None
    # Poker effects
    poker_effect_state: dict[str, Any] | None = None
    # Birth effects
    birth_effect_timer: int | None = None
    # Death effects
    death_effect_state: dict[str, Any] | None = None
    # Crab hunt state
    can_hunt: bool | None = None
    # Rendering metadata hints
    render_hint: dict[str, Any] | None = None

    def to_full_dict(self) -> dict[str, Any]:
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
        if self.death_effect_state is not None:
            data["death_effect_state"] = self.death_effect_state
        if self.can_hunt is not None:
            data["can_hunt"] = self.can_hunt
        if self.render_hint is not None:
            data["render_hint"] = self.render_hint

        return data

    def to_delta_dict(self) -> dict[str, Any]:
        """Return only fast-changing fields for delta frames."""

        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "poker_effect_state": self.poker_effect_state,
            "birth_effect_timer": self.birth_effect_timer,
            "death_effect_state": self.death_effect_state,
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
    death_causes: dict[str, int]
    fish_count: int
    food_count: int
    plant_count: int
    total_energy: float
    food_energy: float  # Total energy of all regular food
    live_food_count: int
    live_food_energy: float  # Total energy of all live food
    fish_energy: float  # Total energy of all fish
    plant_energy: float  # Total energy of all plants
    energy_sources: dict[str, float] = field(default_factory=dict)
    energy_sources_recent: dict[str, float] = field(default_factory=dict)
    energy_from_nectar: float = 0.0
    energy_from_live_food: float = 0.0
    energy_from_falling_food: float = 0.0
    energy_from_poker: float = 0.0
    energy_from_poker_plant: float = 0.0
    energy_from_auto_eval: float = 0.0
    energy_burn_recent: dict[str, float] = field(default_factory=dict)
    energy_burn_total: float = 0.0
    # Fish energy accounting reconciliation (recent window)
    energy_gains_recent_total: float = 0.0
    energy_net_recent: float = 0.0
    energy_accounting_discrepancy: float = 0.0
    # Plant energy economy (separate pool from fish)
    plant_energy_sources: dict[str, float] = field(default_factory=dict)
    plant_energy_sources_recent: dict[str, float] = field(default_factory=dict)
    plant_energy_from_photosynthesis: float = 0.0
    plant_energy_burn_recent: dict[str, float] = field(default_factory=dict)
    plant_energy_burn_total: float = 0.0
    # Energy delta (true change in fish population energy over window)
    energy_delta: dict[str, Any] = field(default_factory=dict)
    # Fish energy distribution
    avg_fish_energy: float = 0.0
    min_fish_energy: float = 0.0
    max_fish_energy: float = 0.0
    # Max Energy Capacity Stats (Genetic)
    min_max_energy_capacity: float = 0.0
    max_max_energy_capacity: float = 0.0
    median_max_energy_capacity: float = 0.0
    # Fish health status counts (by energy ratio)
    fish_health_critical: int = 0  # <15% energy
    fish_health_low: int = 0  # 15-30% energy
    fish_health_healthy: int = 0  # 30-80% energy
    fish_health_full: int = 0  # >80% energy
    # Adult size statistics (multipliers / absolute sizes)
    adult_size_min: float = 0.0
    adult_size_max: float = 0.0
    adult_size_median: float = 0.0
    adult_size_range: str = ""
    allowed_adult_size_min: float = 0.0
    allowed_adult_size_max: float = 0.0
    # Histogram bins and edges for adult size distribution
    adult_size_bins: list[int] = field(default_factory=list)
    adult_size_bin_edges: list[float] = field(default_factory=list)
    # Eye size statistics
    eye_size_min: float = 0.0
    eye_size_max: float = 0.0
    eye_size_median: float = 0.0
    eye_size_bins: list[int] = field(default_factory=list)
    eye_size_bin_edges: list[float] = field(default_factory=list)
    allowed_eye_size_min: float = 0.0
    allowed_eye_size_max: float = 0.0
    # Fin size statistics
    fin_size_min: float = 0.0
    fin_size_max: float = 0.0
    fin_size_median: float = 0.0
    fin_size_bins: list[int] = field(default_factory=list)
    fin_size_bin_edges: list[float] = field(default_factory=list)
    allowed_fin_size_min: float = 0.0
    allowed_fin_size_max: float = 0.0
    # Tail size statistics
    tail_size_min: float = 0.0
    tail_size_max: float = 0.0
    tail_size_median: float = 0.0
    allowed_tail_size_min: float = 0.0
    allowed_tail_size_max: float = 0.0
    tail_size_bins: list[int] = field(default_factory=list)
    tail_size_bin_edges: list[float] = field(default_factory=list)
    # Body aspect statistics
    body_aspect_min: float = 0.0
    body_aspect_max: float = 0.0
    body_aspect_median: float = 0.0
    allowed_body_aspect_min: float = 0.0
    allowed_body_aspect_max: float = 0.0
    body_aspect_bins: list[int] = field(default_factory=list)
    body_aspect_bin_edges: list[float] = field(default_factory=list)
    # Template ID statistics
    template_id_min: float = 0.0
    template_id_max: float = 0.0
    template_id_median: float = 0.0
    allowed_template_id_min: float = 0.0
    allowed_template_id_max: float = 0.0
    template_id_bins: list[int] = field(default_factory=list)
    template_id_bin_edges: list[float] = field(default_factory=list)
    # Pattern type statistics
    pattern_type_min: float = 0.0
    pattern_type_max: float = 0.0
    pattern_type_median: float = 0.0
    allowed_pattern_type_min: float = 0.0
    allowed_pattern_type_max: float = 0.0
    pattern_type_bins: list[int] = field(default_factory=list)
    pattern_type_bin_edges: list[float] = field(default_factory=list)
    # Pattern intensity statistics
    pattern_intensity_min: float = 0.0
    pattern_intensity_max: float = 0.0
    pattern_intensity_median: float = 0.0
    allowed_pattern_intensity_min: float = 0.0
    allowed_pattern_intensity_max: float = 0.0
    pattern_intensity_bins: list[int] = field(default_factory=list)
    pattern_intensity_bin_edges: list[float] = field(default_factory=list)
    # Lifespan modifier statistics
    lifespan_modifier_min: float = 0.0
    lifespan_modifier_max: float = 0.0
    lifespan_modifier_median: float = 0.0
    allowed_lifespan_modifier_min: float = 0.0
    allowed_lifespan_modifier_max: float = 0.0
    lifespan_modifier_bins: list[int] = field(default_factory=list)
    lifespan_modifier_bin_edges: list[float] = field(default_factory=list)
    # Dynamic gene distributions (physical + behavioral), for dashboards
    gene_distributions: dict[str, Any] = field(default_factory=dict)
    poker_stats: PokerStatsPayload = field(
        default_factory=lambda: PokerStatsPayload(
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
        )
    )
    poker_score: float | None = None
    poker_score_history: list[float] = field(default_factory=list)
    poker_elo: float | None = None
    poker_elo_history: list[float] = field(default_factory=list)
    meta_stats: dict[str, float] = field(default_factory=dict)
    total_sexual_births: int = 0
    total_asexual_births: int = 0
    fps: float = 0.0
    fast_forward: bool = False

    def to_dict(self) -> dict[str, Any]:
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
            "energy_gains_recent_total": self.energy_gains_recent_total,
            "energy_net_recent": self.energy_net_recent,
            "energy_accounting_discrepancy": self.energy_accounting_discrepancy,
            "plant_energy_sources": self.plant_energy_sources,
            "plant_energy_sources_recent": self.plant_energy_sources_recent,
            "plant_energy_from_photosynthesis": self.plant_energy_from_photosynthesis,
            "plant_energy_burn_recent": self.plant_energy_burn_recent,
            "plant_energy_burn_total": self.plant_energy_burn_total,
            "energy_delta": self.energy_delta,
            "avg_fish_energy": self.avg_fish_energy,
            "min_fish_energy": self.min_fish_energy,
            "max_fish_energy": self.max_fish_energy,
            "min_max_energy_capacity": self.min_max_energy_capacity,
            "max_max_energy_capacity": self.max_max_energy_capacity,
            "median_max_energy_capacity": self.median_max_energy_capacity,
            "fish_health_critical": self.fish_health_critical,
            "fish_health_low": self.fish_health_low,
            "fish_health_healthy": self.fish_health_healthy,
            "fish_health_full": self.fish_health_full,
            # Adult size fields
            "adult_size_min": self.adult_size_min,
            "adult_size_max": self.adult_size_max,
            "adult_size_median": self.adult_size_median,
            "adult_size_range": self.adult_size_range,
            "allowed_adult_size_min": self.allowed_adult_size_min,
            "allowed_adult_size_max": self.allowed_adult_size_max,
            "adult_size_bins": self.adult_size_bins,
            "adult_size_bin_edges": self.adult_size_bin_edges,
            # Eye size fields
            "eye_size_min": self.eye_size_min,
            "eye_size_max": self.eye_size_max,
            "eye_size_median": self.eye_size_median,
            "eye_size_bins": self.eye_size_bins,
            "eye_size_bin_edges": self.eye_size_bin_edges,
            "allowed_eye_size_min": self.allowed_eye_size_min,
            "allowed_eye_size_max": self.allowed_eye_size_max,
            # Fin size fields
            "fin_size_min": self.fin_size_min,
            "fin_size_max": self.fin_size_max,
            "fin_size_median": self.fin_size_median,
            "fin_size_bins": self.fin_size_bins,
            "fin_size_bin_edges": self.fin_size_bin_edges,
            "allowed_fin_size_min": self.allowed_fin_size_min,
            "allowed_fin_size_max": self.allowed_fin_size_max,
            # Tail size fields
            "tail_size_min": self.tail_size_min,
            "tail_size_max": self.tail_size_max,
            "tail_size_median": self.tail_size_median,
            "allowed_tail_size_min": self.allowed_tail_size_min,
            "allowed_tail_size_max": self.allowed_tail_size_max,
            "tail_size_bins": self.tail_size_bins,
            "tail_size_bin_edges": self.tail_size_bin_edges,
            # Body aspect fields
            "body_aspect_min": self.body_aspect_min,
            "body_aspect_max": self.body_aspect_max,
            "body_aspect_median": self.body_aspect_median,
            "allowed_body_aspect_min": self.allowed_body_aspect_min,
            "allowed_body_aspect_max": self.allowed_body_aspect_max,
            "body_aspect_bins": self.body_aspect_bins,
            "body_aspect_bin_edges": self.body_aspect_bin_edges,
            # Template ID fields
            "template_id_min": self.template_id_min,
            "template_id_max": self.template_id_max,
            "template_id_median": self.template_id_median,
            "allowed_template_id_min": self.allowed_template_id_min,
            "allowed_template_id_max": self.allowed_template_id_max,
            "template_id_bins": self.template_id_bins,
            "template_id_bin_edges": self.template_id_bin_edges,
            # Pattern type fields
            "pattern_type_min": self.pattern_type_min,
            "pattern_type_max": self.pattern_type_max,
            "pattern_type_median": self.pattern_type_median,
            "allowed_pattern_type_min": self.allowed_pattern_type_min,
            "allowed_pattern_type_max": self.allowed_pattern_type_max,
            "pattern_type_bins": self.pattern_type_bins,
            "pattern_type_bin_edges": self.pattern_type_bin_edges,
            # Pattern intensity fields
            "pattern_intensity_min": self.pattern_intensity_min,
            "pattern_intensity_max": self.pattern_intensity_max,
            "pattern_intensity_median": self.pattern_intensity_median,
            "allowed_pattern_intensity_min": self.allowed_pattern_intensity_min,
            "allowed_pattern_intensity_max": self.allowed_pattern_intensity_max,
            "pattern_intensity_bins": self.pattern_intensity_bins,
            "pattern_intensity_bin_edges": self.pattern_intensity_bin_edges,
            # Lifespan modifier fields
            "lifespan_modifier_min": self.lifespan_modifier_min,
            "lifespan_modifier_max": self.lifespan_modifier_max,
            "lifespan_modifier_median": self.lifespan_modifier_median,
            "allowed_lifespan_modifier_min": self.allowed_lifespan_modifier_min,
            "allowed_lifespan_modifier_max": self.allowed_lifespan_modifier_max,
            "lifespan_modifier_bins": self.lifespan_modifier_bins,
            "lifespan_modifier_bin_edges": self.lifespan_modifier_bin_edges,
            "gene_distributions": self.gene_distributions,
            "total_sexual_births": self.total_sexual_births,
            "total_asexual_births": self.total_asexual_births,
            "fps": self.fps,
            "fast_forward": self.fast_forward,
        }

        data["poker_stats"] = self.poker_stats.to_dict()
        if self.poker_score is not None:
            data["poker_score"] = self.poker_score
        if self.poker_score_history:
            data["poker_score_history"] = self.poker_score_history
        if self.poker_elo is not None:
            data["poker_elo"] = self.poker_elo
        if self.poker_elo_history:
            data["poker_elo_history"] = self.poker_elo_history
        if self.meta_stats:
            data.update(self.meta_stats)
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
    plant_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
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

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


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
        return _to_dict(self)


@dataclass
class FullStatePayload:
    """Full snapshot with complete entity data."""

    frame: int
    elapsed_time: int
    entities: list[EntitySnapshot]
    stats: StatsPayload
    poker_events: list[PokerEventPayload]
    poker_leaderboard: list[PokerLeaderboardEntryPayload]
    auto_evaluation: AutoEvaluateStatsPayload | None = None
    type: str = "update"
    tank_id: str | None = None  # Tank World Net identifier
    mode_id: str | None = "tank"
    world_type: str | None = "tank"
    view_mode: str | None = "side"

    def to_dict(self) -> dict[str, Any]:
        # Build snapshot containing all simulation state
        snapshot = {
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "entities": [e.to_full_dict() for e in self.entities],
            "stats": self.stats.to_dict(),
            "poker_events": [e.to_dict() for e in self.poker_events],
            "poker_leaderboard": [e.to_dict() for e in self.poker_leaderboard],
        }
        if self.auto_evaluation:
            snapshot["auto_evaluation"] = self.auto_evaluation.to_dict()

        # Top-level payload with metadata and nested snapshot
        data: dict[str, Any] = {
            "type": self.type,
            "snapshot": snapshot,
        }
        if self.tank_id is not None:
            data["tank_id"] = self.tank_id
        if self.mode_id is not None:
            data["mode_id"] = self.mode_id
        if self.world_type is not None:
            data["world_type"] = self.world_type
        if self.view_mode is not None:
            data["view_mode"] = self.view_mode
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
    updates: list[dict[str, Any]]
    added: list[dict[str, Any]]
    removed: list[int]
    poker_events: list[PokerEventPayload] | None = None
    stats: StatsPayload | None = None
    type: str = "delta"
    tank_id: str | None = None  # Tank World Net identifier
    mode_id: str | None = "tank"
    world_type: str | None = "tank"
    view_mode: str | None = "side"

    def to_dict(self) -> dict[str, Any]:
        # Build snapshot containing delta simulation state
        snapshot: dict[str, Any] = {
            "frame": self.frame,
            "elapsed_time": self.elapsed_time,
            "updates": self.updates,
            "added": self.added,
            "removed": self.removed,
        }
        if self.poker_events is not None:
            snapshot["poker_events"] = [e.to_dict() for e in self.poker_events]
        if self.stats:
            snapshot["stats"] = self.stats.to_dict()

        # Top-level payload with metadata and nested snapshot
        data: dict[str, Any] = {
            "type": self.type,
            "snapshot": snapshot,
        }
        if self.tank_id is not None:
            data["tank_id"] = self.tank_id
        if self.mode_id is not None:
            data["mode_id"] = self.mode_id
        if self.world_type is not None:
            data["world_type"] = self.world_type
        if self.view_mode is not None:
            data["view_mode"] = self.view_mode
        return data

    def to_json(self) -> str:
        data = self.to_dict()
        if orjson:
            return orjson.dumps(data).decode("utf-8")
        return json.dumps(data, separators=(",", ":"))
