from __future__ import annotations

import logging
from collections import defaultdict
from statistics import median
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.constants import (
    ENERGY_STATS_WINDOW_FRAMES,
    FISH_ADULT_SIZE,
    FISH_SIZE_MODIFIER_MAX,
    FISH_SIZE_MODIFIER_MIN,
)
from core.ecosystem_stats import EcosystemEvent, GenerationStats, GeneticDiversityStats

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.entities import Fish
    from core.genetics import Genome

logger = logging.getLogger(__name__)


def record_birth(
    ecosystem: EcosystemManager,
    fish_id: int,
    generation: int,
    parent_ids: Optional[List[int]] = None,
    algorithm_id: Optional[int] = None,
    color: Optional[str] = None,
) -> None:
    ecosystem.total_births += 1

    if generation not in ecosystem.generation_stats:
        ecosystem.generation_stats[generation] = GenerationStats(generation=generation)

    ecosystem.generation_stats[generation].births += 1
    ecosystem.generation_stats[generation].population += 1

    if generation > ecosystem.current_generation:
        ecosystem.current_generation = generation

    if algorithm_id is not None and algorithm_id in ecosystem.algorithm_stats:
        ecosystem.algorithm_stats[algorithm_id].total_births += 1
        ecosystem.algorithm_stats[algorithm_id].current_population += 1

    ecosystem.enhanced_stats.record_offspring_birth(energy_cost=0.0)

    parent_id = None
    if parent_ids and len(parent_ids) > 0:
        parent_id = parent_ids[0]

    algorithm_name = "Unknown"
    if algorithm_id is not None and algorithm_id in ecosystem.algorithm_stats:
        algorithm_name = ecosystem.algorithm_stats[algorithm_id].algorithm_name

    lineage_record = {
        "id": str(fish_id),
        "parent_id": str(parent_id) if parent_id is not None else "root",
        "generation": generation,
        "algorithm": algorithm_name,
        "color": color if color else "#00ff00",
        "birth_time": ecosystem.frame_count,
    }
    ecosystem.lineage_log.append(lineage_record)

    # Cap lineage log size to prevent unbounded growth
    MAX_LINEAGE_LOG_SIZE = 5000
    if len(ecosystem.lineage_log) > MAX_LINEAGE_LOG_SIZE:
        ecosystem.lineage_log.pop(0)

    details = f"Parents: {parent_ids}" if parent_ids else "Initial spawn"
    if algorithm_id is not None:
        details += f", Algorithm: {algorithm_id}"
    ecosystem._add_event(
        EcosystemEvent(
            frame=ecosystem.frame_count,
            event_type="birth",
            fish_id=fish_id,
            details=details,
        )
    )


def record_death(
    ecosystem: EcosystemManager,
    fish_id: int,
    generation: int,
    age: int,
    cause: str = "unknown",
    genome: Optional[Genome] = None,
    algorithm_id: Optional[int] = None,
    remaining_energy: float = 0.0,
) -> None:
    ecosystem.total_deaths += 1

    if generation in ecosystem.generation_stats:
        stats = ecosystem.generation_stats[generation]
        stats.deaths += 1
        stats.population = max(0, stats.population - 1)

        total_fish = stats.deaths
        if total_fish > 0:
            stats.avg_age = (stats.avg_age * (total_fish - 1) + age) / total_fish
        else:
            stats.avg_age = age

    if not isinstance(ecosystem.death_causes, defaultdict):
        ecosystem.death_causes = defaultdict(int, ecosystem.death_causes)

    ecosystem.death_causes[cause] += 1

    if algorithm_id is not None and algorithm_id in ecosystem.algorithm_stats:
        algo_stats = ecosystem.algorithm_stats[algorithm_id]
        algo_stats.total_deaths += 1
        algo_stats.current_population = max(0, algo_stats.current_population - 1)
        algo_stats.total_lifespan += age

        if cause == "starvation":
            algo_stats.deaths_starvation += 1
        elif cause == "old_age":
            algo_stats.deaths_old_age += 1
        elif cause == "predation":
            algo_stats.deaths_predation += 1

    ecosystem.enhanced_stats.record_death_energy_loss(remaining_energy)

    # Record energy burn for economy stats
    ecosystem.record_energy_burn(f"death_{cause}", remaining_energy)

    details = f"Age: {age}, Generation: {generation}"
    if algorithm_id is not None:
        details += f", Algorithm: {algorithm_id}"
    ecosystem._add_event(
        EcosystemEvent(
            frame=ecosystem.frame_count, event_type=cause, fish_id=fish_id, details=details
        )
    )


