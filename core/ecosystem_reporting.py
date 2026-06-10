"""Ecosystem report building.

Builds the comprehensive summary-stats dictionary and poker-strategy
distribution reports from the ecosystem's trackers. Extracted from
core/ecosystem.py; EcosystemManager keeps thin delegating facades, and
lookups go back through the manager so monkeypatched manager methods are
honored.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from core.config.ecosystem import ENERGY_STATS_WINDOW_FRAMES

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.entities import Fish


logger = logging.getLogger(__name__)


def build_summary_stats(eco: "EcosystemManager", entities: list | None = None) -> dict[str, Any]:
    """Get comprehensive ecosystem summary statistics."""
    from statistics import StatisticsError, median

    from core.config.fish import FISH_ADULT_SIZE, FISH_SIZE_MODIFIER_MAX, FISH_SIZE_MODIFIER_MIN

    total_pop = eco.get_total_population()
    poker_summary = eco.get_poker_stats_summary()

    energy_summary = eco.get_energy_source_summary()
    recent_energy = eco.get_recent_energy_breakdown(window_frames=ENERGY_STATS_WINDOW_FRAMES)
    recent_energy_burn = eco.get_recent_energy_burn(window_frames=ENERGY_STATS_WINDOW_FRAMES)
    energy_delta = eco.get_energy_delta(window_frames=ENERGY_STATS_WINDOW_FRAMES)

    recent_energy_total = sum(recent_energy.values())
    recent_energy_burn_total = sum(recent_energy_burn.values())
    recent_energy_net = recent_energy_total - recent_energy_burn_total
    energy_accounting_discrepancy = recent_energy_net - energy_delta.get("energy_delta", 0.0)

    plant_energy_summary = eco.get_plant_energy_source_summary()
    recent_plant_energy = eco.get_recent_plant_energy_breakdown(
        window_frames=ENERGY_STATS_WINDOW_FRAMES
    )
    recent_plant_energy_burn = eco.get_recent_plant_energy_burn(
        window_frames=ENERGY_STATS_WINDOW_FRAMES
    )

    total_energy = 0.0
    fish_list = []
    if entities is not None:
        from core.entities import Fish

        fish_list = [e for e in entities if isinstance(e, Fish)]
        total_energy = sum(
            e.energy + e._reproduction_component.overflow_energy_bank for e in fish_list
        )

    alive_generations = [g for g, stats in eco.generation_stats.items() if stats.population > 0]

    # Calculate adult size stats if we have fish
    adult_size_min = 0.0
    adult_size_max = 0.0
    adult_size_median = 0.0
    adult_size_range = "0.0-0.0"
    if fish_list:
        adult_sizes = [
            FISH_ADULT_SIZE
            * (f.genome.physical.size_modifier.value if hasattr(f, "genome") else 1.0)
            for f in fish_list
        ]
        adult_size_min = min(adult_sizes)
        adult_size_max = max(adult_sizes)
        try:
            adult_size_median = median(adult_sizes)
        except StatisticsError:
            adult_size_median = 0.0
        adult_size_range = f"{adult_size_min:.2f}-{adult_size_max:.2f}"

    return {
        "total_population": total_pop,
        "current_generation": eco.current_generation,
        "max_generation": max(alive_generations) if alive_generations else 0,
        "total_births": eco.total_births,
        "total_deaths": eco.total_deaths,
        "total_extinctions": eco.total_extinctions,
        "carrying_capacity": eco.max_population,
        "capacity_usage": (
            f"{int(100 * total_pop / eco.max_population)}%" if eco.max_population > 0 else "0%"
        ),
        "death_causes": dict(eco.death_causes),
        "generations_alive": len(alive_generations),
        "poker_stats": poker_summary,
        "total_energy": total_energy,
        "energy_sources": energy_summary,
        "energy_from_nectar": recent_energy.get("nectar", 0.0),
        "energy_from_live_food": recent_energy.get("live_food", 0.0),
        "energy_from_falling_food": recent_energy.get("falling_food", 0.0),
        "energy_from_poker": recent_energy.get("poker_fish", 0.0),
        "energy_from_poker_plant": recent_energy.get("poker_plant", 0.0),
        "energy_from_auto_eval": recent_energy.get("auto_eval", 0.0),
        "energy_from_birth": recent_energy.get("birth", 0.0),
        "energy_from_soup_spawn": recent_energy.get("soup_spawn", 0.0),
        "energy_from_migration_in": recent_energy.get("migration_in", 0.0),
        "energy_burn_recent": recent_energy_burn,
        "energy_burn_total": recent_energy_burn_total,
        "energy_sources_recent": recent_energy,
        "energy_gains_recent_total": recent_energy_total,
        "energy_net_recent": recent_energy_net,
        "energy_accounting_discrepancy": energy_accounting_discrepancy,
        "energy_delta": energy_delta,
        "plant_energy_sources": plant_energy_summary,
        "plant_energy_sources_recent": recent_plant_energy,
        "plant_energy_from_photosynthesis": recent_plant_energy.get("photosynthesis", 0.0),
        "plant_energy_burn_recent": recent_plant_energy_burn,
        "plant_energy_burn_total": sum(recent_plant_energy_burn.values()),
        "adult_size_min": adult_size_min,
        "adult_size_max": adult_size_max,
        "adult_size_median": adult_size_median,
        "adult_size_range": adult_size_range,
        "allowed_adult_size_min": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN,
        "allowed_adult_size_max": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX,
        "reproduction_stats": eco.get_reproduction_summary(),
        "diversity_stats": eco.get_diversity_summary(),
    }


def get_poker_strategy_distribution(fish_list: list["Fish"]) -> dict[str, Any]:
    """Get distribution of poker strategies in the population."""
    from collections import Counter

    strategy_counts: Counter = Counter()
    strategy_win_rates: dict[str, list[float]] = defaultdict(list)
    strategy_params: dict[str, list[dict[str, float]]] = defaultdict(list)

    for fish in fish_list:
        if not hasattr(fish, "genome") or fish.genome is None:
            continue

        trait = fish.genome.behavioral.poker_strategy
        strat = trait.value if trait else None
        if strat is None:
            continue

        strategy_counts[strat.strategy_id] += 1
        strategy_params[strat.strategy_id].append(strat.parameters.copy())

        if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
            ps = fish.poker_stats
            if ps.total_games > 0:
                strategy_win_rates[strat.strategy_id].append(ps.get_win_rate())

    avg_win_rates: dict[str, float] = {}
    for strat_id, rates in strategy_win_rates.items():
        if rates:
            avg_win_rates[strat_id] = sum(rates) / len(rates)

    result = {
        "total_fish": len(fish_list),
        "strategy_counts": dict(strategy_counts),
        "dominant_strategy": (strategy_counts.most_common(1)[0][0] if strategy_counts else None),
        "diversity": len(strategy_counts),
        "strategy_avg_win_rates": avg_win_rates,
    }

    return result


def log_poker_evolution_status(eco: "EcosystemManager", fish_list: list["Fish"]) -> None:
    """Log current poker evolution status to console."""
    dist = eco.get_poker_strategy_distribution(fish_list)

    if not dist["strategy_counts"]:
        logger.info("Poker Evolution: No fish with poker strategies")
        return

    sorted_strats = sorted(dist["strategy_counts"].items(), key=lambda x: x[1], reverse=True)

    strat_str = ", ".join(f"{s}:{c}" for s, c in sorted_strats[:5])
    dominant = dist["dominant_strategy"]
    diversity = dist["diversity"]
    dom_win_rate = dist["strategy_avg_win_rates"].get(dominant, 0)

    logger.info(
        f"Poker Evolution [Gen {eco.current_generation}]: "
        f"Dominant={dominant} ({dom_win_rate:.1%} win rate), "
        f"Diversity={diversity}, Distribution=[{strat_str}]"
    )
