"""Genetic diversity tracking for the ecosystem.

Computes population-level genetic diversity statistics (algorithm/species
counts, trait variances) and produces the diversity summary used by
EcosystemManager. Extracted from core/ecosystem.py; EcosystemManager keeps
thin delegating facades.
"""

from typing import TYPE_CHECKING, Any

from core.ecosystem_stats import GeneticDiversityStats
from core.statistics_utils import population_variance

if TYPE_CHECKING:
    from core.entities import Fish


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
        behavioral_trait_names = ("prediction_skill", "pursuit_aggression", "hunting_stamina")
        behavioral_trait_values: dict[str, list[float]] = {
            name: [] for name in behavioral_trait_names
        }

        for fish in fish_list:
            genome = fish.genome

            composable = genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                # Count distinct behavior_ids directly. The old
                # ``hash(behavior_id) % 1000`` was process-randomized (PYTHONHASHSEED)
                # AND collision-prone, making unique_algorithms - and the
                # ecosystem_health benchmark score it feeds - non-reproducible. See
                # ADR-014.
                behavior_id = composable.value.behavior_id
                algorithms.add(behavior_id)

            species.add(fish.species)
            color_hues.append(genome.physical.color_hue.value)
            speed_modifiers.append(genome.speed_modifier)
            size_modifiers.append(genome.physical.size_modifier.value)
            vision_ranges.append(genome.vision_range)

            for trait_name in behavioral_trait_names:
                trait = getattr(genome.behavioral, trait_name, None)
                if trait is not None and hasattr(trait, "value"):
                    behavioral_trait_values[trait_name].append(float(trait.value))

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
