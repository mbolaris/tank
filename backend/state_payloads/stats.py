"""Aggregate ecosystem stats payload (the `stats` block on every frame)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.state_payloads.poker import PokerStatsPayload


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
    diversity_score: float = 0.0

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
            "diversity_score": self.diversity_score,
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
