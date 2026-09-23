"""Genetic diversity tracking for the ecosystem.

Computes population-level genetic diversity statistics (algorithm/species
counts, trait variances) and produces the diversity summary used by
EcosystemManager. Extracted from core/ecosystem.py; EcosystemManager keeps
thin delegating facades.
"""

from typing import TYPE_CHECKING, Any, cast

from core.ecosystem_stats import GeneticDiversityStats
from core.statistics_utils import population_variance

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics.genome import Genome


BEHAVIORAL_TRAIT_NAMES = ("prediction_skill", "pursuit_aggression", "hunting_stamina")

# (behavior_id, color_hue, speed_modifier, size_modifier, vision_range,
#  one value per BEHAVIORAL_TRAIT_NAMES entry, None where the trait is absent)
DiversityProfile = tuple["str | None", float, float, float, float, "tuple[float | None, ...]"]


def _diversity_profile(genome: "Genome") -> DiversityProfile:
    """The per-genome values GeneticDiversityTracker.update reads every frame.

    Genomes do not change after creation (the same assumption the genome's
    speed/metabolism caches and genetic_distance's profile cache rest on), so
    the values are extracted once per genome instead of once per fish per
    frame; Genome.invalidate_caches() clears it with the others.
    """
    cached = genome._diversity_profile_cache
    if cached is not None:
        return cast(DiversityProfile, cached)

    composable = genome.behavioral.behavior
    # Distinct behavior_ids are counted directly. The old ``hash(behavior_id) %
    # 1000`` was process-randomized (PYTHONHASHSEED) AND collision-prone, making
    # unique_algorithms - and the ecosystem_health score it feeds -
    # non-reproducible. See ADR-014.
    behavior_id = (
        composable.value.behavior_id
        if composable is not None and composable.value is not None
        else None
    )
    behavioral: list[float | None] = []
    for trait_name in BEHAVIORAL_TRAIT_NAMES:
        trait = getattr(genome.behavioral, trait_name, None)
        if trait is not None and hasattr(trait, "value"):
            behavioral.append(float(trait.value))
        else:
            behavioral.append(None)
    profile: DiversityProfile = (
        behavior_id,
        genome.physical.color_hue.value,
        genome.speed_modifier,
        genome.physical.size_modifier.value,
        genome.vision_range,
        tuple(behavioral),
    )
    object.__setattr__(genome, "_diversity_profile_cache", profile)
    return profile


class GeneticDiversityTracker:
    """Tracks genetic diversity statistics for the current population."""

    def __init__(self) -> None:
        self.stats: GeneticDiversityStats = GeneticDiversityStats()

    def update(self, fish_list: list["Fish"]) -> None:
        """Update genetic diversity statistics."""
        if not fish_list:
            self.stats = GeneticDiversityStats()
            return

        algorithms = set()
        species = set()
        color_hues = []
        speed_modifiers = []
        size_modifiers = []
        vision_ranges = []

        # Behavioral trait variances feed convergence detection (low variance
        # means the population has converged on that trait, maybe a
        # convergence trap). Collected in the same pass as the fields above -
        # per-fish values and their order are unchanged, so variances are
        # identical to computing them in separate passes.
        behavioral_trait_values: dict[str, list[float]] = {
            name: [] for name in BEHAVIORAL_TRAIT_NAMES
        }

        for fish in fish_list:
            behavior_id, hue, speed, size, vision, behavioral = _diversity_profile(fish.genome)
            if behavior_id is not None:
                algorithms.add(behavior_id)
            # Species is read live: taxonomy can reclassify a fish, its genome cannot change.
            species.add(fish.species)
            color_hues.append(hue)
            speed_modifiers.append(speed)
            size_modifiers.append(size)
            vision_ranges.append(vision)
            for trait_name, value in zip(BEHAVIORAL_TRAIT_NAMES, behavioral, strict=True):
                if value is not None:
                    behavioral_trait_values[trait_name].append(value)

        n_fish = len(fish_list)

        color_variance = 0.0
        trait_variances: dict[str, float] = {}
        if n_fish > 1:
            color_variance = population_variance(color_hues)
            trait_variances["speed"] = population_variance(speed_modifiers)
            trait_variances["size"] = population_variance(size_modifiers)
            trait_variances["vision"] = population_variance(vision_ranges)

        for trait_name, values in behavioral_trait_values.items():
            if len(values) > 1:
                trait_variances[trait_name] = population_variance(values)

        self.stats.unique_algorithms = len(algorithms)
        self.stats.unique_species = len(species)
        self.stats.color_variance = color_variance
        self.stats.trait_variances = trait_variances

    def get_summary(self) -> dict[str, Any]:
        """Get summary genetic diversity statistics.

        Includes convergence warnings for traits with near-zero variance,
        which may indicate convergence traps where evolution has stalled.
        """
        diversity_score = self.stats.get_diversity_score()
        trait_vars = self.stats.trait_variances

        # Detect converged traits (variance < 0.001 = essentially fixed)
        converged_traits = [name for name, var in trait_vars.items() if var < 0.001]

        return {
            "unique_algorithms": self.stats.unique_algorithms,
            "unique_species": self.stats.unique_species,
            "color_variance": self.stats.color_variance,
            "speed_variance": trait_vars.get("speed", 0.0),
            "size_variance": trait_vars.get("size", 0.0),
            "vision_variance": trait_vars.get("vision", 0.0),
            "prediction_skill_variance": trait_vars.get("prediction_skill", 0.0),
            "pursuit_aggression_variance": trait_vars.get("pursuit_aggression", 0.0),
            "hunting_stamina_variance": trait_vars.get("hunting_stamina", 0.0),
            "diversity_score": diversity_score,
            "diversity_score_pct": f"{diversity_score:.1%}",
            "converged_traits": converged_traits,
        }
