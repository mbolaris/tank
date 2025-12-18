"""Poker Evolution Tracker - Monitor and log poker skill evolution over generations.

This module provides tools to track and visualize how poker performance
evolves in the fish population over time.
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.entities import Fish

logger = logging.getLogger(__name__)


@dataclass
class GenerationPokerStats:
    """Poker statistics for a single generation."""

    generation: int
    timestamp: str
    fish_count: int = 0

    # Aggregate poker metrics
    total_poker_games: int = 0
    total_poker_wins: int = 0
    avg_win_rate: float = 0.0
    avg_energy_won: float = 0.0
    avg_showdown_win_rate: float = 0.0

    # Strategy distribution
    strategy_counts: Dict[str, int] = field(default_factory=dict)
    dominant_strategy: str = ""
    strategy_diversity: int = 0

    # Parameter averages for dominant strategy
    dominant_strategy_params: Dict[str, float] = field(default_factory=dict)

    # Performance against baseline (if available)
    avg_bb_per_100_vs_baseline: Optional[float] = None

    # Reproduction metrics
    poker_reproductions: int = 0
    asexual_reproductions: int = 0


@dataclass
class PokerEvolutionMetrics:
    """Comprehensive metrics for poker evolution tracking."""

    # Historical data
    generation_stats: List[GenerationPokerStats] = field(default_factory=list)

    # Trend analysis
    win_rate_trend: List[float] = field(default_factory=list)
    strategy_dominance_trend: List[str] = field(default_factory=list)
    fitness_trend: List[float] = field(default_factory=list)

    # Best performers
    best_win_rate_ever: float = 0.0
    best_strategy_ever: str = ""
    best_fitness_ever: float = 0.0

    def add_generation(self, stats: GenerationPokerStats) -> None:
        """Add a generation's statistics."""
        self.generation_stats.append(stats)
        self.win_rate_trend.append(stats.avg_win_rate)
        self.strategy_dominance_trend.append(stats.dominant_strategy)

        if stats.avg_bb_per_100_vs_baseline is not None:
            self.fitness_trend.append(stats.avg_bb_per_100_vs_baseline)

            if stats.avg_bb_per_100_vs_baseline > self.best_fitness_ever:
                self.best_fitness_ever = stats.avg_bb_per_100_vs_baseline

        if stats.avg_win_rate > self.best_win_rate_ever:
            self.best_win_rate_ever = stats.avg_win_rate
            self.best_strategy_ever = stats.dominant_strategy

    def get_evolution_summary(self) -> Dict[str, Any]:
        """Get a summary of evolution progress."""
        if len(self.generation_stats) < 2:
            return {"status": "insufficient_data", "generations": len(self.generation_stats)}

        first_gen = self.generation_stats[0]
        last_gen = self.generation_stats[-1]
        mid_point = len(self.generation_stats) // 2

        # Calculate trends
        first_half_avg = sum(self.win_rate_trend[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = (
            sum(self.win_rate_trend[mid_point:]) / (len(self.win_rate_trend) - mid_point)
            if len(self.win_rate_trend) > mid_point
            else 0
        )

        fitness_improvement = None
        if len(self.fitness_trend) >= 2:
            fitness_improvement = self.fitness_trend[-1] - self.fitness_trend[0]

        return {
            "status": "tracked",
            "total_generations": len(self.generation_stats),
            "win_rate_start": first_gen.avg_win_rate,
            "win_rate_end": last_gen.avg_win_rate,
            "win_rate_change": last_gen.avg_win_rate - first_gen.avg_win_rate,
            "first_half_avg_win_rate": first_half_avg,
            "second_half_avg_win_rate": second_half_avg,
            "win_rate_trend": "improving" if second_half_avg > first_half_avg else "declining",
            "fitness_improvement": fitness_improvement,
            "dominant_strategy_start": first_gen.dominant_strategy,
            "dominant_strategy_end": last_gen.dominant_strategy,
            "strategy_diversity_start": first_gen.strategy_diversity,
            "strategy_diversity_end": last_gen.strategy_diversity,
            "best_win_rate_ever": self.best_win_rate_ever,
            "best_strategy_ever": self.best_strategy_ever,
        }


class PokerEvolutionTracker:
    """Tracks poker evolution metrics across generations."""

    def __init__(self, export_path: Optional[Path] = None):
        """Initialize the evolution tracker.

        Args:
            export_path: Optional path to export metrics JSON
        """
        self.metrics = PokerEvolutionMetrics()
        self.export_path = export_path
        self._current_generation = 0
        self._last_snapshot_frame = 0
        self._snapshot_interval = 3000  # Take snapshot every 100 seconds at 30fps

    def snapshot(
        self,
        fish_list: List["Fish"],
        generation: Optional[int] = None,
        poker_reproductions: int = 0,
        asexual_reproductions: int = 0,
    ) -> GenerationPokerStats:
        """Take a snapshot of the current poker evolution state.

        Args:
            fish_list: List of all fish in the simulation
            generation: Current generation number (auto-incremented if None)
            poker_reproductions: Number of poker-based reproductions since last snapshot
            asexual_reproductions: Number of asexual reproductions since last snapshot

        Returns:
            GenerationPokerStats for this snapshot
        """
        if generation is not None:
            self._current_generation = generation
        else:
            self._current_generation += 1

        stats = GenerationPokerStats(
            generation=self._current_generation,
            timestamp=datetime.now().isoformat(),
            fish_count=len(fish_list),
            poker_reproductions=poker_reproductions,
            asexual_reproductions=asexual_reproductions,
        )

        if not fish_list:
            self.metrics.add_generation(stats)
            return stats

        # Collect poker statistics from fish
        total_games = 0
        total_wins = 0
        total_energy_won = 0.0
        total_showdown_wins = 0
        total_showdowns = 0
        strategy_counts: Dict[str, int] = defaultdict(int)
        strategy_params: Dict[str, List[Dict[str, float]]] = defaultdict(list)

        for fish in fish_list:
            # Get poker stats from fish
            if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
                ps = fish.poker_stats
                total_games += ps.total_games
                total_wins += ps.wins  # Fixed: was total_wins
                total_energy_won += ps.total_energy_won
                total_showdown_wins += ps.hands_won_at_showdown  # Fixed: was showdowns_won
                total_showdowns += ps.showdown_count  # Fixed: was showdowns_played

            # Get poker strategy
            if hasattr(fish, "genome") and fish.genome is not None:
                strat = fish.genome.behavioral.poker_strategy_algorithm.value
                if strat is not None:
                    strategy_counts[strat.strategy_id] += 1
                    strategy_params[strat.strategy_id].append(strat.parameters.copy())

        # Calculate averages
        if total_games > 0:
            stats.total_poker_games = total_games
            stats.total_poker_wins = total_wins
            stats.avg_win_rate = total_wins / total_games
            stats.avg_energy_won = total_energy_won / len(fish_list)

        if total_showdowns > 0:
            stats.avg_showdown_win_rate = total_showdown_wins / total_showdowns

        # Strategy distribution
        stats.strategy_counts = dict(strategy_counts)
        stats.strategy_diversity = len(strategy_counts)

        if strategy_counts:
            stats.dominant_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0]

            # Calculate average parameters for dominant strategy
            if stats.dominant_strategy in strategy_params:
                params_list = strategy_params[stats.dominant_strategy]
                if params_list:
                    avg_params: Dict[str, float] = {}
                    all_keys = set()
                    for p in params_list:
                        all_keys.update(p.keys())

                    for key in all_keys:
                        values = [p.get(key, 0) for p in params_list if key in p]
                        if values:
                            avg_params[key] = sum(values) / len(values)

                    stats.dominant_strategy_params = avg_params

        self.metrics.add_generation(stats)
        self._export_if_configured()

        return stats

    def _export_if_configured(self) -> None:
        """Export metrics to file if export_path is configured."""
        if self.export_path is None:
            return

        try:
            export_data = {
                "summary": self.metrics.get_evolution_summary(),
                "generations": [asdict(g) for g in self.metrics.generation_stats],
                "trends": {
                    "win_rate": self.metrics.win_rate_trend,
                    "fitness": self.metrics.fitness_trend,
                    "dominant_strategy": self.metrics.strategy_dominance_trend,
                },
            }

            with open(self.export_path, "w") as f:
                json.dump(export_data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to export poker evolution metrics: {e}")

    def should_take_snapshot(self, current_frame: int) -> bool:
        """Check if it's time to take a snapshot based on frame count."""
        if current_frame - self._last_snapshot_frame >= self._snapshot_interval:
            self._last_snapshot_frame = current_frame
            return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get evolution summary."""
        return self.metrics.get_evolution_summary()

    def log_evolution_status(self) -> None:
        """Log the current evolution status."""
        summary = self.get_summary()

        if summary.get("status") == "insufficient_data":
            logger.info(f"Poker Evolution: Only {summary.get('generations', 0)} generations tracked")
            return

        trend = summary.get("win_rate_trend", "unknown")
        fitness_change = summary.get("fitness_improvement")

        logger.info(
            f"Poker Evolution Status (Gen {summary.get('total_generations', 0)}): "
            f"Win rate {summary.get('win_rate_start', 0):.1%} → {summary.get('win_rate_end', 0):.1%} ({trend}), "
            f"Dominant: {summary.get('dominant_strategy_end', 'unknown')}, "
            f"Diversity: {summary.get('strategy_diversity_end', 0)}"
        )

        if fitness_change is not None:
            logger.info(f"  Fitness vs baseline change: {fitness_change:+.2f} BB/100")


# Singleton instance for ecosystem-wide tracking
_global_tracker: Optional[PokerEvolutionTracker] = None


def get_evolution_tracker(export_path: Optional[Path] = None) -> PokerEvolutionTracker:
    """Get or create the global poker evolution tracker.

    Args:
        export_path: Optional path for exporting metrics

    Returns:
        The global PokerEvolutionTracker instance
    """
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = PokerEvolutionTracker(export_path)
    elif export_path is not None and _global_tracker.export_path is None:
        _global_tracker.export_path = export_path

    return _global_tracker


def reset_evolution_tracker() -> None:
    """Reset the global tracker (useful for testing)."""
    global _global_tracker
    _global_tracker = None
