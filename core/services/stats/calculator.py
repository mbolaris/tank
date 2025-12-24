"""Statistics calculation aggregator for the simulation.

This module provides the main StatsCalculator class that aggregates
statistics from specialized sub-modules:
- entity_stats: Fish, food, and plant counts/energy
- genetic_stats: Genetic trait distributions
"""

from typing import TYPE_CHECKING, Any, Dict, List

from core.services.stats import entity_stats
from core.services.stats.utils import calculate_meta_stats, humanize_gene_label

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


class StatsCalculator:
    """Calculates simulation statistics on demand.

    This service extracts stat calculation from SimulationEngine,
    providing a cleaner separation of concerns and easier testing.

    Attributes:
        _engine: Reference to the simulation engine
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the stats calculator.

        Args:
            engine: The simulation engine to calculate stats for
        """
        self._engine = engine

    def _calculate_meta_stats(self, traits: List[Any], prefix: str) -> Dict[str, Any]:
        """Delegate to utils module."""
        return calculate_meta_stats(traits, prefix)

    def _humanize_gene_label(self, key: str) -> str:
        """Delegate to utils module."""
        return humanize_gene_label(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive simulation statistics.

        This is the main entry point that aggregates all stat categories.

        Returns:
            Dictionary with all simulation statistics
        """
        if self._engine.ecosystem is None:
            return {}

        # Start with ecosystem summary stats
        stats = self._engine.ecosystem.get_summary_stats(
            self._engine.get_all_entities()
        )

        # Add cumulative energy sources
        stats["energy_sources"] = self._engine.ecosystem.get_energy_source_summary()

        # Add simulation state (delegated to entity_stats module)
        stats.update(entity_stats.get_simulation_state(self._engine))

        # Add entity counts and energy (delegated to entity_stats module)
        stats.update(entity_stats.get_entity_stats(self._engine))

        # Add fish health distribution (delegated to entity_stats module)
        stats.update(entity_stats.get_fish_health_stats(self._engine))

        # Add genetic distribution stats
        stats.update(self._get_genetic_distribution_stats())

        return stats

    def _get_genetic_distribution_stats(self) -> Dict[str, Any]:
        """Get genetic trait distribution statistics with histograms."""
        from core.services.stats.genetic_stats import get_genetic_distribution_stats

        fish_list = self._engine.get_fish_list()
        return get_genetic_distribution_stats(fish_list)
