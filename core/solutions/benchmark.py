"""Benchmark system for evaluating and comparing solutions.

This module provides comprehensive evaluation of solutions against
standard benchmark opponents and head-to-head comparisons between
user-submitted solutions.
"""

from __future__ import annotations

import hashlib
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from core.poker.evaluation.benchmark_eval import BenchmarkEvalConfig, evaluate_vs_benchmark_suite
from core.poker.evaluation.elo_rating import compute_elo_from_benchmarks, rating_to_skill_tier
from core.solutions.models import BenchmarkResult, SolutionComparison, SolutionRecord

logger = logging.getLogger(__name__)


# Standard benchmark opponents for solution evaluation
SOLUTION_BENCHMARK_OPPONENTS = [
    "always_fold",
    "random",
    "loose_passive",
    "tight_passive",
    "tight_aggressive",
    "loose_aggressive",
    "balanced",
    "maniac",
]


@dataclass
class SolutionBenchmarkConfig:
    """Configuration for solution benchmarking."""

    # Benchmark settings
    hands_per_opponent: int = 500
    num_duplicate_sets: int = 25
    base_seed: int = 42

    # Poker game settings
    small_blind: int = 50
    big_blind: int = 100
    starting_stack: int = 10_000

    # Which opponents to include
    opponents: list[str] = field(default_factory=lambda: SOLUTION_BENCHMARK_OPPONENTS.copy())

    # Parallel execution
    max_workers: int = 4


