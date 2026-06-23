from __future__ import annotations

import json
import math
from types import SimpleNamespace

from core.poker.evaluation import comprehensive_benchmark
from core.poker.evaluation.benchmark_suite import ComprehensiveBenchmarkConfig
from core.poker.evaluation.comprehensive_benchmark import FishBenchmarkResult
from core.poker.evaluation.evolution_benchmark_tracker import EvolutionBenchmarkTracker


class _StubFish:
    poker_stats = None


def test_population_benchmark_populates_bb100_uncertainty(monkeypatch):
    fish_results = [
        FishBenchmarkResult(
            fish_id=1,
            fish_generation=0,
            strategy_id="a",
            strategy_params={},
            overall_bb_per_100=10.0,
            weighted_bb_per_100=5.0,
        ),
        FishBenchmarkResult(
            fish_id=2,
            fish_generation=0,
            strategy_id="b",
            strategy_params={},
            overall_bb_per_100=20.0,
            weighted_bb_per_100=15.0,
        ),
        FishBenchmarkResult(
            fish_id=3,
            fish_generation=0,
            strategy_id="c",
            strategy_params={},
            overall_bb_per_100=30.0,
            weighted_bb_per_100=25.0,
        ),
    ]

    def fake_evaluate(fish, config, eval_config):
        return fish_results.pop(0)

    monkeypatch.setattr(comprehensive_benchmark, "_evaluate_single_fish", fake_evaluate)

    result = comprehensive_benchmark.run_comprehensive_benchmark(
        fish_population=[_StubFish(), _StubFish(), _StubFish()],
        config=ComprehensiveBenchmarkConfig(),
        parallel=False,
        frame=100,
    )

    assert result.pop_avg_bb_per_100 == 20.0
    assert result.pop_avg_bb_per_100_ci_95[0] < result.pop_avg_bb_per_100
    assert result.pop_avg_bb_per_100_ci_95[1] > result.pop_avg_bb_per_100

    assert result.pop_weighted_bb_per_100 == 15.0


def test_tracker_persists_uncertainty_fields(monkeypatch, tmp_path):
    def fake_quick_benchmark(fish_population, frame):
        return SimpleNamespace(
            frame=frame,
            timestamp="2026-06-23T00:00:00",
            pop_avg_bb_per_100=12.345,
            pop_avg_bb_per_100_ci_95=(7.0, 18.0),
            pop_weighted_bb_per_100=15.678,
            pop_bb_vs_trivial=0.0,
            pop_bb_vs_weak=0.0,
            pop_bb_vs_moderate=0.0,
            pop_bb_vs_strong=0.0,
            pop_bb_vs_expert=0.0,
            pop_mean_elo=1234.0,
            pop_median_elo=1230.0,
            elo_tier_distribution={},
            pop_confidence_vs_weak=0.5,
            pop_confidence_vs_moderate=0.5,
            pop_confidence_vs_strong=0.5,
            pop_confidence_vs_expert=0.5,
            strategy_count={"tight_aggressive": 1},
            best_fish_id=1,
            best_bb_per_100=20.0,
            best_elo=1300.0,
            best_strategy="tight_aggressive",
            pop_vs_baseline={},
            fish_evaluated=1,
            total_hands=100,
            individual_results=[
                FishBenchmarkResult(
                    fish_id=1,
                    fish_generation=2,
                    strategy_id="tight_aggressive",
                    strategy_params={},
                    overall_bb_per_100=10.0,
                    weighted_bb_per_100=12.0,
                ),
                FishBenchmarkResult(
                    fish_id=2,
                    fish_generation=2,
                    strategy_id="tight_aggressive",
                    strategy_params={},
                    overall_bb_per_100=20.0,
                    weighted_bb_per_100=24.0,
                ),
            ],
        )

    monkeypatch.setattr(comprehensive_benchmark, "run_quick_benchmark", fake_quick_benchmark)

    export_path = tmp_path / "poker_evolution.json"
    tracker = EvolutionBenchmarkTracker(export_path=export_path)
    snapshot = tracker.run_and_record(
        [SimpleNamespace(generation=2)], current_frame=100, force=True
    )

    assert snapshot is not None
    assert snapshot.pop_bb_per_100_ci_95[0] < 15.0
    assert snapshot.pop_bb_per_100_ci_95[1] > 15.0
    assert math.isclose(snapshot.pop_bb_per_100_se, 5.0)
    assert snapshot.pop_weighted_bb_ci_95[0] < 18.0
    assert snapshot.pop_weighted_bb_ci_95[1] > 18.0
    assert math.isclose(snapshot.pop_weighted_bb_se, 6.0)

    api_data = tracker.get_api_data()
    assert api_data["latest"]["pop_bb_per_100_ci_95"] == [5.2, 24.8]
    assert api_data["latest"]["pop_bb_per_100_se"] == 5.0
    assert api_data["latest"]["pop_weighted_bb_ci_95"] == [6.24, 29.76]
    assert api_data["latest"]["pop_weighted_bb_se"] == 6.0
    assert api_data["history"][0]["pop_bb_per_100_ci_95"] == [5.2, 24.8]

    exported = json.loads(export_path.read_text())
    assert exported["snapshots"][0]["pop_bb_per_100_ci_95"] == [5.2, 24.8]
    assert exported["snapshots"][0]["pop_weighted_bb_ci_95"] == [6.24, 29.76]
