"""Genetic diversity tracking for the ecosystem.

Computes population-level genetic diversity statistics (algorithm/species
counts, trait variances) and produces the diversity summary used by
EcosystemManager. Extracted from core/ecosystem.py; EcosystemManager keeps
thin delegating facades.
"""

from typing import TYPE_CHECKING, Any

from core.ecosystem_stats import GeneticDiversityStats

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

        for fish in fish_list:
            genome = fish.genome

            composable = genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                behavior_id = composable.value.behavior_id
                algorithms.add(hash(behavior_id) % 1000)

            species.add(fish.species)
            color_hues.append(genome.physical.color_hue.value)
            speed_modifiers.append(genome.speed_modifier)
            size_modifiers.append(genome.physical.size_modifier.value)
            vision_ranges.append(genome.vision_range)

        n_fish = len(fish_list)

        color_variance = 0.0
        if n_fish > 1:
            mean_color = sum(color_hues) / n_fish
            color_variance = sum((h - mean_color) ** 2 for h in color_hues) / n_fish

        trait_variances: dict[str, float] = {}
        if n_fish > 1:
            mean_speed = sum(speed_modifiers) / n_fish
            trait_variances["speed"] = sum((s - mean_speed) ** 2 for s in speed_modifiers) / n_fish

            mean_size = sum(size_modifiers) / n_fish
            trait_variances["size"] = sum((s - mean_size) ** 2 for s in size_modifiers) / n_fish

            mean_vision = sum(vision_ranges) / n_fish
            trait_variances["vision"] = sum((v - mean_vision) ** 2 for v in vision_ranges) / n_fish

        # Track behavioral trait variances for convergence detection.
        # Low variance in a trait means the population has converged on it,
        # which may indicate a convergence trap (stuck at suboptimal value).
        behavioral_traits = ["prediction_skill", "pursuit_aggression", "hunting_stamina"]
        for trait_name in behavioral_traits:
            values = []
            for fish in fish_list:
                trait = getattr(fish.genome.behavioral, trait_name, None)
                if trait is not None and hasattr(trait, "value"):
                    values.append(float(trait.value))
            if len(values) > 1:
                mean_val = sum(values) / len(values)
                trait_variances[trait_name] = sum((v - mean_val) ** 2 for v in values) / len(values)

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
