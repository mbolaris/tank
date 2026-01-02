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
import random as pyrandom
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    SingleBenchmarkResult,
    evaluate_vs_single_benchmark_duplicate,
)
from core.poker.evaluation.benchmark_suite import (
    BASELINE_OPPONENTS,
    ComprehensiveBenchmarkConfig,
)
from core.poker.evaluation.elo_rating import (
    EloRating,
    PopulationEloStats,
    compute_elo_from_benchmarks,
    compute_population_elo_stats,
    rating_to_skill_tier,
)

if TYPE_CHECKING:
    from core.entities import Fish

logger = logging.getLogger(__name__)


@dataclass
class FishBenchmarkResult:
    """Complete benchmark results for a single fish."""

    fish_id: int
    fish_generation: int
    strategy_id: str
    strategy_params: dict[str, float]

    # Per-baseline results
    vs_baselines: dict[str, SingleBenchmarkResult] = field(default_factory=dict)

    # Aggregate scores by difficulty tier
    avg_bb_per_100_vs_trivial: float = 0.0  # vs always_fold, random
    avg_bb_per_100_vs_weak: float = 0.0  # vs calling station, rock
    avg_bb_per_100_vs_moderate: float = 0.0  # vs TAG, LAG
    avg_bb_per_100_vs_strong: float = 0.0  # vs balanced, maniac
    avg_bb_per_100_vs_expert: float = 0.0  # vs gto_expert
    overall_bb_per_100: float = 0.0
    weighted_bb_per_100: float = 0.0  # Weighted by baseline difficulty

    # Elo rating (more stable than raw bb/100)
    elo_rating: EloRating | None = None
    elo_skill_tier: str = "unknown"

    # Confidence-based assessments
    confidence_vs_weak: float = 0.0  # Probability of beating weak opponents
    confidence_vs_moderate: float = 0.0  # Probability of beating moderate opponents
    confidence_vs_strong: float = 0.0  # Probability of beating strong opponents
    confidence_vs_expert: float = 0.0  # Probability of beating expert opponents

    # Fish-vs-fish results (if available)
    bb_per_100_vs_fish: float | None = None

    # Total hands played across all benchmarks
    total_hands: int = 0

    def compute_aggregates(self) -> None:
        """Compute aggregate scores from per-baseline results."""
        # Map strategy IDs to difficulty tiers
        trivial_ids = ["always_fold", "random"]
        weak_ids = ["loose_passive", "tight_passive"]
        moderate_ids = ["tight_aggressive", "loose_aggressive"]
        strong_ids = ["balanced", "maniac"]
        expert_ids = ["gto_expert"]

        def avg_bb(baseline_ids: list[str]) -> tuple[float, int]:
            """Get average bb/100 and total hands for a set of baselines."""
            results = [self.vs_baselines[bid] for bid in baseline_ids if bid in self.vs_baselines]
            if not results:
                return 0.0, 0
            total_bb = sum(r.bb_per_100 for r in results)
            total_hands = sum(r.hands_played for r in results)
            return total_bb / len(results), total_hands

        self.avg_bb_per_100_vs_trivial, hands_trivial = avg_bb(trivial_ids)
        self.avg_bb_per_100_vs_weak, hands_weak = avg_bb(weak_ids)
        self.avg_bb_per_100_vs_moderate, hands_moderate = avg_bb(moderate_ids)
        self.avg_bb_per_100_vs_strong, hands_strong = avg_bb(strong_ids)
        self.avg_bb_per_100_vs_expert, hands_expert = avg_bb(expert_ids)

        self.total_hands = hands_trivial + hands_weak + hands_moderate + hands_strong + hands_expert

        # Overall unweighted average
        all_results = list(self.vs_baselines.values())
        if all_results:
            self.overall_bb_per_100 = sum(r.bb_per_100 for r in all_results) / len(all_results)

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

        # Compute Elo rating from benchmark results
        benchmark_results = {bid: r.bb_per_100 for bid, r in self.vs_baselines.items()}
        hands_per_benchmark = {bid: r.hands_played for bid, r in self.vs_baselines.items()}
        self.elo_rating = compute_elo_from_benchmarks(benchmark_results, hands_per_benchmark)
        self.elo_skill_tier = rating_to_skill_tier(self.elo_rating.rating)

        # Compute confidence-based assessments using CI
        self.confidence_vs_weak = self._compute_win_confidence(weak_ids)
        self.confidence_vs_moderate = self._compute_win_confidence(moderate_ids)
        self.confidence_vs_strong = self._compute_win_confidence(strong_ids)
        self.confidence_vs_expert = self._compute_win_confidence(expert_ids)

    def _compute_win_confidence(self, baseline_ids: list[str]) -> float:
        """Compute probability of winning against a tier based on CI.

        Uses the confidence interval to estimate probability that true skill
        is positive (winning) against this tier.
        """
        results = [self.vs_baselines[bid] for bid in baseline_ids if bid in self.vs_baselines]
        if not results:
            return 0.5  # No data = uncertain

        # Average bb/100 and CI width
        avg_bb = sum(r.bb_per_100 for r in results) / len(results)
        avg_ci_width = sum(
            (r.bb_per_100_ci_95[1] - r.bb_per_100_ci_95[0]) / 2 for r in results
        ) / len(results)

        if avg_ci_width <= 0:
            return 1.0 if avg_bb > 0 else 0.0

        # Approximate probability that true skill > 0
        # Using normal approximation: P(X > 0) = Φ(avg / std)
        import math

        z = avg_bb / max(avg_ci_width / 1.96, 0.1)  # CI/1.96 ≈ std
        # Sigmoid approximation of normal CDF
        confidence = 1.0 / (1.0 + math.exp(-z * 0.7))
        return round(confidence, 3)

    def skill_rating(self) -> str:
        """Categorize skill level based on Elo rating (more stable than raw bb/100)."""
        if self.elo_rating is not None:
            return self.elo_skill_tier
        # Fallback to bb/100-based rating
        if self.avg_bb_per_100_vs_trivial < 10:
            return "failing"
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
    pop_avg_bb_per_100_ci_95: tuple[float, float] = (0.0, 0.0)
    pop_weighted_bb_per_100: float = 0.0

    # Per-difficulty tier population averages
    pop_bb_vs_trivial: float = 0.0
    pop_bb_vs_weak: float = 0.0
    pop_bb_vs_moderate: float = 0.0
    pop_bb_vs_strong: float = 0.0
    pop_bb_vs_expert: float = 0.0

    # Per-baseline population averages
    pop_vs_baseline: dict[str, float] = field(default_factory=dict)

    # Elo rating statistics (more stable than raw bb/100)
    pop_elo_stats: PopulationEloStats | None = None
    pop_mean_elo: float = 1200.0
    pop_median_elo: float = 1200.0
    elo_tier_distribution: dict[str, int] = field(default_factory=dict)

    # Confidence-based skill assessments (population average)
    pop_confidence_vs_weak: float = 0.5
    pop_confidence_vs_moderate: float = 0.5
    pop_confidence_vs_strong: float = 0.5
    pop_confidence_vs_expert: float = 0.5

    # Strategy-type breakdown
    strategy_avg_bb_per_100: dict[str, float] = field(default_factory=dict)
    strategy_weighted_bb: dict[str, float] = field(default_factory=dict)
    strategy_count: dict[str, int] = field(default_factory=dict)

    # Best performers
    best_fish_id: int | None = None
    best_bb_per_100: float = 0.0
    best_weighted_bb: float = 0.0
    best_elo: float = 1200.0
    best_strategy: str = ""

    # Individual results (for detailed analysis)
    individual_results: list[FishBenchmarkResult] = field(default_factory=list)

    # Total hands across all evaluations
    total_hands: int = 0

    def get_summary(self) -> dict[str, Any]:
        """Get a summary suitable for logging/display."""
        return {
            "frame": self.frame,
            "fish_evaluated": self.fish_evaluated,
            "pop_bb_per_100": round(self.pop_avg_bb_per_100, 2),
            "pop_weighted_bb": round(self.pop_weighted_bb_per_100, 2),
            "pop_mean_elo": round(self.pop_mean_elo, 1),
            "pop_median_elo": round(self.pop_median_elo, 1),
            "vs_trivial": round(self.pop_bb_vs_trivial, 2),
            "vs_weak": round(self.pop_bb_vs_weak, 2),
            "vs_moderate": round(self.pop_bb_vs_moderate, 2),
            "vs_strong": round(self.pop_bb_vs_strong, 2),
            "vs_expert": round(self.pop_bb_vs_expert, 2),
            "conf_vs_weak": round(self.pop_confidence_vs_weak, 2),
            "conf_vs_moderate": round(self.pop_confidence_vs_moderate, 2),
            "conf_vs_strong": round(self.pop_confidence_vs_strong, 2),
            "conf_vs_expert": round(self.pop_confidence_vs_expert, 2),
            "best_fish_id": self.best_fish_id,
            "best_bb": round(self.best_bb_per_100, 2),
            "best_elo": round(self.best_elo, 1),
            "best_strategy": self.best_strategy,
            "elo_tier_distribution": self.elo_tier_distribution,
            "dominant_strategy": (
                max(self.strategy_count.items(), key=lambda x: x[1])[0]
                if self.strategy_count
                else "unknown"
            ),
            "total_hands": self.total_hands,
        }


