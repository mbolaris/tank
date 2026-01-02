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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

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
    pop_bb_vs_strong: float = 0.0
    pop_bb_vs_expert: float = 0.0  # Elo rating metrics (more stable than raw bb/100)
    pop_mean_elo: float = 1200.0
    pop_median_elo: float = 1200.0
    elo_tier_distribution: dict[str, int] = field(default_factory=dict)

    # Confidence-based skill assessments
    confidence_vs_weak: float = 0.5
    confidence_vs_moderate: float = 0.5
    confidence_vs_strong: float = 0.5
    confidence_vs_expert: float = 0.5

    # Strategy distribution
    strategy_distribution: dict[str, int] = field(default_factory=dict)
    dominant_strategy: str = ""

    # Best performer
    best_fish_id: int | None = None
    best_bb_per_100: float = 0.0
    best_elo: float = 1200.0
    best_strategy: str = ""

    # Per-baseline breakdown
    per_baseline_bb_per_100: dict[str, float] = field(default_factory=dict)

    # Evaluation metadata
    fish_evaluated: int = 0
    total_hands: int = 0


@dataclass
class EvolutionBenchmarkHistory:
    """Complete history of benchmark snapshots over time."""

    snapshots: list[BenchmarkSnapshot] = field(default_factory=list)

    # Raw trends (updated on each snapshot)
    bb_per_100_trend: list[float] = field(default_factory=list)
    weighted_bb_trend: list[float] = field(default_factory=list)
    vs_trivial_trend: list[float] = field(default_factory=list)
    vs_weak_trend: list[float] = field(default_factory=list)
    vs_moderate_trend: list[float] = field(default_factory=list)
    vs_strong_trend: list[float] = field(default_factory=list)
    best_performer_trend: list[float] = field(default_factory=list)

    # Elo-based trends (more stable)
    elo_trend: list[float] = field(default_factory=list)
    elo_median_trend: list[float] = field(default_factory=list)
    best_elo_trend: list[float] = field(default_factory=list)

    # Confidence-based trends
    confidence_weak_trend: list[float] = field(default_factory=list)
    confidence_moderate_trend: list[float] = field(default_factory=list)
    confidence_strong_trend: list[float] = field(default_factory=list)

    # EMA smoothed trends (reduces noise for clearer improvement signals)
    # Using alpha=0.3 for moderate smoothing (higher = more responsive, lower = smoother)
    ema_alpha: float = 0.3
    elo_ema: list[float] = field(default_factory=list)
    bb_per_100_ema: list[float] = field(default_factory=list)
    vs_strong_ema: list[float] = field(default_factory=list)
    confidence_strong_ema: list[float] = field(default_factory=list)

    def _compute_ema(self, new_value: float, ema_list: list[float]) -> float:
        """Compute exponential moving average for a new value."""
        if not ema_list:
            return new_value
        prev_ema = ema_list[-1]
        return self.ema_alpha * new_value + (1 - self.ema_alpha) * prev_ema

    def add_snapshot(self, snapshot: BenchmarkSnapshot) -> None:
        """Add a new benchmark snapshot and update trends."""
        self.snapshots.append(snapshot)

        # Raw trends
        self.bb_per_100_trend.append(snapshot.pop_bb_per_100)
        self.weighted_bb_trend.append(snapshot.pop_weighted_bb)
        self.vs_trivial_trend.append(snapshot.pop_bb_vs_trivial)
        self.vs_weak_trend.append(snapshot.pop_bb_vs_weak)
        self.vs_moderate_trend.append(snapshot.pop_bb_vs_moderate)
        self.vs_strong_trend.append(snapshot.pop_bb_vs_strong)
        self.best_performer_trend.append(snapshot.best_bb_per_100)

        # Elo trends (more stable than bb/100)
        self.elo_trend.append(snapshot.pop_mean_elo)
        self.elo_median_trend.append(snapshot.pop_median_elo)
        self.best_elo_trend.append(snapshot.best_elo)

        # Confidence trends
        self.confidence_weak_trend.append(snapshot.confidence_vs_weak)
        self.confidence_moderate_trend.append(snapshot.confidence_vs_moderate)
        self.confidence_strong_trend.append(snapshot.confidence_vs_strong)

        # EMA smoothed trends (reduces variance, shows clearer improvement)
        self.elo_ema.append(self._compute_ema(snapshot.pop_mean_elo, self.elo_ema))
        self.bb_per_100_ema.append(self._compute_ema(snapshot.pop_bb_per_100, self.bb_per_100_ema))
        self.vs_strong_ema.append(self._compute_ema(snapshot.pop_bb_vs_strong, self.vs_strong_ema))
        self.confidence_strong_ema.append(
            self._compute_ema(snapshot.confidence_vs_strong, self.confidence_strong_ema)
        )

    def get_improvement_metrics(self) -> dict[str, Any]:
        """Calculate improvement metrics over time.

        Uses Elo ratings and EMA smoothing for more stable trend analysis.
        """
        if len(self.snapshots) < 2:
            return {
                "status": "insufficient_data",
                "snapshots_collected": len(self.snapshots),
            }

        first = self.snapshots[0]
        last = self.snapshots[-1]

        # Calculate trend slope using linear regression
        def trend_slope(values: list[float]) -> float:
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
        def moving_avg(values: list[float], window: int = 3) -> float:
            """Get average of last N values."""
            if len(values) < window:
                return sum(values) / len(values) if values else 0.0
            return sum(values[-window:]) / window

        # Elo-based improvement (more stable than bb/100)
        elo_start = self.elo_trend[0] if self.elo_trend else 1200.0
        elo_end = self.elo_trend[-1] if self.elo_trend else 1200.0
        elo_ema_end = self.elo_ema[-1] if self.elo_ema else 1200.0

        # Confidence-based improvement (probability of winning)
        conf_strong_start = self.confidence_strong_trend[0] if self.confidence_strong_trend else 0.5
        conf_strong_end = self.confidence_strong_trend[-1] if self.confidence_strong_trend else 0.5
        conf_strong_ema_end = self.confidence_strong_ema[-1] if self.confidence_strong_ema else 0.5

        # Use EMA for trend direction (more stable than raw values)
        elo_slope = trend_slope(self.elo_ema) if self.elo_ema else 0.0

        # Determine trend direction based on Elo EMA slope
        # Elo change of ~10 points per snapshot is meaningful improvement
        if elo_slope > 5:
            trend_direction = "improving"
        elif elo_slope < -5:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return {
            "status": "tracked",
            "total_snapshots": len(self.snapshots),
            "frames_tracked": last.frame - first.frame,
            "generation_start": first.generation_estimate,
            "generation_end": last.generation_estimate,
            # Elo-based skill progression (primary metric - more stable)
            "elo_start": round(elo_start, 1),
            "elo_end": round(elo_end, 1),
            "elo_change": round(elo_end - elo_start, 1),
            "elo_ema_current": round(elo_ema_end, 1),
            "elo_slope": round(elo_slope, 2),
            # Confidence-based assessment (probability of winning)
            "confidence_vs_strong_start": round(conf_strong_start, 3),
            "confidence_vs_strong_end": round(conf_strong_end, 3),
            "confidence_vs_strong_ema": round(conf_strong_ema_end, 3),
            "confidence_change": round(conf_strong_end - conf_strong_start, 3),
            # Overall bb/100 skill progression (raw metrics for reference)
            "bb_per_100_start": round(first.pop_bb_per_100, 2),
            "bb_per_100_end": round(last.pop_bb_per_100, 2),
            "bb_per_100_change": round(last.pop_bb_per_100 - first.pop_bb_per_100, 2),
            "bb_per_100_ema_current": round(
                self.bb_per_100_ema[-1] if self.bb_per_100_ema else 0.0, 2
            ),
            # Per-tier progression
            "vs_trivial_change": round(last.pop_bb_vs_trivial - first.pop_bb_vs_trivial, 2),
            "vs_weak_change": round(last.pop_bb_vs_weak - first.pop_bb_vs_weak, 2),
            "vs_moderate_change": round(last.pop_bb_vs_moderate - first.pop_bb_vs_moderate, 2),
            "vs_strong_change": round(last.pop_bb_vs_strong - first.pop_bb_vs_strong, 2),
            "vs_strong_ema_current": round(
                self.vs_strong_ema[-1] if self.vs_strong_ema else 0.0, 2
            ),
            # Best performer progression
            "best_elo_start": round(first.best_elo, 1),
            "best_elo_end": round(last.best_elo, 1),
            "best_elo_change": round(last.best_elo - first.best_elo, 1),
            "best_bb_start": round(first.best_bb_per_100, 2),
            "best_bb_end": round(last.best_bb_per_100, 2),
            "best_bb_change": round(last.best_bb_per_100 - first.best_bb_per_100, 2),
            # Strategy evolution
            "dominant_strategy_start": first.dominant_strategy,
            "dominant_strategy_end": last.dominant_strategy,
            # Qualitative assessments using Elo and confidence
            "is_improving": elo_end > elo_start + 20,  # Significant Elo gain
            "trend_direction": trend_direction,
            # Skill tier assessments (based on confidence, not raw bb/100)
            "can_beat_trivial": last.pop_bb_vs_trivial > 10,
            "can_beat_weak": last.confidence_vs_weak > 0.7,  # >70% confident
            "can_beat_moderate": last.confidence_vs_moderate > 0.6,  # >60% confident
            "can_beat_strong": last.confidence_vs_strong > 0.55,  # >55% confident
            "can_beat_expert": last.confidence_vs_expert > 0.50,  # >50% = profitable vs GTO
            # Skill tier distribution (latest)
            "elo_tier_distribution": last.elo_tier_distribution,
        }

    def get_variance_metrics(self) -> dict[str, float]:
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
        export_path: Path | None = None,
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

        return snapshot

    def _assign_rewards(
        self,
        results: PopulationBenchmarkResult,
        fish_population: list[Fish],
        reward_callback: Callable[[Fish, float], None],
    ) -> None:
        """Assign energy rewards to high-performing fish."""
        import os

        if not results.individual_results:
            return

        enabled = os.getenv("TANK_BENCHMARK_REWARD_ENABLED", "1").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not enabled:
            return

        # Reward scale: energy per 1 bb/100
        # Example: 10 bb/100 * 0.1 = 1.0 energy
        scale = float(os.getenv("TANK_BENCHMARK_REWARD_SCALE", "0.1"))
        max_reward = float(os.getenv("TANK_BENCHMARK_REWARD_MAX", "20.0"))

        for res in results.individual_results:
            # Reward based on weighted performance (overall skill)
            score = res.weighted_bb_per_100

            # Bonus for beating Expert
            if res.avg_bb_per_100_vs_expert > 0:
                score += res.avg_bb_per_100_vs_expert * 0.5

            if score <= 0:
                continue

            energy_reward = min(score * scale, max_reward)

            # Find the live fish entity
            fish = next((f for f in fish_population if f.fish_id == res.fish_id), None)
            if fish:
                try:
                    reward_callback(fish, energy_reward)
                except Exception as e:
                    logger.error(f"Failed to apply reward to fish {fish.fish_id}: {e}")

    def run_and_record(
        self,
        fish_population: list[Fish],
        current_frame: int,
        force: bool = False,
        reward_callback: Callable[[Fish, float], None] | None = None,
    ) -> BenchmarkSnapshot | None:
        """Run benchmark and record results if it's time.

        Args:
            fish_population: All fish in the simulation
            current_frame: Current simulation frame
            force: Force run even if interval hasn't passed
            reward_callback: Optional callback to apply energy rewards (fish, amount)

        Returns:
            BenchmarkSnapshot if run, None if skipped
        """
        if not force and not self.should_run(current_frame):
            return None

        # Import here to avoid circular imports
        import time as time_module

        from core.poker.evaluation.comprehensive_benchmark import (
            run_full_benchmark,
            run_quick_benchmark,
        )

        # Run the appropriate benchmark with timing
        start_time = time_module.time()
        logger.info(
            f"Starting {'quick' if self.use_quick_benchmark else 'full'} benchmark for {len(fish_population)} fish..."
        )

        if self.use_quick_benchmark:
            result = run_quick_benchmark(fish_population, current_frame)
        else:
            result = run_full_benchmark(fish_population, current_frame)

        elapsed = time_module.time() - start_time
        logger.info(f"Benchmark completed in {elapsed:.1f}s ({result.total_hands:,} hands)")

        # Apply rewards if callback provided
        if reward_callback:
            self._assign_rewards(result, fish_population, reward_callback)

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
            pop_bb_vs_expert=result.pop_bb_vs_expert,
            # Elo rating metrics (more stable than raw bb/100)
            pop_mean_elo=result.pop_mean_elo,
            pop_median_elo=result.pop_median_elo,
            elo_tier_distribution=result.elo_tier_distribution.copy(),
            # Confidence-based skill assessments
            confidence_vs_weak=result.pop_confidence_vs_weak,
            confidence_vs_moderate=result.pop_confidence_vs_moderate,
            confidence_vs_strong=result.pop_confidence_vs_strong,
            confidence_vs_expert=result.pop_confidence_vs_expert,
            strategy_distribution=result.strategy_count.copy(),
            dominant_strategy=(
                max(result.strategy_count.items(), key=lambda x: x[1])[0]
                if result.strategy_count
                else ""
            ),
            best_fish_id=result.best_fish_id,
            best_bb_per_100=result.best_bb_per_100,
            best_elo=result.best_elo,
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
            f"pop_elo={snapshot.pop_mean_elo:.0f}, "
            f"conf_strong={snapshot.confidence_vs_strong:.0%}, "
            f"vs_strong={snapshot.pop_bb_vs_strong:.1f}, "
            f"best_elo={snapshot.best_elo:.0f} ({snapshot.best_strategy})"
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
                        # Elo ratings (primary stable metric)
                        "pop_mean_elo": round(s.pop_mean_elo, 1),
                        "pop_median_elo": round(s.pop_median_elo, 1),
                        "elo_tier_distribution": s.elo_tier_distribution,
                        # Confidence metrics (probability of winning)
                        "confidence_vs_weak": round(s.confidence_vs_weak, 3),
                        "confidence_vs_moderate": round(s.confidence_vs_moderate, 3),
                        "confidence_vs_strong": round(s.confidence_vs_strong, 3),
                        # Raw bb/100 metrics (for reference)
                        "pop_bb_per_100": round(s.pop_bb_per_100, 2),
                        "pop_weighted_bb": round(s.pop_weighted_bb, 2),
                        "pop_bb_vs_trivial": round(s.pop_bb_vs_trivial, 2),
                        "pop_bb_vs_weak": round(s.pop_bb_vs_weak, 2),
                        "pop_bb_vs_moderate": round(s.pop_bb_vs_moderate, 2),
                        "pop_bb_vs_strong": round(s.pop_bb_vs_strong, 2),
                        "strategy_distribution": s.strategy_distribution,
                        "dominant_strategy": s.dominant_strategy,
                        "best_bb_per_100": round(s.best_bb_per_100, 2),
                        "best_elo": round(s.best_elo, 1),
                        "best_strategy": s.best_strategy,
                        "per_baseline": {
                            k: round(v, 2) for k, v in s.per_baseline_bb_per_100.items()
                        },
                        "fish_evaluated": s.fish_evaluated,
                        "total_hands": s.total_hands,
                    }
                    for s in self.history.snapshots
                ],
                "trends": {
                    # Elo trends (more stable, preferred)
                    "elo": [round(v, 1) for v in self.history.elo_trend],
                    "elo_median": [round(v, 1) for v in self.history.elo_median_trend],
                    "best_elo": [round(v, 1) for v in self.history.best_elo_trend],
                    # EMA smoothed trends (reduced variance)
                    "elo_ema": [round(v, 1) for v in self.history.elo_ema],
                    "bb_per_100_ema": [round(v, 2) for v in self.history.bb_per_100_ema],
                    "vs_strong_ema": [round(v, 2) for v in self.history.vs_strong_ema],
                    "confidence_strong_ema": [
                        round(v, 3) for v in self.history.confidence_strong_ema
                    ],
                    # Confidence trends
                    "confidence_weak": [round(v, 3) for v in self.history.confidence_weak_trend],
                    "confidence_moderate": [
                        round(v, 3) for v in self.history.confidence_moderate_trend
                    ],
                    "confidence_strong": [
                        round(v, 3) for v in self.history.confidence_strong_trend
                    ],
                    # Raw bb/100 trends (for reference)
                    "bb_per_100": [round(v, 2) for v in self.history.bb_per_100_trend],
                    "weighted_bb": [round(v, 2) for v in self.history.weighted_bb_trend],
                    "vs_trivial": [round(v, 2) for v in self.history.vs_trivial_trend],
                    "vs_weak": [round(v, 2) for v in self.history.vs_weak_trend],
                    "vs_moderate": [round(v, 2) for v in self.history.vs_moderate_trend],
                    "vs_strong": [round(v, 2) for v in self.history.vs_strong_trend],
                    "best_performer": [round(v, 2) for v in self.history.best_performer_trend],
                },
                "improvement_metrics": self.history.get_improvement_metrics(),
                "variance_metrics": self.history.get_variance_metrics(),
            }

            self.export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.export_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to export benchmark history: {e}")

    def get_api_data(self) -> dict[str, Any]:
        """Get data formatted for API/frontend consumption."""
        return {
            "history": [
                {
                    "frame": s.frame,
                    "timestamp": s.timestamp,
                    "generation": s.generation_estimate,
                    # Elo ratings (primary stable metric)
                    "pop_mean_elo": round(s.pop_mean_elo, 1),
                    "pop_median_elo": round(s.pop_median_elo, 1),
                    "elo_tier_distribution": s.elo_tier_distribution,
                    # Confidence metrics (probability of winning)
                    "conf_weak": round(s.confidence_vs_weak, 3),
                    "conf_moderate": round(s.confidence_vs_moderate, 3),
                    "conf_strong": round(s.confidence_vs_strong, 3),
                    "conf_expert": round(s.confidence_vs_expert, 3),
                    # Raw bb/100 metrics (for reference)
                    "pop_bb_per_100": round(s.pop_bb_per_100, 2),
                    "pop_weighted_bb": round(s.pop_weighted_bb, 2),
                    "vs_trivial": round(s.pop_bb_vs_trivial, 2),
                    "vs_weak": round(s.pop_bb_vs_weak, 2),
                    "vs_moderate": round(s.pop_bb_vs_moderate, 2),
                    "vs_strong": round(s.pop_bb_vs_strong, 2),
                    "vs_expert": round(s.pop_bb_vs_expert, 2),
                    "best_bb": round(s.best_bb_per_100, 2),
                    "best_elo": round(s.best_elo, 1),
                    "dominant_strategy": s.dominant_strategy,
                    "per_baseline": {k: round(v, 2) for k, v in s.per_baseline_bb_per_100.items()},
                    "fish_evaluated": s.fish_evaluated,
                    "total_hands": s.total_hands,
                }
                for s in self.history.snapshots
            ],
            # EMA smoothed trends for stable visualization
            "ema_trends": {
                "elo": [round(v, 1) for v in self.history.elo_ema],
                "bb_per_100": [round(v, 2) for v in self.history.bb_per_100_ema],
                "vs_strong": [round(v, 2) for v in self.history.vs_strong_ema],
                "conf_strong": [round(v, 3) for v in self.history.confidence_strong_ema],
            },
            "improvement": self.history.get_improvement_metrics(),
            "latest": (
                {
                    "frame": self.history.snapshots[-1].frame,
                    "timestamp": self.history.snapshots[-1].timestamp,
                    "generation": self.history.snapshots[-1].generation_estimate,
                    # Elo ratings (primary stable metric)
                    "pop_mean_elo": round(self.history.snapshots[-1].pop_mean_elo, 1),
                    "pop_median_elo": round(self.history.snapshots[-1].pop_median_elo, 1),
                    "elo_tier_distribution": self.history.snapshots[-1].elo_tier_distribution,
                    # EMA smoothed values (for stable current reading)
                    "elo_ema": (
                        round(self.history.elo_ema[-1], 1) if self.history.elo_ema else 1200.0
                    ),
                    # Confidence metrics
                    "conf_weak": round(self.history.snapshots[-1].confidence_vs_weak, 3),
                    "conf_moderate": round(self.history.snapshots[-1].confidence_vs_moderate, 3),
                    "conf_strong": round(self.history.snapshots[-1].confidence_vs_strong, 3),
                    "conf_expert": round(self.history.snapshots[-1].confidence_vs_expert, 3),
                    "conf_strong_ema": (
                        round(self.history.confidence_strong_ema[-1], 3)
                        if self.history.confidence_strong_ema
                        else 0.5
                    ),
                    # Raw bb/100 metrics (for reference)
                    "pop_bb_per_100": round(self.history.snapshots[-1].pop_bb_per_100, 2),
                    "pop_weighted_bb": round(self.history.snapshots[-1].pop_weighted_bb, 2),
                    "vs_trivial": round(self.history.snapshots[-1].pop_bb_vs_trivial, 2),
                    "vs_weak": round(self.history.snapshots[-1].pop_bb_vs_weak, 2),
                    "vs_moderate": round(self.history.snapshots[-1].pop_bb_vs_moderate, 2),
                    "vs_strong": round(self.history.snapshots[-1].pop_bb_vs_strong, 2),
                    "best_bb": round(self.history.snapshots[-1].best_bb_per_100, 2),
                    "best_elo": round(self.history.snapshots[-1].best_elo, 1),
                    "best_strategy": self.history.snapshots[-1].best_strategy,
                    "dominant_strategy": self.history.snapshots[-1].dominant_strategy,
                    "per_baseline": {
                        k: round(v, 2)
                        for k, v in self.history.snapshots[-1].per_baseline_bb_per_100.items()
                    },
                    "fish_evaluated": self.history.snapshots[-1].fish_evaluated,
                    "total_hands": self.history.snapshots[-1].total_hands,
                }
                if self.history.snapshots
                else None
            ),
        }

    def get_latest_snapshot(self) -> BenchmarkSnapshot | None:
        """Get the most recent benchmark snapshot."""
        return self.history.snapshots[-1] if self.history.snapshots else None

    def get_history(self) -> list[BenchmarkSnapshot]:
        """Get the full history of benchmark snapshots."""
        return self.history.snapshots


# Global tracker instance
_global_tracker: EvolutionBenchmarkTracker | None = None


def get_global_benchmark_tracker(
    export_path: Path | None = None,
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
