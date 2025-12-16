"""
Poker hand strength evaluation and decision support.

This package provides tools for evaluating hand strength, calculating pot odds,
recommending actions based on poker theory, and comprehensive benchmarking for
measuring poker skill evolution.
"""

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    BenchmarkSuiteResult,
    SingleBenchmarkResult,
    create_standard_strategy,
    evaluate_vs_benchmark_suite,
    evaluate_vs_single_benchmark_duplicate,
)
from core.poker.evaluation.benchmark_suite import (
    BASELINE_OPPONENTS,
    BaselineDifficulty,
    BaselineOpponent,
    BenchmarkCategory,
    ComprehensiveBenchmarkConfig,
    SubTournamentConfig,
)
from core.poker.evaluation.comprehensive_benchmark import (
    FishBenchmarkResult,
    PopulationBenchmarkResult,
    run_comprehensive_benchmark,
    run_full_benchmark,
    run_quick_benchmark,
)
from core.poker.evaluation.evolution_benchmark_tracker import (
    BenchmarkSnapshot,
    EvolutionBenchmarkHistory,
    EvolutionBenchmarkTracker,
    get_global_benchmark_tracker,
    reset_global_tracker,
)
from core.poker.evaluation.hand_evaluator import (
    evaluate_hand,
    evaluate_hand_cached,
)
from core.poker.evaluation.strength import (
    calculate_pot_odds,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)

__all__ = [
    # Hand evaluation
    "calculate_pot_odds",
    "evaluate_hand",
    "evaluate_hand_cached",
    "evaluate_starting_hand_strength",
    "get_action_recommendation",
    # Benchmark evaluation
    "BenchmarkEvalConfig",
    "BenchmarkSuiteResult",
    "SingleBenchmarkResult",
    "create_standard_strategy",
    "evaluate_vs_benchmark_suite",
    "evaluate_vs_single_benchmark_duplicate",
    # Benchmark suite
    "BASELINE_OPPONENTS",
    "BaselineDifficulty",
    "BaselineOpponent",
    "BenchmarkCategory",
    "ComprehensiveBenchmarkConfig",
    "SubTournamentConfig",
    # Comprehensive benchmark
    "FishBenchmarkResult",
    "PopulationBenchmarkResult",
    "run_comprehensive_benchmark",
    "run_full_benchmark",
    "run_quick_benchmark",
    # Evolution tracker
    "BenchmarkSnapshot",
    "EvolutionBenchmarkHistory",
    "EvolutionBenchmarkTracker",
    "get_global_benchmark_tracker",
    "reset_global_tracker",
]
