"""Evolution Benchmark Tracker - Longitudinal tracking of poker skill evolution.

This module manages periodic benchmark evaluation and tracks population-level
poker skill metrics over time to measure evolutionary progress.

Key features:
- Periodic benchmark scheduling
- Historical snapshot storage
- Trend analysis and improvement metrics
- JSON export for external analysis
- API data formatting for frontend
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.entities import Fish

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSnapshot:
    """Single point-in-time benchmark snapshot."""

    frame: int
    timestamp: str
    generation_estimate: int  # Average generation of evaluated fish

    # Population-level bb/100 metrics
    pop_bb_per_100: float
    pop_weighted_bb: float
    pop_bb_vs_trivial: float
    pop_bb_vs_weak: float
    pop_bb_vs_moderate: float
    pop_bb_vs_strong: float

    # Strategy distribution
    strategy_distribution: Dict[str, int] = field(default_factory=dict)
    dominant_strategy: str = ""

    # Best performer
    best_fish_id: Optional[int] = None
    best_bb_per_100: float = 0.0
    best_strategy: str = ""

    # Per-baseline breakdown
    per_baseline_bb_per_100: Dict[str, float] = field(default_factory=dict)

    # Evaluation metadata
    fish_evaluated: int = 0
    total_hands: int = 0


@dataclass
class EvolutionBenchmarkHistory:
    """Complete history of benchmark snapshots over time."""

    snapshots: List[BenchmarkSnapshot] = field(default_factory=list)

    # Computed trends (updated on each snapshot)
    bb_per_100_trend: List[float] = field(default_factory=list)
    weighted_bb_trend: List[float] = field(default_factory=list)
    vs_trivial_trend: List[float] = field(default_factory=list)
    vs_weak_trend: List[float] = field(default_factory=list)
    vs_moderate_trend: List[float] = field(default_factory=list)
    vs_strong_trend: List[float] = field(default_factory=list)
    best_performer_trend: List[float] = field(default_factory=list)

    def add_snapshot(self, snapshot: BenchmarkSnapshot) -> None:
        """Add a new benchmark snapshot and update trends."""
        self.snapshots.append(snapshot)
        self.bb_per_100_trend.append(snapshot.pop_bb_per_100)
        self.weighted_bb_trend.append(snapshot.pop_weighted_bb)
        self.vs_trivial_trend.append(snapshot.pop_bb_vs_trivial)
        self.vs_weak_trend.append(snapshot.pop_bb_vs_weak)
        self.vs_moderate_trend.append(snapshot.pop_bb_vs_moderate)
        self.vs_strong_trend.append(snapshot.pop_bb_vs_strong)
        self.best_performer_trend.append(snapshot.best_bb_per_100)

    def get_improvement_metrics(self) -> Dict[str, Any]:
        """Calculate improvement metrics over time."""
        if len(self.snapshots) < 2:
            return {
                "status": "insufficient_data",
                "snapshots_collected": len(self.snapshots),
            }

        first = self.snapshots[0]
        last = self.snapshots[-1]

        # Calculate trend slope using linear regression
        def trend_slope(values: List[float]) -> float:
            """Simple linear regression slope."""
            if len(values) < 2:
                return 0.0
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            return numerator / denominator if denominator != 0 else 0.0

        # Calculate moving averages for smoother comparison
        def moving_avg(values: List[float], window: int = 3) -> float:
            """Get average of last N values."""
            if len(values) < window:
                return sum(values) / len(values) if values else 0.0
            return sum(values[-window:]) / window

        return {
            "status": "tracked",
            "total_snapshots": len(self.snapshots),
            "frames_tracked": last.frame - first.frame,
            "generation_start": first.generation_estimate,
            "generation_end": last.generation_estimate,
            # Overall skill progression
            "bb_per_100_start": round(first.pop_bb_per_100, 2),
            "bb_per_100_end": round(last.pop_bb_per_100, 2),
            "bb_per_100_change": round(last.pop_bb_per_100 - first.pop_bb_per_100, 2),
            "bb_per_100_slope": round(trend_slope(self.bb_per_100_trend), 4),
            "bb_per_100_recent_avg": round(moving_avg(self.bb_per_100_trend), 2),
            # Weighted skill (accounts for opponent difficulty)
            "weighted_bb_start": round(first.pop_weighted_bb, 2),
            "weighted_bb_end": round(last.pop_weighted_bb, 2),
            "weighted_bb_change": round(last.pop_weighted_bb - first.pop_weighted_bb, 2),
            # Per-tier progression
            "vs_trivial_change": round(
                last.pop_bb_vs_trivial - first.pop_bb_vs_trivial, 2
            ),
            "vs_weak_change": round(last.pop_bb_vs_weak - first.pop_bb_vs_weak, 2),
            "vs_moderate_change": round(
                last.pop_bb_vs_moderate - first.pop_bb_vs_moderate, 2
            ),
            "vs_strong_change": round(
                last.pop_bb_vs_strong - first.pop_bb_vs_strong, 2
            ),
            # Best performer progression
            "best_bb_start": round(first.best_bb_per_100, 2),
            "best_bb_end": round(last.best_bb_per_100, 2),
            "best_bb_change": round(
                last.best_bb_per_100 - first.best_bb_per_100, 2
            ),
            # Strategy evolution
            "dominant_strategy_start": first.dominant_strategy,
            "dominant_strategy_end": last.dominant_strategy,
            # Qualitative assessments
            "is_improving": last.pop_bb_per_100 > first.pop_bb_per_100,
            "trend_direction": "improving"
            if trend_slope(self.bb_per_100_trend) > 0.1
            else "declining"
            if trend_slope(self.bb_per_100_trend) < -0.1
            else "stable",
            "can_beat_trivial": last.pop_bb_vs_trivial > 10,  # > 10 bb/100
            "can_beat_weak": last.pop_bb_vs_weak > 5,  # > 5 bb/100
            "can_beat_moderate": last.pop_bb_vs_moderate > 0,  # Positive
            "can_beat_strong": last.pop_bb_vs_strong > 0,  # Positive
        }

    def get_variance_metrics(self) -> Dict[str, float]:
        """Get variance/stability metrics for the population."""
        if len(self.bb_per_100_trend) < 3:
            return {}

        return {
            "bb_per_100_std": round(statistics.stdev(self.bb_per_100_trend), 2),
            "vs_strong_std": round(statistics.stdev(self.vs_strong_trend), 2),
            "best_performer_std": round(statistics.stdev(self.best_performer_trend), 2),
        }


class EvolutionBenchmarkTracker:
    """Manages periodic benchmark evaluation and longitudinal tracking."""

    def __init__(
        self,
        eval_interval_frames: int = 15_000,  # ~8 minutes at 30fps
        export_path: Optional[Path] = None,
        use_quick_benchmark: bool = True,
    ):
        """Initialize the evolution benchmark tracker.

        Args:
            eval_interval_frames: Frames between benchmark runs
            export_path: Optional path to export JSON data
            use_quick_benchmark: Use quick (True) or full (False) benchmark config
        """
        self.eval_interval_frames = eval_interval_frames
        self.export_path = export_path
        self.use_quick_benchmark = use_quick_benchmark
        self.history = EvolutionBenchmarkHistory()
        self._last_eval_frame = -eval_interval_frames  # Allow immediate first run

    def should_run(self, current_frame: int) -> bool:
        """Check if it's time for a benchmark run."""
        return current_frame - self._last_eval_frame >= self.eval_interval_frames

    def run_and_record(
        self,
        fish_population: List["Fish"],
        current_frame: int,
        force: bool = False,
    ) -> Optional[BenchmarkSnapshot]:
        """Run benchmark and record results if it's time.

        Args:
            fish_population: All fish in the simulation
            current_frame: Current simulation frame
            force: Force run even if interval hasn't passed

        Returns:
            BenchmarkSnapshot if run, None if skipped
        """
        if not force and not self.should_run(current_frame):
            return None

        # Import here to avoid circular imports
        from core.poker.evaluation.comprehensive_benchmark import (
            run_quick_benchmark,
            run_full_benchmark,
        )

        # Run the appropriate benchmark
        if self.use_quick_benchmark:
            result = run_quick_benchmark(fish_population, current_frame)
        else:
            result = run_full_benchmark(fish_population, current_frame)

        # Calculate average generation
        avg_generation = 0
        if fish_population:
            gens = [getattr(f, "generation", 0) for f in fish_population]
            avg_generation = int(sum(gens) / len(gens)) if gens else 0

        # Create snapshot from result
        snapshot = BenchmarkSnapshot(
            frame=current_frame,
            timestamp=result.timestamp,
            generation_estimate=avg_generation,
            pop_bb_per_100=result.pop_avg_bb_per_100,
            pop_weighted_bb=result.pop_weighted_bb_per_100,
            pop_bb_vs_trivial=result.pop_bb_vs_trivial,
            pop_bb_vs_weak=result.pop_bb_vs_weak,
            pop_bb_vs_moderate=result.pop_bb_vs_moderate,
            pop_bb_vs_strong=result.pop_bb_vs_strong,
            strategy_distribution=result.strategy_count.copy(),
            dominant_strategy=max(
                result.strategy_count.items(), key=lambda x: x[1]
            )[0]
            if result.strategy_count
            else "",
            best_fish_id=result.best_fish_id,
            best_bb_per_100=result.best_bb_per_100,
            best_strategy=result.best_strategy,
            per_baseline_bb_per_100=result.pop_vs_baseline.copy(),
            fish_evaluated=result.fish_evaluated,
            total_hands=result.total_hands,
        )

        self.history.add_snapshot(snapshot)
        self._last_eval_frame = current_frame

        # Export if configured
        if self.export_path:
            self._export_to_json()

        logger.info(
            f"Evolution benchmark @ frame {current_frame}: "
            f"pop_bb/100={snapshot.pop_bb_per_100:.1f}, "
            f"vs_weak={snapshot.pop_bb_vs_weak:.1f}, "
            f"vs_strong={snapshot.pop_bb_vs_strong:.1f}, "
            f"best={snapshot.best_bb_per_100:.1f} ({snapshot.best_strategy})"
        )

        return snapshot

    def _export_to_json(self) -> None:
        """Export history to JSON file."""
        if self.export_path is None:
            return

        try:
            data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_snapshots": len(self.history.snapshots),
                },
                "snapshots": [
                    {
                        "frame": s.frame,
                        "timestamp": s.timestamp,
                        "generation": s.generation_estimate,
                        "pop_bb_per_100": round(s.pop_bb_per_100, 2),
                        "pop_weighted_bb": round(s.pop_weighted_bb, 2),
                        "pop_bb_vs_trivial": round(s.pop_bb_vs_trivial, 2),
                        "pop_bb_vs_weak": round(s.pop_bb_vs_weak, 2),
                        "pop_bb_vs_moderate": round(s.pop_bb_vs_moderate, 2),
                        "pop_bb_vs_strong": round(s.pop_bb_vs_strong, 2),
                        "strategy_distribution": s.strategy_distribution,
                        "dominant_strategy": s.dominant_strategy,
                        "best_bb_per_100": round(s.best_bb_per_100, 2),
                        "best_strategy": s.best_strategy,
                        "per_baseline": {
                            k: round(v, 2)
                            for k, v in s.per_baseline_bb_per_100.items()
                        },
                        "fish_evaluated": s.fish_evaluated,
                        "total_hands": s.total_hands,
                    }
                    for s in self.history.snapshots
                ],
                "trends": {
                    "bb_per_100": [round(v, 2) for v in self.history.bb_per_100_trend],
                    "weighted_bb": [round(v, 2) for v in self.history.weighted_bb_trend],
                    "vs_trivial": [round(v, 2) for v in self.history.vs_trivial_trend],
                    "vs_weak": [round(v, 2) for v in self.history.vs_weak_trend],
                    "vs_moderate": [
                        round(v, 2) for v in self.history.vs_moderate_trend
                    ],
                    "vs_strong": [round(v, 2) for v in self.history.vs_strong_trend],
                    "best_performer": [
                        round(v, 2) for v in self.history.best_performer_trend
                    ],
                },
                "improvement_metrics": self.history.get_improvement_metrics(),
                "variance_metrics": self.history.get_variance_metrics(),
            }

            self.export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.export_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to export benchmark history: {e}")

    def get_api_data(self) -> Dict[str, Any]:
        """Get data formatted for API/frontend consumption."""
        return {
            "history": [
                {
                    "frame": s.frame,
                    "generation": s.generation_estimate,
                    "pop_bb_per_100": round(s.pop_bb_per_100, 2),
                    "pop_weighted_bb": round(s.pop_weighted_bb, 2),
                    "vs_trivial": round(s.pop_bb_vs_trivial, 2),
                    "vs_weak": round(s.pop_bb_vs_weak, 2),
                    "vs_moderate": round(s.pop_bb_vs_moderate, 2),
                    "vs_strong": round(s.pop_bb_vs_strong, 2),
                    "best_bb": round(s.best_bb_per_100, 2),
                    "dominant_strategy": s.dominant_strategy,
                    "per_baseline": {
                        k: round(v, 2) for k, v in s.per_baseline_bb_per_100.items()
                    },
                }
                for s in self.history.snapshots
            ],
            "improvement": self.history.get_improvement_metrics(),
            "latest": {
                "frame": self.history.snapshots[-1].frame,
                "generation": self.history.snapshots[-1].generation_estimate,
                "pop_bb_per_100": round(self.history.snapshots[-1].pop_bb_per_100, 2),
                "pop_weighted_bb": round(
                    self.history.snapshots[-1].pop_weighted_bb, 2
                ),
                "vs_trivial": round(self.history.snapshots[-1].pop_bb_vs_trivial, 2),
                "vs_weak": round(self.history.snapshots[-1].pop_bb_vs_weak, 2),
                "vs_moderate": round(
                    self.history.snapshots[-1].pop_bb_vs_moderate, 2
                ),
                "vs_strong": round(self.history.snapshots[-1].pop_bb_vs_strong, 2),
                "best_bb": round(self.history.snapshots[-1].best_bb_per_100, 2),
                "best_strategy": self.history.snapshots[-1].best_strategy,
                "dominant_strategy": self.history.snapshots[-1].dominant_strategy,
                "per_baseline": {
                    k: round(v, 2)
                    for k, v in self.history.snapshots[
                        -1
                    ].per_baseline_bb_per_100.items()
                },
            }
            if self.history.snapshots
            else None,
        }

    def get_latest_snapshot(self) -> Optional[BenchmarkSnapshot]:
        """Get the most recent benchmark snapshot."""
        return self.history.snapshots[-1] if self.history.snapshots else None


# Global tracker instance
_global_tracker: Optional[EvolutionBenchmarkTracker] = None


def get_global_benchmark_tracker(
    export_path: Optional[Path] = None,
) -> EvolutionBenchmarkTracker:
    """Get or create the global benchmark tracker.

    Args:
        export_path: Optional path for JSON export

    Returns:
        The global EvolutionBenchmarkTracker instance
    """
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = EvolutionBenchmarkTracker(export_path=export_path)
    elif export_path is not None and _global_tracker.export_path is None:
        _global_tracker.export_path = export_path

    return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global tracker (useful for testing)."""
    global _global_tracker
    _global_tracker = None