class SolutionBenchmark:
    """Evaluates and compares solutions using standardized benchmarks.

    This class provides:
    1. Evaluation of individual solutions against benchmark opponents
    2. Head-to-head comparison between solutions
    3. Comprehensive tournament-style evaluation of all solutions
    4. Elo rating computation and skill tier classification
    """

    def __init__(self, config: SolutionBenchmarkConfig | None = None):
        """Initialize the benchmark system.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or SolutionBenchmarkConfig()

    def evaluate_solution(
        self,
        solution: SolutionRecord,
        verbose: bool = False,
    ) -> BenchmarkResult:
        """Evaluate a single solution against all benchmark opponents.

        Args:
            solution: The solution to evaluate
            verbose: Whether to print progress

        Returns:
            BenchmarkResult with performance metrics
        """
        # Create strategy from solution
        strategy = self._create_strategy_from_solution(solution)
        if strategy is None:
            logger.warning(
                f"Could not create strategy for solution {solution.metadata.solution_id}"
            )
            return BenchmarkResult(evaluated_at=datetime.utcnow().isoformat())

        # Create evaluation config
        eval_config = BenchmarkEvalConfig(
            small_blind=self.config.small_blind,
            big_blind=self.config.big_blind,
            starting_stack=self.config.starting_stack,
            hands_per_match=self.config.hands_per_opponent,
            num_duplicate_sets=self.config.num_duplicate_sets,
            base_seed=self.config.base_seed,
            benchmark_opponents=self.config.opponents,
        )

        # Run evaluation
        if verbose:
            logger.info(f"Evaluating solution {solution.metadata.solution_id}...")

        suite_result = evaluate_vs_benchmark_suite(strategy, eval_config)

        # Convert to BenchmarkResult
        per_opponent = {}
        confidence_intervals = {}

        for opp_id, result in suite_result.per_benchmark.items():
            per_opponent[opp_id] = result.bb_per_100
            confidence_intervals[opp_id] = result.bb_per_100_ci_95

        # Compute Elo rating
        hands_per_benchmark = {
            opp_id: result.hands_played for opp_id, result in suite_result.per_benchmark.items()
        }
        elo = compute_elo_from_benchmarks(per_opponent, hands_per_benchmark)

        benchmark_result = BenchmarkResult(
            per_opponent=per_opponent,
            weighted_bb_per_100=suite_result.weighted_bb_per_100,
            total_hands_played=suite_result.total_hands,
            elo_rating=elo.rating,
            confidence_intervals=confidence_intervals,
            skill_tier=rating_to_skill_tier(elo.rating),
            evaluated_at=datetime.utcnow().isoformat(),
        )

        return benchmark_result

    def evaluate_all_solutions(
        self,
        solutions: list[SolutionRecord],
        parallel: bool = True,
        verbose: bool = False,
    ) -> dict[str, BenchmarkResult]:
        """Evaluate all solutions and update their benchmark results.

        Args:
            solutions: List of solutions to evaluate
            parallel: Whether to evaluate in parallel
            verbose: Whether to print progress

        Returns:
            Dict mapping solution_id to BenchmarkResult
        """
        results = {}

        if parallel and len(solutions) > 1:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {
                    executor.submit(self.evaluate_solution, sol, verbose): sol for sol in solutions
                }

                for future in as_completed(futures):
                    solution = futures[future]
                    try:
                        result = future.result()
                        results[solution.metadata.solution_id] = result
                        solution.benchmark_result = result
                        if verbose:
                            logger.info(
                                f"Completed: {solution.metadata.name} - "
                                f"Elo: {result.elo_rating:.0f}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to evaluate {solution.metadata.solution_id}: {e}")
        else:
            for solution in solutions:
                try:
                    result = self.evaluate_solution(solution, verbose)
                    results[solution.metadata.solution_id] = result
                    solution.benchmark_result = result
                except Exception as e:
                    logger.error(f"Failed to evaluate {solution.metadata.solution_id}: {e}")

        return results

    def compare_solutions(
        self,
        solutions: list[SolutionRecord],
        hands_per_matchup: int = 500,
        verbose: bool = False,
    ) -> SolutionComparison:
        """Compare solutions head-to-head against each other.

        Args:
            solutions: Solutions to compare
            hands_per_matchup: Hands per head-to-head matchup
            verbose: Whether to print progress

        Returns:
            SolutionComparison with rankings and head-to-head results
        """
        if len(solutions) < 2:
            return SolutionComparison(
                solution_ids=[s.metadata.solution_id for s in solutions],
                compared_at=datetime.utcnow().isoformat(),
            )

        # Ensure all solutions have been benchmarked
        for solution in solutions:
            if solution.benchmark_result is None:
                solution.benchmark_result = self.evaluate_solution(solution, verbose)

        # Build head-to-head matrix
        solution_ids = [s.metadata.solution_id for s in solutions]
        head_to_head: dict[str, dict[str, float]] = {sid: {} for sid in solution_ids}

        for i, sol1 in enumerate(solutions):
            for j, sol2 in enumerate(solutions):
                if i >= j:
                    continue

                # Run head-to-head
                win_rate_1, win_rate_2 = self._run_head_to_head(
                    sol1, sol2, hands_per_matchup, verbose
                )

                head_to_head[sol1.metadata.solution_id][sol2.metadata.solution_id] = win_rate_1
                head_to_head[sol2.metadata.solution_id][sol1.metadata.solution_id] = win_rate_2

        # Compute rankings based on aggregate Elo
        solution_scores = []
        for solution in solutions:
            score = solution.benchmark_result.elo_rating if solution.benchmark_result else 1200
            solution_scores.append((solution.metadata.solution_id, score))

        solution_scores.sort(key=lambda x: x[1], reverse=True)
        rankings = {sid: rank + 1 for rank, (sid, _) in enumerate(solution_scores)}

        # Find statistically significant differences
        significant_differences = []
        for i, sol1 in enumerate(solutions):
            for j, sol2 in enumerate(solutions):
                if i >= j:
                    continue

                if sol1.benchmark_result and sol2.benchmark_result:
                    diff = (
                        sol1.benchmark_result.weighted_bb_per_100
                        - sol2.benchmark_result.weighted_bb_per_100
                    )
                    # Rough significance check: difference > 5 bb/100
                    if abs(diff) > 5.0:
                        significant_differences.append(
                            (
                                sol1.metadata.solution_id,
                                sol2.metadata.solution_id,
                                diff,
                            )
                        )

        return SolutionComparison(
            solution_ids=solution_ids,
            rankings=rankings,
            head_to_head=head_to_head,
            significant_differences=significant_differences,
            compared_at=datetime.utcnow().isoformat(),
        )

    def run_head_to_head(
        self,
        sol1: SolutionRecord,
        sol2: SolutionRecord,
        num_hands: int,
        verbose: bool = False,
    ) -> tuple[float, float]:
        """Run a deterministic head-to-head match between two solutions."""
        return self._run_head_to_head(sol1, sol2, num_hands, verbose)

    def _create_strategy_from_solution(self, solution: SolutionRecord):
        """Create a poker strategy from a solution record.

        Returns a PokerStrategyAlgorithm that can be used in benchmarks.
        """
        from core.poker.strategy.implementations import BalancedStrategy, PokerStrategyAlgorithm

        # Create a deterministic RNG based on solution ID (avoid Python's salted hash()).
        seed_material = f"strategy|{solution.metadata.solution_id}".encode()
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little")
        rng = random.Random(seed)

        # If the solution has poker strategy config, use it
        poker_config = solution.poker_strategy
        if poker_config:
            # Newer format: full strategy dict.
            try:
                if poker_config.get("type") == "ComposablePokerStrategy":
                    from core.poker.strategy.composable import ComposablePokerStrategy

                    return ComposablePokerStrategy.from_dict(poker_config)

                # Legacy/monolithic implementations identified by strategy_id + parameters.
                if "strategy_id" in poker_config:
                    strategy = PokerStrategyAlgorithm.from_dict(poker_config)
                    if hasattr(strategy, "_rng"):
                        strategy._rng = rng
                    return strategy
            except Exception:
                pass

            # Oldest format: class name only.
            if poker_config.get("class"):
                try:
                    from core.poker.strategy import implementations as impl

                    strategy_class = getattr(impl, poker_config["class"], None)
                    if strategy_class and issubclass(strategy_class, PokerStrategyAlgorithm):
                        return strategy_class(rng=rng)
                except Exception:
                    pass

        # If we have behavior algorithm, try to create a strategy from its parameters
        behavior = solution.behavior_algorithm
        if behavior:
            # Use balanced strategy with adjusted parameters based on behavior
            strategy = BalancedStrategy(rng=rng)

            # Adjust strategy based on captured behavior parameters
            params = behavior.get("parameters", {})
            if "aggression" in params:
                # Could adjust strategy aggression here
                pass

            return strategy

        # Fallback to balanced strategy
        return BalancedStrategy(rng=rng)

    def _run_head_to_head(
        self,
        sol1: SolutionRecord,
        sol2: SolutionRecord,
        num_hands: int,
        verbose: bool = False,
    ) -> tuple[float, float]:
        """Run a head-to-head match between two solutions.

        Returns (win_rate_1, win_rate_2) tuple.
        """
        from core.auto_evaluate_poker import AutoEvaluatePokerGame

        if sol1.metadata.solution_id == sol2.metadata.solution_id:
            return (0.5, 0.5)

        strategy1 = self._create_strategy_from_solution(sol1)
        strategy2 = self._create_strategy_from_solution(sol2)

        if strategy1 is None or strategy2 is None:
            return (0.5, 0.5)

        # Run matches with position rotation.
        #
        # Important: seed must be invariant to solution list ordering so that
        # the same pair produces the same match (boards/deals) regardless of
        # where the solutions appear in a tournament bracket.
        a_id, b_id = sorted([sol1.metadata.solution_id, sol2.metadata.solution_id])
        seed_material = f"{a_id}|{b_id}".encode()
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little")

        hands_total = num_hands - (num_hands % 4)
        if hands_total >= 4:
            hands_orientation = hands_total // 2
            hands_seat = hands_orientation // 2
        else:
            hands_total = num_hands - (num_hands % 2)
            if hands_total < 2:
                return (0.5, 0.5)
            hands_seat = hands_total // 2

        # Position 1: sol1 as player 0
        stats1 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=strategy1,
            benchmark_algo=strategy2,
            candidate_seat=0,
            num_hands=hands_seat,
            small_blind=self.config.small_blind,
            big_blind=self.config.big_blind,
            starting_stack=self.config.starting_stack,
            rng_seed=seed,
        )

        # Position 2: sol1 as player 1
        stats2 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=strategy1,
            benchmark_algo=strategy2,
            candidate_seat=1,
            num_hands=hands_seat,
            small_blind=self.config.small_blind,
            big_blind=self.config.big_blind,
            starting_stack=self.config.starting_stack,
            rng_seed=seed + 1,
        )

        if hands_total >= 4:
            # Reverse roles (sol2 as candidate) using the same deals/seed so the
            # matchup is invariant to solution ordering.
            stats3 = AutoEvaluatePokerGame.run_heads_up(
                candidate_algo=strategy2,
                benchmark_algo=strategy1,
                candidate_seat=0,
                num_hands=hands_seat,
                small_blind=self.config.small_blind,
                big_blind=self.config.big_blind,
                starting_stack=self.config.starting_stack,
                rng_seed=seed,
            )

            stats4 = AutoEvaluatePokerGame.run_heads_up(
                candidate_algo=strategy2,
                benchmark_algo=strategy1,
                candidate_seat=1,
                num_hands=hands_seat,
                small_blind=self.config.small_blind,
                big_blind=self.config.big_blind,
                starting_stack=self.config.starting_stack,
                rng_seed=seed + 1,
            )

            total_hands = (
                stats1.hands_played
                + stats2.hands_played
                + stats3.hands_played
                + stats4.hands_played
            )
            net_bb_sol1_candidate = (stats1.net_bb_for_candidate or 0.0) + (
                stats2.net_bb_for_candidate or 0.0
            )
            net_bb_sol2_candidate = (stats3.net_bb_for_candidate or 0.0) + (
                stats4.net_bb_for_candidate or 0.0
            )
            total_net_bb_sol1 = net_bb_sol1_candidate - net_bb_sol2_candidate
        else:
            total_hands = stats1.hands_played + stats2.hands_played
            total_net_bb_sol1 = (stats1.net_bb_for_candidate or 0.0) + (
                stats2.net_bb_for_candidate or 0.0
            )

        if total_hands == 0:
            return (0.5, 0.5)

        # Convert bb/hand to win rate approximation
        bb_per_hand = total_net_bb_sol1 / total_hands
        # Rough conversion: +1 bb/hand ≈ 60% win rate
        win_rate_1 = 0.5 + bb_per_hand * 0.1
        win_rate_1 = max(0.0, min(1.0, win_rate_1))
        return (win_rate_1, 1.0 - win_rate_1)

    def generate_report(
        self,
        solutions: list[SolutionRecord],
        output_path: str | None = None,
    ) -> str:
        """Generate a comprehensive benchmark report.

        Args:
            solutions: Solutions to include in report
            output_path: Optional file path to save report

        Returns:
            Report as a string
        """
        lines = [
            "=" * 60,
            "TankWorld Solution Benchmark Report",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Solutions Evaluated: {len(solutions)}",
            "=" * 60,
            "",
        ]

        # Sort by Elo
        sorted_solutions = sorted(
            solutions,
            key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0,
            reverse=True,
        )

        lines.append("RANKINGS")
        lines.append("-" * 60)

        for rank, solution in enumerate(sorted_solutions, 1):
            result = solution.benchmark_result
            if result:
                lines.append(
                    f"#{rank:<2}  {solution.metadata.name:<30} "
                    f"Elo: {result.elo_rating:>6.0f}  "
                    f"Tier: {result.skill_tier:<12} "
                    f"bb/100: {result.weighted_bb_per_100:>+7.2f}"
                )
            else:
                lines.append(f"#{rank:<2}  {solution.metadata.name:<30} [Not Evaluated]")

        lines.append("")
        lines.append("DETAILED RESULTS")
        lines.append("-" * 60)

        for solution in sorted_solutions:
            lines.append(f"\n{solution.metadata.name}")
            lines.append(f"  ID: {solution.metadata.solution_id}")
            lines.append(f"  Author: {solution.metadata.author}")

            result = solution.benchmark_result
            if result:
                lines.append(f"  Elo Rating: {result.elo_rating:.0f}")
                lines.append(f"  Skill Tier: {result.skill_tier}")
                lines.append(f"  Total Hands: {result.total_hands_played:,}")
                lines.append("")
                lines.append("  Performance vs Opponents:")

                for opp, bb_per_100 in sorted(result.per_opponent.items()):
                    ci = result.confidence_intervals.get(opp, (0, 0))
                    lines.append(
                        f"    {opp:<20} {bb_per_100:>+8.2f} bb/100  "
                        f"[{ci[0]:+.2f}, {ci[1]:+.2f}]"
                    )

        lines.append("")
        lines.append("=" * 60)

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w") as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")

        return report