def update_population_stats(ecosystem: EcosystemManager, fish_list: List[Fish]) -> None:
    if not fish_list:
        return

    gen_fish: Dict[int, List[Fish]] = defaultdict(list)
    for fish in fish_list:
        if hasattr(fish, "generation"):
            gen_fish[fish.generation].append(fish)

    for generation, fishes in gen_fish.items():
        if generation not in ecosystem.generation_stats:
            ecosystem.generation_stats[generation] = GenerationStats(generation=generation)

        stats = ecosystem.generation_stats[generation]
        stats.population = len(fishes)

        fishes_with_genome = [f for f in fishes if hasattr(f, "genome")]
        if fishes_with_genome:
            stats.avg_speed = sum(f.genome.speed_modifier for f in fishes_with_genome) / len(fishes)
            stats.avg_size = sum(
                f.genome.physical.size_modifier.value for f in fishes_with_genome
            ) / len(fishes)
            stats.avg_energy = sum(
                f.genome.physical.size_modifier.value for f in fishes_with_genome
            ) / len(fishes)  # Max energy is based on size

    update_genetic_diversity_stats(ecosystem, fish_list)

    pregnant_count = sum(
        1
        for fish in fish_list
        if hasattr(fish, "reproduction") and fish.reproduction.is_pregnant
    )
    ecosystem.update_pregnant_count(pregnant_count)

    if ecosystem.frame_count % 10 == 0:
        ecosystem.enhanced_stats.record_frame_snapshot(
            frame=ecosystem.frame_count,
            fish_list=fish_list,
            births_this_frame=0,
            deaths_this_frame=0,
        )


def update_genetic_diversity_stats(ecosystem: EcosystemManager, fish_list: List[Fish]) -> None:
    """Update genetic diversity statistics.

    PERFORMANCE OPTIMIZATIONS:
    - Removed redundant hasattr checks (fish always have genome, species)
    - Direct attribute access with getattr fallback
    - Single loop iteration collecting all data
    """
    if not fish_list:
        ecosystem.genetic_diversity_stats = GeneticDiversityStats()
        return

    try:
        from core.algorithms import get_algorithm_index
    except ImportError:
        get_algorithm_index = None

    algorithms = set()
    species = set()
    color_hues = []
    speed_modifiers = []
    size_modifiers = []
    vision_ranges = []

    # OPTIMIZATION: Fish always have genome and species - skip hasattr checks
    for fish in fish_list:
        genome = fish.genome

        composable = genome.behavioral.behavior
        if composable is not None and composable.value is not None:
            # Use hash of behavior_id for diversity tracking
            behavior_id = composable.value.behavior_id
            algorithms.add(hash(behavior_id) % 1000)

        species.add(fish.species)

        # Direct attribute access - these exist on FishGenome
        color_hues.append(genome.physical.color_hue.value)
        speed_modifiers.append(genome.speed_modifier)
        size_modifiers.append(genome.physical.size_modifier.value)
        vision_ranges.append(genome.vision_range)

    # OPTIMIZATION: Only calculate variances if we have data
    n_fish = len(fish_list)

    color_variance = 0.0
    if n_fish > 1:
        mean_color = sum(color_hues) / n_fish
        color_variance = sum((h - mean_color) ** 2 for h in color_hues) / n_fish

    trait_variances: Dict[str, float] = {}
    if n_fish > 1:
        mean_speed = sum(speed_modifiers) / n_fish
        trait_variances["speed"] = sum((s - mean_speed) ** 2 for s in speed_modifiers) / n_fish

        mean_size = sum(size_modifiers) / n_fish
        trait_variances["size"] = sum((s - mean_size) ** 2 for s in size_modifiers) / n_fish

        mean_vision = sum(vision_ranges) / n_fish
        trait_variances["vision"] = sum((v - mean_vision) ** 2 for v in vision_ranges) / n_fish

    ecosystem.genetic_diversity_stats.unique_algorithms = len(algorithms)
    ecosystem.genetic_diversity_stats.unique_species = len(species)
    ecosystem.genetic_diversity_stats.color_variance = color_variance
    ecosystem.genetic_diversity_stats.trait_variances = trait_variances


