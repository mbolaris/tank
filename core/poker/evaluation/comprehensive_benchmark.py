"""Comprehensive benchmark evaluation system for poker evolution.

This module provides the sub-tournament runner that evaluates fish
against structured baseline opponents to measure pure poker skill
independent of ecosystem dynamics.

Key features:
- Parallel evaluation of multiple fish
- Per-baseline breakdown (weak/moderate/strong)
- Strategy-type performance analysis
- Population-level aggregate metrics
"""

from __future__ import annotations

import logging
import random as rng_module
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    SingleBenchmarkResult,
    evaluate_vs_single_benchmark_duplicate,
)
from core.poker.evaluation.benchmark_suite import (
    BASELINE_OPPONENTS,
    BaselineDifficulty,
    ComprehensiveBenchmarkConfig,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class FishBenchmarkResult:
    """Complete benchmark results for a single fish."""

    fish_id: int
    fish_generation: int
    strategy_id: str
    strategy_params: Dict[str, float]

    # Per-baseline results
    vs_baselines: Dict[str, SingleBenchmarkResult] = field(default_factory=dict)

    # Aggregate scores by difficulty tier
    avg_bb_per_100_vs_trivial: float = 0.0  # vs always_fold, random
    avg_bb_per_100_vs_weak: float = 0.0  # vs calling station, rock
    avg_bb_per_100_vs_moderate: float = 0.0  # vs TAG, LAG
    avg_bb_per_100_vs_strong: float = 0.0  # vs balanced, maniac
    overall_bb_per_100: float = 0.0
    weighted_bb_per_100: float = 0.0  # Weighted by baseline difficulty

    # Fish-vs-fish results (if available)
    bb_per_100_vs_fish: Optional[float] = None

    # Total hands played across all benchmarks
    total_hands: int = 0

    def compute_aggregates(self) -> None:
        """Compute aggregate scores from per-baseline results."""
        # Map strategy IDs to difficulty tiers
        trivial_ids = ["always_fold", "random"]
        weak_ids = ["loose_passive", "tight_passive"]
        moderate_ids = ["tight_aggressive", "loose_aggressive"]
        strong_ids = ["balanced", "maniac"]

        def avg_bb(baseline_ids: List[str]) -> Tuple[float, int]:
            """Get average bb/100 and total hands for a set of baselines."""
            results = [
                self.vs_baselines[bid]
                for bid in baseline_ids
                if bid in self.vs_baselines
            ]
            if not results:
                return 0.0, 0
            total_bb = sum(r.bb_per_100 for r in results)
            total_hands = sum(r.hands_played for r in results)
            return total_bb / len(results), total_hands

        self.avg_bb_per_100_vs_trivial, hands_trivial = avg_bb(trivial_ids)
        self.avg_bb_per_100_vs_weak, hands_weak = avg_bb(weak_ids)
        self.avg_bb_per_100_vs_moderate, hands_moderate = avg_bb(moderate_ids)
        self.avg_bb_per_100_vs_strong, hands_strong = avg_bb(strong_ids)

        self.total_hands = hands_trivial + hands_weak + hands_moderate + hands_strong

        # Overall unweighted average
        all_results = list(self.vs_baselines.values())
        if all_results:
            self.overall_bb_per_100 = sum(r.bb_per_100 for r in all_results) / len(
                all_results
            )

        # Weighted average using baseline weights
        weights = {b.strategy_id: b.weight for b in BASELINE_OPPONENTS}
        weighted_sum = 0.0
        weight_total = 0.0
        for bid, result in self.vs_baselines.items():
            w = weights.get(bid, 1.0)
            weighted_sum += result.bb_per_100 * w
            weight_total += w
        if weight_total > 0:
            self.weighted_bb_per_100 = weighted_sum / weight_total

    def skill_rating(self) -> str:
        """Categorize skill level based on performance against baselines."""
        # Must beat trivial opponents significantly
        if self.avg_bb_per_100_vs_trivial < 10:
            return "failing"
        # Check performance against each tier
        if self.avg_bb_per_100_vs_strong > 5:
            return "expert"
        if self.avg_bb_per_100_vs_strong > 0:
            return "advanced"
        if self.avg_bb_per_100_vs_moderate > 5:
            return "intermediate"
        if self.avg_bb_per_100_vs_weak > 10:
            return "beginner"
        return "novice"


@dataclass
class PopulationBenchmarkResult:
    """Aggregate benchmark results for the entire fish population."""

    frame: int
    timestamp: str
    fish_evaluated: int

    # Population averages
    pop_avg_bb_per_100: float = 0.0
    pop_avg_bb_per_100_ci_95: Tuple[float, float] = (0.0, 0.0)
    pop_weighted_bb_per_100: float = 0.0

    # Per-difficulty tier population averages
    pop_bb_vs_trivial: float = 0.0
    pop_bb_vs_weak: float = 0.0
    pop_bb_vs_moderate: float = 0.0
    pop_bb_vs_strong: float = 0.0

    # Per-baseline population averages
    pop_vs_baseline: Dict[str, float] = field(default_factory=dict)

    # Strategy-type breakdown
    strategy_avg_bb_per_100: Dict[str, float] = field(default_factory=dict)
    strategy_weighted_bb: Dict[str, float] = field(default_factory=dict)
    strategy_count: Dict[str, int] = field(default_factory=dict)

    # Best performers
    best_fish_id: Optional[int] = None
    best_bb_per_100: float = 0.0
    best_weighted_bb: float = 0.0
    best_strategy: str = ""

    # Individual results (for detailed analysis)
    individual_results: List[FishBenchmarkResult] = field(default_factory=list)

    # Total hands across all evaluations
    total_hands: int = 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary suitable for logging/display."""
        return {
            "frame": self.frame,
            "fish_evaluated": self.fish_evaluated,
            "pop_bb_per_100": round(self.pop_avg_bb_per_100, 2),
            "pop_weighted_bb": round(self.pop_weighted_bb_per_100, 2),
            "vs_trivial": round(self.pop_bb_vs_trivial, 2),
            "vs_weak": round(self.pop_bb_vs_weak, 2),
            "vs_moderate": round(self.pop_bb_vs_moderate, 2),
            "vs_strong": round(self.pop_bb_vs_strong, 2),
            "best_fish_id": self.best_fish_id,
            "best_bb": round(self.best_bb_per_100, 2),
            "best_strategy": self.best_strategy,
            "dominant_strategy": max(self.strategy_count.items(), key=lambda x: x[1])[0]
            if self.strategy_count
            else "unknown",
            "total_hands": self.total_hands,
        }


def _evaluate_single_fish(
    fish: "Fish",
    config: ComprehensiveBenchmarkConfig,
    eval_config: BenchmarkEvalConfig,
) -> Optional[FishBenchmarkResult]:
    """Evaluate a single fish against all baselines.

    Args:
        fish: Fish to evaluate
        config: Comprehensive benchmark config
        eval_config: Low-level evaluation config

    Returns:
        FishBenchmarkResult or None if fish has no valid strategy
    """
    # Get fish's poker strategy
    if not hasattr(fish, "genome") or fish.genome is None:
        return None

    strat = fish.genome.poker_strategy_algorithm
    if strat is None:
        return None

    fish_result = FishBenchmarkResult(
        fish_id=fish.id,
        fish_generation=getattr(fish, "generation", 0),
        strategy_id=strat.strategy_id,
        strategy_params=strat.parameters.copy(),
    )

    # Evaluate against each baseline
    for baseline_id in config.fish_vs_baselines.baseline_opponents:
        try:
            baseline_result = evaluate_vs_single_benchmark_duplicate(
                candidate_algo=strat,
                benchmark_id=baseline_id,
                cfg=eval_config,
            )
            fish_result.vs_baselines[baseline_id] = baseline_result
        except Exception as e:
            logger.warning(f"Failed to evaluate fish {fish.id} vs {baseline_id}: {e}")

    fish_result.compute_aggregates()
    return fish_result


def run_comprehensive_benchmark(
    fish_population: List["Fish"],
    config: Optional[ComprehensiveBenchmarkConfig] = None,
    frame: int = 0,
    parallel: bool = True,
    max_workers: int = 4,
) -> PopulationBenchmarkResult:
    """Run comprehensive benchmark suite on fish population.

    This is the main entry point for population-level poker skill evaluation.

    Args:
        fish_population: All fish in the simulation
        config: Benchmark configuration (uses default if None)
        frame: Current simulation frame
        parallel: Whether to run evaluations in parallel
        max_workers: Max parallel workers

    Returns:
        PopulationBenchmarkResult with all metrics
    """
    if config is None:
        config = ComprehensiveBenchmarkConfig()

    # Select fish to evaluate
    def get_poker_winnings(f: "Fish") -> float:
        if hasattr(f, "components") and hasattr(f.components, "poker_stats"):
            ps = f.components.poker_stats
            if ps is not None:
                return getattr(ps, "total_winnings", 0)
        return 0

    sorted_fish = sorted(fish_population, key=get_poker_winnings, reverse=True)

    # Top N by winnings
    top_fish = sorted_fish[: config.top_n_fish]

    # Add random sample from rest of population for diversity
    remaining = sorted_fish[config.top_n_fish :]
    if remaining and config.random_sample_fish > 0:
        sample_size = min(config.random_sample_fish, len(remaining))
        random_sample = rng_module.sample(remaining, sample_size)
        top_fish.extend(random_sample)

    result = PopulationBenchmarkResult(
        frame=frame,
        timestamp=datetime.now().isoformat(),
        fish_evaluated=len(top_fish),
    )

    if not top_fish:
        logger.warning("No fish to evaluate in benchmark")
        return result

    # Create evaluation config from comprehensive config
    eval_config = BenchmarkEvalConfig(
        small_blind=config.small_blind,
        big_blind=config.big_blind,
        starting_stack=config.starting_stack,
        hands_per_match=config.fish_vs_baselines.hands_per_match,
        num_duplicate_sets=config.fish_vs_baselines.num_duplicate_sets,
        benchmark_opponents=config.fish_vs_baselines.baseline_opponents,
    )

    fish_results: List[FishBenchmarkResult] = []

    # Run evaluations
    if parallel and len(top_fish) > 1 and config.parallel_evaluation:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_evaluate_single_fish, f, config, eval_config): f
                for f in top_fish
            }
            for future in as_completed(futures):
                try:
                    fish_result = future.result()
                    if fish_result:
                        fish_results.append(fish_result)
                except Exception as e:
                    fish = futures[future]
                    logger.error(f"Benchmark failed for fish {fish.id}: {e}")
    else:
        for fish in top_fish:
            try:
                fish_result = _evaluate_single_fish(fish, config, eval_config)
                if fish_result:
                    fish_results.append(fish_result)
            except Exception as e:
                logger.error(f"Benchmark failed for fish {fish.id}: {e}")

    # Compute population aggregates
    if fish_results:
        result.individual_results = fish_results

        # Overall population averages
        all_bb = [r.overall_bb_per_100 for r in fish_results]
        all_weighted = [r.weighted_bb_per_100 for r in fish_results]
        result.pop_avg_bb_per_100 = sum(all_bb) / len(all_bb)
        result.pop_weighted_bb_per_100 = sum(all_weighted) / len(all_weighted)

        # Per-tier averages
        result.pop_bb_vs_trivial = sum(
            r.avg_bb_per_100_vs_trivial for r in fish_results
        ) / len(fish_results)
        result.pop_bb_vs_weak = sum(r.avg_bb_per_100_vs_weak for r in fish_results) / len(
            fish_results
        )
        result.pop_bb_vs_moderate = sum(
            r.avg_bb_per_100_vs_moderate for r in fish_results
        ) / len(fish_results)
        result.pop_bb_vs_strong = sum(
            r.avg_bb_per_100_vs_strong for r in fish_results
        ) / len(fish_results)

        # Per-baseline population averages
        for baseline_id in config.fish_vs_baselines.baseline_opponents:
            baseline_bbs = [
                r.vs_baselines[baseline_id].bb_per_100
                for r in fish_results
                if baseline_id in r.vs_baselines
            ]
            if baseline_bbs:
                result.pop_vs_baseline[baseline_id] = sum(baseline_bbs) / len(
                    baseline_bbs
                )

        # Strategy-type breakdown
        strategy_bbs: Dict[str, List[float]] = defaultdict(list)
        strategy_weighted: Dict[str, List[float]] = defaultdict(list)
        for r in fish_results:
            strategy_bbs[r.strategy_id].append(r.overall_bb_per_100)
            strategy_weighted[r.strategy_id].append(r.weighted_bb_per_100)

        for strat_id, bbs in strategy_bbs.items():
            result.strategy_avg_bb_per_100[strat_id] = sum(bbs) / len(bbs)
            result.strategy_count[strat_id] = len(bbs)
        for strat_id, wbbs in strategy_weighted.items():
            result.strategy_weighted_bb[strat_id] = sum(wbbs) / len(wbbs)

        # Best performer (by weighted score)
        best = max(fish_results, key=lambda r: r.weighted_bb_per_100)
        result.best_fish_id = best.fish_id
        result.best_bb_per_100 = best.overall_bb_per_100
        result.best_weighted_bb = best.weighted_bb_per_100
        result.best_strategy = best.strategy_id

        # Total hands
        result.total_hands = sum(r.total_hands for r in fish_results)

    logger.info(
        f"Benchmark complete @ frame {frame}: "
        f"evaluated {len(fish_results)} fish, "
        f"pop_bb/100={result.pop_avg_bb_per_100:.1f}, "
        f"vs_strong={result.pop_bb_vs_strong:.1f}, "
        f"best={result.best_bb_per_100:.1f} ({result.best_strategy})"
    )

    return result


def run_quick_benchmark(
    fish_population: List["Fish"],
    frame: int = 0,
) -> PopulationBenchmarkResult:
    """Run a quick benchmark with reduced sample size.

    Use this for frequent evaluation during simulation.
    """
    from core.poker.evaluation.benchmark_suite import QUICK_BENCHMARK_CONFIG

    return run_comprehensive_benchmark(
        fish_population=fish_population,
        config=QUICK_BENCHMARK_CONFIG,
        frame=frame,
        parallel=True,
        max_workers=2,
    )


def run_full_benchmark(
    fish_population: List["Fish"],
    frame: int = 0,
) -> PopulationBenchmarkResult:
    """Run a full benchmark with high sample size.

    Use this for detailed analysis, e.g., at major milestones.
    """
    from core.poker.evaluation.benchmark_suite import FULL_BENCHMARK_CONFIG

    return run_comprehensive_benchmark(
        fish_population=fish_population,
        config=FULL_BENCHMARK_CONFIG,
        frame=frame,
        parallel=True,
        max_workers=4,
    )
