"""Calibrated heads-up poker benchmark evaluation system.

This module provides duplicate deal head-to-head poker evaluation to assess
fish poker strategies against calibrated benchmark opponents with minimal variance.

## Duplicate Deal Semantics

For each benchmark evaluation:
1. Same rng_seed → same sequence of cards dealt (via Deck's seeded RNG)
2. Two matches per seed: candidate in seat 0, then candidate in seat 1
3. Card luck cancels out; only skill and positional effects remain

## Determinism Guarantees

**What IS deterministic:**
- Card dealing: Same seed → same deck shuffles → same hole cards and board
- Hand evaluation: Same cards → same hand rankings
- Game structure: Blinds, betting rounds, pot calculations

**What is NOT fully deterministic:**
- Strategy decisions: PokerStrategyAlgorithm.decide_action() may use random.random()
  for bluffing, mixed strategies, etc. This is INTENTIONAL - we're measuring the
  expected performance of a mixed strategy, not a single deterministic path.

**Why this is okay:**
- Strategies are static (not learning during evaluation)
- The randomness in decisions is part of the strategy's definition
- Variance from decision randomness is small compared to card variance
- Duplicate deals still eliminate the dominant source of variance (card luck)

## Statistical Properties

With N duplicate sets:
- Each set contributes 2 × hands_per_match samples (one from each seat)
- Total hands = N × hands_per_match × 2
- Variance primarily from strategy decision randomness (not card luck)
- 95% confidence intervals computed via t-distribution
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.poker.strategy.implementations import PokerStrategyAlgorithm


@dataclass
class BenchmarkEvalConfig:
    """Configuration for benchmark evaluation suite."""

    small_blind: int = 50
    big_blind: int = 100
    starting_stack: int = 10_000

    hands_per_match: int = 200  # hands per duplicate set per seat
    num_duplicate_sets: int = 50  # number of seeds
    base_seed: int = 42

    benchmark_opponents: list[str] = field(
        default_factory=lambda: [
            "balanced",
            "tight_aggressive",
            "loose_aggressive",
            "maniac",
        ]
    )

    benchmark_weights: dict[str, float] = field(
        default_factory=lambda: {
            "balanced": 1.0,
            "tight_aggressive": 1.0,
            "loose_aggressive": 1.0,
            "maniac": 0.5,
        }
    )


@dataclass
class SingleBenchmarkResult:
    """Results from evaluation against a single benchmark opponent."""

    benchmark_id: str
    hands_played: int
    bb_per_100: float
    bb_per_100_ci_95: tuple[float, float]
    sample_variance: float
    is_statistically_significant: bool


@dataclass
class BenchmarkSuiteResult:
    """Aggregate results from evaluation against full benchmark suite."""

    total_hands: int
    # per-opponent details
    per_benchmark: dict[str, SingleBenchmarkResult]
    # weighted aggregate
    weighted_bb_per_100: float
    weighted_bb_per_100_ci_95: tuple[float, float]


def _compute_ci_95(values: list[float]) -> tuple[float, float]:
    """Basic t-approximation CI. Good enough for our use;
    if you want bootstrap later, you can swap this out.
    """
    if len(values) < 2:
        mean = values[0] if values else 0.0
        return (mean, mean)

    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    n = len(values)

    t_crit = 1.96  # ~95% for large n
    margin = t_crit * (stdev / math.sqrt(n))
    return (mean - margin, mean + margin)


def create_standard_strategy(strategy_id: str) -> PokerStrategyAlgorithm:
    """Create a standard benchmark strategy by ID.

    Args:
        strategy_id: One of: balanced, tight_aggressive, loose_aggressive,
                     tight_passive, loose_passive, maniac

    Returns:
        PokerStrategyAlgorithm instance
    """
    from core.poker.strategy.implementations import (
        BalancedStrategy,
        LooseAggressiveStrategy,
        LoosePassiveStrategy,
        ManiacStrategy,
        TightAggressiveStrategy,
        TightPassiveStrategy,
    )

    strategy_map = {
        "balanced": BalancedStrategy,
        "tight_aggressive": TightAggressiveStrategy,
        "loose_aggressive": LooseAggressiveStrategy,
        "tight_passive": TightPassiveStrategy,
        "loose_passive": LoosePassiveStrategy,
        "maniac": ManiacStrategy,
    }

    strategy_cls = strategy_map.get(strategy_id)
    if not strategy_cls:
        raise ValueError(
            f"Unknown strategy_id: {strategy_id}. "
            f"Valid options: {list(strategy_map.keys())}"
        )

    return strategy_cls()


def evaluate_vs_single_benchmark_duplicate(
    candidate_algo: PokerStrategyAlgorithm,
    benchmark_id: str,
    cfg: BenchmarkEvalConfig,
) -> SingleBenchmarkResult:
    """Runs HU duplicate matches versus a single benchmark opponent.

    For each duplicate set d:
      - Run a match with RNG seed = base_seed + d, candidate in seat 0
      - Run another match with the SAME seed, candidate in seat 1
    This cancels out card-luck and seat position effects.

    Args:
        candidate_algo: The algorithm to evaluate
        benchmark_id: ID of benchmark opponent (e.g. "balanced")
        cfg: Evaluation configuration

    Returns:
        SingleBenchmarkResult with bb/100 and confidence interval
    """
    benchmark_algo = create_standard_strategy(benchmark_id)

    bb_per_100_samples: list[float] = []
    total_hands = 0
    total_net_bb = 0.0  # big blinds won by candidate

    for dup_idx in range(cfg.num_duplicate_sets):
        seed = cfg.base_seed + dup_idx

        # Seat 0: candidate vs benchmark
        stats_a = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate_algo,
            benchmark_algo=benchmark_algo,
            candidate_seat=0,
            num_hands=cfg.hands_per_match,
            small_blind=cfg.small_blind,
            big_blind=cfg.big_blind,
            starting_stack=cfg.starting_stack,
            rng_seed=seed,
        )

        # Seat 1: benchmark vs candidate (candidate on the right / BB)
        stats_b = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate_algo,
            benchmark_algo=benchmark_algo,
            candidate_seat=1,
            num_hands=cfg.hands_per_match,
            small_blind=cfg.small_blind,
            big_blind=cfg.big_blind,
            starting_stack=cfg.starting_stack,
            rng_seed=seed,
        )

        net_bb_a = stats_a.net_bb_for_candidate
        net_bb_b = stats_b.net_bb_for_candidate

        hands_a = stats_a.hands_played
        hands_b = stats_b.hands_played

        # Sanity: both should equal cfg.hands_per_match, but don't assume
        total_hands_dup = hands_a + hands_b
        net_bb_dup = net_bb_a + net_bb_b

        total_hands += total_hands_dup
        total_net_bb += net_bb_dup

        # bb/100 sample for this duplicate set
        bb_per_100 = (net_bb_dup / total_hands_dup) * 100.0 if total_hands_dup > 0 else 0.0
        bb_per_100_samples.append(bb_per_100)

    if total_hands == 0:
        return SingleBenchmarkResult(
            benchmark_id=benchmark_id,
            hands_played=0,
            bb_per_100=0.0,
            bb_per_100_ci_95=(0.0, 0.0),
            sample_variance=0.0,
            is_statistically_significant=False,
        )

    mean_bb_100 = (total_net_bb / total_hands) * 100.0
    ci_low, ci_high = _compute_ci_95(bb_per_100_samples)
    variance = (
        statistics.pvariance(bb_per_100_samples) if len(bb_per_100_samples) > 1 else 0.0
    )

    # crude "significance" heuristic: CI excludes 0
    significant = (ci_low > 0.0) or (ci_high < 0.0)

    return SingleBenchmarkResult(
        benchmark_id=benchmark_id,
        hands_played=total_hands,
        bb_per_100=mean_bb_100,
        bb_per_100_ci_95=(ci_low, ci_high),
        sample_variance=variance,
        is_statistically_significant=significant,
    )


def evaluate_vs_benchmark_suite(
    candidate_algo: PokerStrategyAlgorithm,
    cfg: BenchmarkEvalConfig,
) -> BenchmarkSuiteResult:
    """Run full benchmark suite evaluation.

    Evaluates candidate against all configured benchmark opponents
    and computes weighted aggregate score.

    Args:
        candidate_algo: The algorithm to evaluate
        cfg: Evaluation configuration

    Returns:
        BenchmarkSuiteResult with per-opponent and aggregate metrics
    """
    per_benchmark: dict[str, SingleBenchmarkResult] = {}
    total_hands = 0

    # First: run per-opponent evals
    for benchmark_id in cfg.benchmark_opponents:
        result = evaluate_vs_single_benchmark_duplicate(candidate_algo, benchmark_id, cfg)
        per_benchmark[benchmark_id] = result
        total_hands += result.hands_played

    # Then: compute weighted aggregate
    weight_sum = 0.0
    weighted_values: list[float] = []
    sample_weights: list[float] = []

    for benchmark_id, result in per_benchmark.items():
        w = cfg.benchmark_weights.get(benchmark_id, 1.0)
        weight_sum += w
        weighted_values.append(result.bb_per_100 * w)
        sample_weights.append(w)

    if weight_sum == 0.0:
        weighted_mean = 0.0
        ci = (0.0, 0.0)
    else:
        weighted_mean = sum(weighted_values) / weight_sum
        # crude weighted CI: treat weights as multiplicities
        expanded_samples: list[float] = []
        for benchmark_id, result in per_benchmark.items():
            w = int(round(cfg.benchmark_weights.get(benchmark_id, 1.0)))
            expanded_samples.extend([result.bb_per_100] * max(w, 1))
        ci = _compute_ci_95(expanded_samples) if expanded_samples else (0.0, 0.0)

    return BenchmarkSuiteResult(
        total_hands=total_hands,
        per_benchmark=per_benchmark,
        weighted_bb_per_100=weighted_mean,
        weighted_bb_per_100_ci_95=ci,
    )
