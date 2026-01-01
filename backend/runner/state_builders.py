"""State serialization helpers for SimulationRunner.

This module contains functions for building state payloads for WebSocket broadcast.
Extracted from SimulationRunner to reduce class size.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.state_payloads import (
    PokerStatsPayload,
)

if TYPE_CHECKING:
    pass


def collect_poker_stats_payload(stats: Dict[str, Any]) -> PokerStatsPayload:
    """Create PokerStatsPayload from stats dictionary."""
    poker_stats_dict = stats.get("poker_stats", {})
    return PokerStatsPayload(
        total_games=poker_stats_dict.get("total_games", 0),
        total_fish_games=poker_stats_dict.get("total_fish_games", 0),
        total_plant_games=poker_stats_dict.get("total_plant_games", 0),
        total_plant_energy_transferred=poker_stats_dict.get("total_plant_energy_transferred", 0.0),
        total_wins=poker_stats_dict.get("total_wins", 0),
        total_losses=poker_stats_dict.get("total_losses", 0),
        total_ties=poker_stats_dict.get("total_ties", 0),
        total_energy_won=poker_stats_dict.get("total_energy_won", 0.0),
        total_energy_lost=poker_stats_dict.get("total_energy_lost", 0.0),
        net_energy=poker_stats_dict.get("net_energy", 0.0),
        best_hand_rank=poker_stats_dict.get("best_hand_rank", 0),
        best_hand_name=poker_stats_dict.get("best_hand_name", "None"),
        # Plant vs fish win tracking
        plant_poker_wins=poker_stats_dict.get("plant_poker_wins", 0),
        fish_poker_wins=poker_stats_dict.get("fish_poker_wins", 0),
        plant_win_rate=poker_stats_dict.get("plant_win_rate", 0.0),
        plant_win_rate_pct=poker_stats_dict.get("plant_win_rate_pct", "0.0%"),
        win_rate=poker_stats_dict.get("win_rate", 0.0),
        win_rate_pct=poker_stats_dict.get("win_rate_pct", "0.0%"),
        roi=poker_stats_dict.get("roi", 0.0),
        vpip=poker_stats_dict.get("vpip", 0.0),
        vpip_pct=poker_stats_dict.get("vpip_pct", "0.0%"),
        bluff_success_rate=poker_stats_dict.get("bluff_success_rate", 0.0),
        bluff_success_pct=poker_stats_dict.get("bluff_success_pct", "0.0%"),
        button_win_rate=poker_stats_dict.get("button_win_rate", 0.0),
        button_win_rate_pct=poker_stats_dict.get("button_win_rate_pct", "0.0%"),
        off_button_win_rate=poker_stats_dict.get("off_button_win_rate", 0.0),
        off_button_win_rate_pct=poker_stats_dict.get("off_button_win_rate_pct", "0.0%"),
        positional_advantage=poker_stats_dict.get("positional_advantage", 0.0),
        positional_advantage_pct=poker_stats_dict.get("positional_advantage_pct", "0.0%"),
        aggression_factor=poker_stats_dict.get("aggression_factor", 0.0),
        avg_hand_rank=poker_stats_dict.get("avg_hand_rank", 0.0),
        total_folds=poker_stats_dict.get("total_folds", 0),
        preflop_folds=poker_stats_dict.get("preflop_folds", 0),
        postflop_folds=poker_stats_dict.get("postflop_folds", 0),
        showdown_win_rate=poker_stats_dict.get("showdown_win_rate", "0.0%"),
        avg_fold_rate=poker_stats_dict.get("avg_fold_rate", "0.0%"),
    )


def build_base_stats(
    stats: Dict[str, Any],
    frame: int,
    fps: float,
    fast_forward: bool,
) -> Dict[str, Any]:
    """Build base simulation stats dictionary."""
    return {
        "frame": frame,
        "population": stats.get("total_population", 0),
        "generation": stats.get("current_generation", 0),
        "max_generation": stats.get("max_generation", stats.get("current_generation", 0)),
        "births": stats.get("total_births", 0),
        "deaths": stats.get("total_deaths", 0),
        "capacity": stats.get("capacity_usage", "0%"),
        "time": stats.get("time_string", "Day"),
        "death_causes": stats.get("death_causes", {}),
        "fish_count": stats.get("fish_count", 0),
        "food_count": stats.get("food_count", 0),
        "plant_count": stats.get("plant_count", 0),
        "fps": round(fps, 1),
        "fast_forward": fast_forward,
        "total_sexual_births": stats.get("reproduction_stats", {}).get("total_sexual_reproductions", 0),
        "total_asexual_births": stats.get("reproduction_stats", {}).get("total_asexual_reproductions", 0),
    }


def build_energy_stats(
    stats: Dict[str, Any],
    poker_score: Optional[float],
    poker_score_history: List[float],
    poker_elo: Optional[float] = None,
    poker_elo_history: List[float] = None,
) -> Dict[str, Any]:
    """Build energy-related stats dictionary."""
    return {
        "total_energy": stats.get("total_energy", 0.0),
        "food_energy": stats.get("food_energy", 0.0),
        "live_food_count": stats.get("live_food_count", 0),
        "live_food_energy": stats.get("live_food_energy", 0.0),
        "fish_energy": stats.get("fish_energy", 0.0),
        "plant_energy": stats.get("plant_energy", 0.0),
        "energy_sources": stats.get("energy_sources", {}),
        "energy_sources_recent": stats.get("energy_sources_recent", {}),
        "energy_from_nectar": stats.get("energy_from_nectar", 0.0),
        "energy_from_live_food": stats.get("energy_from_live_food", 0.0),
        "energy_from_falling_food": stats.get("energy_from_falling_food", 0.0),
        "energy_from_poker": stats.get("energy_from_poker", 0.0),
        "energy_from_poker_plant": stats.get("energy_from_poker_plant", 0.0),
        "energy_from_auto_eval": stats.get("energy_from_auto_eval", 0.0),
        "energy_burn_recent": stats.get("energy_burn_recent", {}),
        "energy_burn_total": stats.get("energy_burn_total", 0.0),
        "energy_gains_recent_total": stats.get("energy_gains_recent_total", 0.0),
        "energy_net_recent": stats.get("energy_net_recent", 0.0),
        "energy_accounting_discrepancy": stats.get("energy_accounting_discrepancy", 0.0),
        "plant_energy_sources": stats.get("plant_energy_sources", {}),
        "plant_energy_sources_recent": stats.get("plant_energy_sources_recent", {}),
        "plant_energy_from_photosynthesis": stats.get("plant_energy_from_photosynthesis", 0.0),
        "plant_energy_burn_recent": stats.get("plant_energy_burn_recent", {}),
        "plant_energy_burn_total": stats.get("plant_energy_burn_total", 0.0),
        "energy_delta": stats.get("energy_delta", {}),
        "avg_fish_energy": stats.get("avg_fish_energy", 0.0),
        "min_fish_energy": stats.get("min_fish_energy", 0.0),
        "max_fish_energy": stats.get("max_fish_energy", 0.0),
        "min_max_energy_capacity": stats.get("min_max_energy_capacity", 0.0),
        "max_max_energy_capacity": stats.get("max_max_energy_capacity", 0.0),
        "median_max_energy_capacity": stats.get("median_max_energy_capacity", 0.0),
        "fish_health_critical": stats.get("fish_health_critical", 0),
        "fish_health_low": stats.get("fish_health_low", 0),
        "fish_health_healthy": stats.get("fish_health_healthy", 0),
        "fish_health_full": stats.get("fish_health_full", 0),
        "poker_score": poker_score,
        "poker_score_history": poker_score_history,
        "poker_elo": poker_elo,
        "poker_elo_history": poker_elo_history or [],
    }


def build_physical_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build physical trait stats dictionary."""
    return {
        # Adult size
        "adult_size_min": stats.get("adult_size_min", 0.0),
        "adult_size_max": stats.get("adult_size_max", 0.0),
        "adult_size_median": stats.get("adult_size_median", 0.0),
        "adult_size_range": stats.get("adult_size_range", ""),
        "allowed_adult_size_min": stats.get("allowed_adult_size_min", 0.0),
        "allowed_adult_size_max": stats.get("allowed_adult_size_max", 0.0),
        "adult_size_bins": stats.get("adult_size_bins", []),
        "adult_size_bin_edges": stats.get("adult_size_bin_edges", []),
        # Eye size
        "eye_size_min": stats.get("eye_size_min", 0.0),
        "eye_size_max": stats.get("eye_size_max", 0.0),
        "eye_size_median": stats.get("eye_size_median", 0.0),
        "eye_size_bins": stats.get("eye_size_bins", []),
        "eye_size_bin_edges": stats.get("eye_size_bin_edges", []),
        "allowed_eye_size_min": stats.get("allowed_eye_size_min", 0.5),
        "allowed_eye_size_max": stats.get("allowed_eye_size_max", 2.0),
        # Fin size
        "fin_size_min": stats.get("fin_size_min", 0.0),
        "fin_size_max": stats.get("fin_size_max", 0.0),
        "fin_size_median": stats.get("fin_size_median", 0.0),
        "fin_size_bins": stats.get("fin_size_bins", []),
        "fin_size_bin_edges": stats.get("fin_size_bin_edges", []),
        "allowed_fin_size_min": stats.get("allowed_fin_size_min", 0.5),
        "allowed_fin_size_max": stats.get("allowed_fin_size_max", 2.0),
        # Tail size
        "tail_size_min": stats.get("tail_size_min", 0.0),
        "tail_size_max": stats.get("tail_size_max", 0.0),
        "tail_size_median": stats.get("tail_size_median", 0.0),
        "tail_size_bins": stats.get("tail_size_bins", []),
        "tail_size_bin_edges": stats.get("tail_size_bin_edges", []),
        "allowed_tail_size_min": stats.get("allowed_tail_size_min", 0.5),
        "allowed_tail_size_max": stats.get("allowed_tail_size_max", 2.0),
        # Body aspect
        "body_aspect_min": stats.get("body_aspect_min", 0.0),
        "body_aspect_max": stats.get("body_aspect_max", 0.0),
        "body_aspect_median": stats.get("body_aspect_median", 0.0),
        "allowed_body_aspect_min": stats.get("allowed_body_aspect_min", 0.0),
        "allowed_body_aspect_max": stats.get("allowed_body_aspect_max", 0.0),
        "body_aspect_bins": stats.get("body_aspect_bins", []),
        "body_aspect_bin_edges": stats.get("body_aspect_bin_edges", []),
        # Template ID
        "template_id_min": stats.get("template_id_min", 0.0),
        "template_id_max": stats.get("template_id_max", 0.0),
        "template_id_median": stats.get("template_id_median", 0.0),
        "allowed_template_id_min": stats.get("allowed_template_id_min", 0.0),
        "allowed_template_id_max": stats.get("allowed_template_id_max", 0.0),
        "template_id_bins": stats.get("template_id_bins", []),
        "template_id_bin_edges": stats.get("template_id_bin_edges", []),
        # Pattern type
        "pattern_type_min": stats.get("pattern_type_min", 0.0),
        "pattern_type_max": stats.get("pattern_type_max", 0.0),
        "pattern_type_median": stats.get("pattern_type_median", 0.0),
        "allowed_pattern_type_min": stats.get("allowed_pattern_type_min", 0.0),
        "allowed_pattern_type_max": stats.get("allowed_pattern_type_max", 0.0),
        "pattern_type_bins": stats.get("pattern_type_bins", []),
        "pattern_type_bin_edges": stats.get("pattern_type_bin_edges", []),
        # Pattern intensity
        "pattern_intensity_min": stats.get("pattern_intensity_min", 0.0),
        "pattern_intensity_max": stats.get("pattern_intensity_max", 0.0),
        "pattern_intensity_median": stats.get("pattern_intensity_median", 0.0),
        "allowed_pattern_intensity_min": stats.get("allowed_pattern_intensity_min", 0.0),
        "allowed_pattern_intensity_max": stats.get("allowed_pattern_intensity_max", 0.0),
        "pattern_intensity_bins": stats.get("pattern_intensity_bins", []),
        "pattern_intensity_bin_edges": stats.get("pattern_intensity_bin_edges", []),
        # Lifespan modifier
        "lifespan_modifier_min": stats.get("lifespan_modifier_min", 0.0),
        "lifespan_modifier_max": stats.get("lifespan_modifier_max", 0.0),
        "lifespan_modifier_median": stats.get("lifespan_modifier_median", 0.0),
        "allowed_lifespan_modifier_min": stats.get("allowed_lifespan_modifier_min", 0.0),
        "allowed_lifespan_modifier_max": stats.get("allowed_lifespan_modifier_max", 0.0),
        "lifespan_modifier_bins": stats.get("lifespan_modifier_bins", []),
        "lifespan_modifier_bin_edges": stats.get("lifespan_modifier_bin_edges", []),
        # Dynamic gene distributions
        "gene_distributions": stats.get("gene_distributions", {}),
    }


def build_meta_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build meta stats (mutation rate, strength, HGT) dictionary."""
    meta_stats = {}
    traits = [
        "adult_size", "eye_size", "fin_size", "tail_size",
        "body_aspect", "template_id", "pattern_type",
        "pattern_intensity", "lifespan_modifier"
    ]
    meta_fields = [
        "mut_rate_mean", "mut_rate_std", "mut_strength_mean",
        "mut_strength_std", "hgt_prob_mean", "hgt_prob_std"
    ]
    for trait in traits:
        for meta in meta_fields:
            key = f"{trait}_{meta}"
            if key in stats:
                meta_stats[key] = stats[key]
    return meta_stats
