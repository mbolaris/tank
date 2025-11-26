import logging
from typing import Any, Dict

from core.ecosystem_stats import AlgorithmStats, ReproductionStats

logger = logging.getLogger(__name__)


class ReproductionStatsManager:
    """Tracks reproduction statistics and algorithm-level reproduction counts."""

    def __init__(self, algorithm_stats: Dict[int, AlgorithmStats]):
        self.reproduction_stats: ReproductionStats = ReproductionStats()
        self._algorithm_stats = algorithm_stats

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregated reproduction statistics."""
        return {
            "total_reproductions": self.reproduction_stats.total_reproductions,
            "total_mating_attempts": self.reproduction_stats.total_mating_attempts,
            "total_failed_attempts": self.reproduction_stats.total_failed_attempts,
            "success_rate": self.reproduction_stats.get_success_rate(),
            "success_rate_pct": f"{self.reproduction_stats.get_success_rate():.1%}",
            "current_pregnant_fish": self.reproduction_stats.current_pregnant_fish,
            "total_offspring": self.reproduction_stats.total_offspring,
            "offspring_per_reproduction": self.reproduction_stats.get_offspring_per_reproduction(),
        }

    def record_reproduction(self, algorithm_id: int) -> None:
        """Record a successful reproduction by a fish with the given algorithm."""
        if algorithm_id in self._algorithm_stats:
            self._algorithm_stats[algorithm_id].total_reproductions += 1

        self.reproduction_stats.total_reproductions += 1
        self.reproduction_stats.total_offspring += 1  # Assume 1 offspring per reproduction

    def record_mating_attempt(self, success: bool) -> None:
        """Record a mating attempt (successful or failed)."""
        self.reproduction_stats.total_mating_attempts += 1
        if not success:
            self.reproduction_stats.total_failed_attempts += 1

    def update_pregnant_count(self, count: int) -> None:
        """Update the count of currently pregnant fish."""
        self.reproduction_stats.current_pregnant_fish = count