def _evaluate_single_fish(
    fish: Fish,
    config: ComprehensiveBenchmarkConfig,
    eval_config: BenchmarkEvalConfig,
) -> FishBenchmarkResult | None:
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

    trait = fish.genome.behavioral.poker_strategy
    strat = trait.value if trait else None
    if strat is None:
        return None

    fish_result = FishBenchmarkResult(
        fish_id=fish.fish_id,
        fish_generation=getattr(fish, "generation", 0),
        strategy_id=strat.strategy_id,
        strategy_params=strat.parameters.copy(),
    )

    # Evaluate against each baseline
    for baseline_id in config.fish_vs_baselines.baseline_opponents:
        try:
            from core.auto_evaluate_poker import is_shutdown_requested

            if is_shutdown_requested():
                break
        except Exception:
            pass
        try:
            baseline_result = evaluate_vs_single_benchmark_duplicate(
                candidate_algo=strat,
                benchmark_id=baseline_id,
                cfg=eval_config,
            )
            fish_result.vs_baselines[baseline_id] = baseline_result
        except Exception as e:
            logger.warning(f"Failed to evaluate fish {fish.fish_id} vs {baseline_id}: {e}")

    fish_result.compute_aggregates()
    return fish_result


def run_comprehensive_benchmark(
    fish_population: list[Fish],
    config: ComprehensiveBenchmarkConfig | None = None,
    frame: int = 0,
    parallel: bool = True,
    max_workers: int = 4,
    rng: pyrandom.Random | None = None,
) -> PopulationBenchmarkResult:
    """Run comprehensive benchmark suite on fish population.

    This is the main entry point for population-level poker skill evaluation.

    Args:
        fish_population: All fish in the simulation
        config: Benchmark configuration (uses default if None)
        frame: Current simulation frame
        parallel: Whether to run evaluations in parallel
        max_workers: Max parallel workers
        rng: Random number generator for deterministic sampling

    Returns:
        PopulationBenchmarkResult with all metrics
    """
    # Fast exit during shutdown (Ctrl+C) to avoid keeping non-daemon worker
    # threads alive and delaying process termination.
    try:
        from core.auto_evaluate_poker import is_shutdown_requested

        if is_shutdown_requested():
            return PopulationBenchmarkResult(
                frame=frame,
                timestamp=datetime.now().isoformat(),
                fish_evaluated=0,
            )
    except Exception:
        pass

    if config is None:
        config = ComprehensiveBenchmarkConfig()

    # Select fish to evaluate using stratified sampling for better representation
    def get_poker_winnings(f: Fish) -> float:
        if hasattr(f, "components") and hasattr(f.components, "poker_stats"):
            ps = f.components.poker_stats
            if ps is not None:
                return getattr(ps, "total_winnings", 0)
        return 0

    sorted_fish = sorted(fish_population, key=get_poker_winnings, reverse=True)
    total_fish = len(sorted_fish)
    rng = rng if rng is not None else pyrandom.Random()

    # Stratified sampling: divide population into tiers and sample from each
    # This ensures we get a representative view of the entire population
    # instead of just top performers
    selected_fish: list[Fish] = []

    if total_fish <= config.top_n_fish + config.random_sample_fish:
        # Small population - evaluate all
        selected_fish = sorted_fish
    else:
        total_to_select = config.top_n_fish + config.random_sample_fish

        # Stratified selection:
        # - 40% from top tier (by winnings)
        # - 30% from middle tier
        # - 20% from bottom tier
        # - 10% random from any tier
        top_count = max(1, int(total_to_select * 0.4))
        mid_count = max(1, int(total_to_select * 0.3))
        bottom_count = max(1, int(total_to_select * 0.2))
        random_count = total_to_select - top_count - mid_count - bottom_count

        # Divide population into thirds
        tier_size = total_fish // 3
        top_tier = sorted_fish[:tier_size]
        mid_tier = sorted_fish[tier_size : 2 * tier_size]
        bottom_tier = sorted_fish[2 * tier_size :]

        # Sample from each tier
        if len(top_tier) >= top_count:
            selected_fish.extend(top_tier[:top_count])
        else:
            selected_fish.extend(top_tier)

        if len(mid_tier) >= mid_count:
            mid_sample = rng.sample(mid_tier, mid_count)
            selected_fish.extend(mid_sample)
        elif mid_tier:
            selected_fish.extend(mid_tier)

        if len(bottom_tier) >= bottom_count:
            bottom_sample = rng.sample(bottom_tier, bottom_count)
            selected_fish.extend(bottom_sample)
        elif bottom_tier:
            selected_fish.extend(bottom_tier)

        # Add random samples from any fish not yet selected
        remaining = [f for f in sorted_fish if f not in selected_fish]
        if remaining and random_count > 0:
            random_sample = rng.sample(remaining, min(random_count, len(remaining)))
            selected_fish.extend(random_sample)

    top_fish = selected_fish

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

    fish_results: list[FishBenchmarkResult] = []

    # Run evaluations
    if parallel and len(top_fish) > 1 and config.parallel_evaluation:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_evaluate_single_fish, f, config, eval_config): f for f in top_fish
            }
            for future in as_completed(futures):
                try:
                    fish_result = future.result()
                    if fish_result:
                        fish_results.append(fish_result)
                except Exception as e:
                    fish = futures[future]
                    logger.error(f"Benchmark failed for fish {fish.fish_id}: {e}")
    else:
        for fish in top_fish:
            try:
                fish_result = _evaluate_single_fish(fish, config, eval_config)
                if fish_result:
                    fish_results.append(fish_result)
            except Exception as e:
                logger.error(f"Benchmark failed for fish {fish.fish_id}: {e}")

    # Compute population aggregates
    if fish_results:
        result.individual_results = fish_results

        # Overall population averages
        all_bb = [r.overall_bb_per_100 for r in fish_results]
        all_weighted = [r.weighted_bb_per_100 for r in fish_results]
        result.pop_avg_bb_per_100 = sum(all_bb) / len(all_bb)
        result.pop_weighted_bb_per_100 = sum(all_weighted) / len(all_weighted)

        # Per-tier averages
        result.pop_bb_vs_trivial = sum(r.avg_bb_per_100_vs_trivial for r in fish_results) / len(
            fish_results
        )
        result.pop_bb_vs_weak = sum(r.avg_bb_per_100_vs_weak for r in fish_results) / len(
            fish_results
        )
        result.pop_bb_vs_moderate = sum(r.avg_bb_per_100_vs_moderate for r in fish_results) / len(
            fish_results
        )
        result.pop_bb_vs_strong = sum(r.avg_bb_per_100_vs_strong for r in fish_results) / len(
            fish_results
        )
        result.pop_bb_vs_expert = sum(r.avg_bb_per_100_vs_expert for r in fish_results) / len(
            fish_results
        )

        # Per-baseline population averages
        for baseline_id in config.fish_vs_baselines.baseline_opponents:
            baseline_bbs = [
                r.vs_baselines[baseline_id].bb_per_100
                for r in fish_results
                if baseline_id in r.vs_baselines
            ]
            if baseline_bbs:
                result.pop_vs_baseline[baseline_id] = sum(baseline_bbs) / len(baseline_bbs)

        # Strategy-type breakdown
        strategy_bbs: dict[str, list[float]] = defaultdict(list)
        strategy_weighted: dict[str, list[float]] = defaultdict(list)
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
        result.best_elo = best.elo_rating.rating if best.elo_rating else 1200.0

        # Total hands
        result.total_hands = sum(r.total_hands for r in fish_results)

        # Compute population Elo stats (more stable than raw bb/100)
        fish_elo_ratings = {
            r.fish_id: r.elo_rating for r in fish_results if r.elo_rating is not None
        }
        if fish_elo_ratings:
            result.pop_elo_stats = compute_population_elo_stats(fish_elo_ratings)
            result.pop_mean_elo = result.pop_elo_stats.mean_rating
            result.pop_median_elo = result.pop_elo_stats.median_rating
            result.elo_tier_distribution = result.pop_elo_stats.tier_distribution

        # Compute population-level confidence metrics
        all_conf_weak = [r.confidence_vs_weak for r in fish_results]
        all_conf_moderate = [r.confidence_vs_moderate for r in fish_results]
        all_conf_strong = [r.confidence_vs_strong for r in fish_results]
        all_conf_expert = [r.confidence_vs_expert for r in fish_results]
        result.pop_confidence_vs_weak = sum(all_conf_weak) / len(all_conf_weak)
        result.pop_confidence_vs_moderate = sum(all_conf_moderate) / len(all_conf_moderate)
        result.pop_confidence_vs_strong = sum(all_conf_strong) / len(all_conf_strong)
        result.pop_confidence_vs_expert = sum(all_conf_expert) / len(all_conf_expert)

    logger.info(
        f"Benchmark complete @ frame {frame}: "
        f"evaluated {len(fish_results)} fish, "
        f"pop_bb/100={result.pop_avg_bb_per_100:.1f}, "
        f"pop_elo={result.pop_mean_elo:.0f}, "
        f"vs_expert_bb={result.pop_bb_vs_expert:.1f}, "
        f"conf_expert={result.pop_confidence_vs_expert:.0%}, "
        f"best={result.best_bb_per_100:.1f} ({result.best_strategy})"
    )

    return result


def run_quick_benchmark(
    fish_population: list[Fish],
    frame: int = 0,
    rng: pyrandom.Random | None = None,
) -> PopulationBenchmarkResult:
    """Run a quick benchmark with reduced sample size.

    Use this for frequent evaluation during simulation.
    """
    from core.poker.evaluation.benchmark_suite import QUICK_BENCHMARK_CONFIG

    return run_comprehensive_benchmark(
        fish_population=fish_population,
        config=QUICK_BENCHMARK_CONFIG,
        frame=frame,
        parallel=False,
        max_workers=1,
        rng=rng,
    )


def run_full_benchmark(
    fish_population: list[Fish],
    frame: int = 0,
    rng: pyrandom.Random | None = None,
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
        rng=rng,
    )
