"""Snapshot model and payload helpers for poker evolution benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.poker.evaluation.benchmark_eval import compute_mean_ci_95


def _round_ci(ci: tuple[float, float], digits: int = 2) -> list[float]:
    """Round a confidence interval for JSON/API payloads."""
    return [round(ci[0], digits), round(ci[1], digits)]


@dataclass
class BenchmarkSnapshot:
    """Single point-in-time benchmark snapshot."""

    frame: int
    timestamp: str
    generation_estimate: int

    # Population-level bb/100 metrics
    pop_bb_per_100: float
    pop_weighted_bb: float
    pop_bb_vs_trivial: float
    pop_bb_vs_weak: float
    pop_bb_vs_moderate: float
    pop_bb_per_100_ci_95: tuple[float, float] = (0.0, 0.0)
    pop_bb_per_100_se: float = 0.0
    pop_weighted_bb_ci_95: tuple[float, float] = (0.0, 0.0)
    pop_weighted_bb_se: float = 0.0
    pop_bb_vs_strong: float = 0.0
    pop_bb_vs_expert: float = 0.0

    # Elo rating metrics
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


def snapshot_uncertainty_payload(snapshot: BenchmarkSnapshot) -> dict[str, Any]:
    """Uncertainty fields shared by export and API benchmark payloads."""
    return {
        "pop_bb_per_100_ci_95": _round_ci(snapshot.pop_bb_per_100_ci_95),
        "pop_bb_per_100_se": round(snapshot.pop_bb_per_100_se, 4),
        "pop_weighted_bb_ci_95": _round_ci(snapshot.pop_weighted_bb_ci_95),
        "pop_weighted_bb_se": round(snapshot.pop_weighted_bb_se, 4),
    }


def benchmark_result_uncertainty(result: Any) -> dict[str, Any]:
    """Build BenchmarkSnapshot uncertainty fields from a population result."""
    individual_results = getattr(result, "individual_results", [])
    all_bb = [r.overall_bb_per_100 for r in individual_results]
    all_weighted = [r.weighted_bb_per_100 for r in individual_results]

    pop_ci, pop_se = compute_mean_ci_95(all_bb)
    weighted_ci, weighted_se = compute_mean_ci_95(all_weighted)

    if not all_bb:
        pop_ci = getattr(result, "pop_avg_bb_per_100_ci_95", (0.0, 0.0))
    return {
        "pop_bb_per_100_ci_95": pop_ci,
        "pop_bb_per_100_se": pop_se,
        "pop_weighted_bb_ci_95": weighted_ci,
        "pop_weighted_bb_se": weighted_se,
    }