def get_population_by_generation(ecosystem: EcosystemManager) -> Dict[int, int]:
    return {
        gen: stats.population
        for gen, stats in ecosystem.generation_stats.items()
        if stats.population > 0
    }


def get_total_population(ecosystem: EcosystemManager) -> int:
    return sum(stats.population for stats in ecosystem.generation_stats.values())


def get_summary_stats(
    ecosystem: EcosystemManager, entities: Optional[List[Any]] = None
) -> Dict[str, Any]:
    total_pop = get_total_population(ecosystem)
    poker_summary = ecosystem.get_poker_stats_summary()

    energy_summary = ecosystem.get_energy_source_summary()
    recent_energy = ecosystem.get_recent_energy_breakdown(window_frames=ENERGY_STATS_WINDOW_FRAMES)
    recent_energy_burn = ecosystem.get_recent_energy_burn(window_frames=ENERGY_STATS_WINDOW_FRAMES)
    energy_delta = ecosystem.get_energy_delta(window_frames=ENERGY_STATS_WINDOW_FRAMES)

    recent_energy_total = sum(recent_energy.values())
    recent_energy_burn_total = sum(recent_energy_burn.values())
    recent_energy_net = recent_energy_total - recent_energy_burn_total
    energy_accounting_discrepancy = recent_energy_net - energy_delta.get("energy_delta", 0.0)

    plant_energy_summary = ecosystem.get_plant_energy_source_summary()
    recent_plant_energy = ecosystem.get_recent_plant_energy_breakdown(
        window_frames=ENERGY_STATS_WINDOW_FRAMES
    )
    recent_plant_energy_burn = ecosystem.get_recent_plant_energy_burn(
        window_frames=ENERGY_STATS_WINDOW_FRAMES
    )

    total_energy = 0.0
    fish_list = []
    if entities is not None:
        from core.entities import Fish

        fish_list = [e for e in entities if isinstance(e, Fish)]
        total_energy = sum(e.energy for e in fish_list)

    alive_generations = [
        g for g, stats in ecosystem.generation_stats.items() if stats.population > 0
    ]

    # Calculate adult size stats if we have fish
    adult_size_min = 0.0
    adult_size_max = 0.0
    adult_size_median = 0.0
    adult_size_range = "0.0-0.0"
    if fish_list:
        # Adult size = FISH_ADULT_SIZE * genome.physical.size_modifier.value
        adult_sizes = [
            FISH_ADULT_SIZE
            * (
                f.genome.physical.size_modifier.value
                if hasattr(f, "genome")
                else 1.0
            )
            for f in fish_list
        ]
        adult_size_min = min(adult_sizes)
        adult_size_max = max(adult_sizes)
        try:
            adult_size_median = median(adult_sizes)
        except Exception:
            adult_size_median = 0.0
        adult_size_range = f"{adult_size_min:.2f}-{adult_size_max:.2f}"

    return {
        "total_population": total_pop,
        "current_generation": ecosystem.current_generation,
        "max_generation": max(alive_generations) if alive_generations else 0,
        "total_births": ecosystem.total_births,
        "total_deaths": ecosystem.total_deaths,
        "total_extinctions": ecosystem.total_extinctions,
        "carrying_capacity": ecosystem.max_population,
        "capacity_usage": (
            f"{int(100 * total_pop / ecosystem.max_population)}%"
            if ecosystem.max_population > 0
            else "0%"
        ),
        "death_causes": dict(ecosystem.death_causes),
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
        # Adult size statistics: current population adult size distribution and allowed bounds
        "adult_size_min": adult_size_min,
        "adult_size_max": adult_size_max,
        "adult_size_median": adult_size_median,
        "adult_size_range": adult_size_range,
        "allowed_adult_size_min": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN,
        "allowed_adult_size_max": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX,
        "reproduction_stats": ecosystem.get_reproduction_summary(),
        "diversity_stats": ecosystem.get_diversity_summary(),
    }
