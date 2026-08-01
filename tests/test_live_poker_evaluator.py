"""Tests for the bounded, isolated live poker skill evaluator."""

from __future__ import annotations

import copy
import random

from core.fish.poker_stats_component import FishPokerStats
from core.genetics import Genome
from core.poker.evaluation.benchmark_eval import BenchmarkEvalConfig, SingleBenchmarkResult
from core.poker.evaluation.periodic_benchmark import PeriodicBenchmarkEvaluator
from core.skill.snapshots import SkillSnapshotStore


class MockFish:
    def __init__(self, fish_id: int, net_energy: float = 0.0) -> None:
        self.fish_id = fish_id
        self.parent_id = fish_id - 1
        self.generation = fish_id
        self.energy = 100.0
        self.poker_stats = FishPokerStats(total_energy_won=net_energy)
        self.genome = Genome.random(use_algorithm=True, rng=random.Random(fish_id))


def _tiny_config() -> BenchmarkEvalConfig:
    return BenchmarkEvalConfig(
        hands_per_match=2,
        num_duplicate_sets=1,
        base_seed=42,
        benchmark_opponents=["random", "loose_passive", "tight_aggressive", "gto_expert"],
    )


def _run_one(fish: MockFish) -> tuple[PeriodicBenchmarkEvaluator, SkillSnapshotStore]:
    store = SkillSnapshotStore()
    evaluator = PeriodicBenchmarkEvaluator(
        cfg=_tiny_config(),
        store=store,
        eval_interval_frames=1,
        max_fish_per_pass=1,
    )
    for frame in range(1, 5):
        evaluator.maybe_run(frame, [fish])
    return evaluator, store


def test_poker_evaluation_is_deterministic_and_records_ladder_snapshot() -> None:
    evaluator1, store1 = _run_one(MockFish(1))
    evaluator2, store2 = _run_one(MockFish(1))

    assert not evaluator1.active
    assert len(store1.get_snapshots(domain="poker")) == 1
    assert store1.get_snapshots(domain="poker")[0].summary.to_dict() == (
        store2.get_snapshots(domain="poker")[0].summary.to_dict()
    )
    assert [r.rung_id for r in store1.get_snapshots(domain="poker")[0].summary.rungs] == [
        "random",
        "loose_passive",
        "tight_aggressive",
        "gto_expert",
    ]


def test_poker_evaluation_preserves_fish_strategy_stats_energy_and_rng() -> None:
    fish = MockFish(2)
    strategy_before = fish.genome.behavioral.poker_strategy.value.to_dict()
    stats_before = copy.deepcopy(fish.poker_stats)
    energy_before = fish.energy
    global_state_before = random.getstate()
    engine_rng = random.Random(991)
    engine_rng_state_before = engine_rng.getstate()

    _run_one(fish)

    assert fish.genome.behavioral.poker_strategy.value.to_dict() == strategy_before
    assert fish.poker_stats == stats_before
    assert fish.energy == energy_before
    assert random.getstate() == global_state_before
    assert engine_rng.getstate() == engine_rng_state_before


def test_poker_history_is_bounded(monkeypatch) -> None:
    import core.poker.evaluation.periodic_benchmark as periodic

    def fake_evaluation(candidate, benchmark_id, cfg):
        return SingleBenchmarkResult(
            benchmark_id=benchmark_id,
            hands_played=cfg.hands_per_match * 2 * cfg.num_duplicate_sets,
            bb_per_100=1.0,
            bb_per_100_ci_95=(0.5, 1.5),
            sample_variance=0.0,
            is_statistically_significant=True,
        )

    monkeypatch.setattr(periodic, "evaluate_vs_single_benchmark_duplicate", fake_evaluation)
    evaluator = PeriodicBenchmarkEvaluator(
        cfg=_tiny_config(), eval_interval_frames=1, max_fish_per_pass=1, history_max=3
    )
    fish = MockFish(3)
    for frame in range(1, 5 * 8 + 1):
        evaluator.maybe_run(frame, [fish])

    assert len(evaluator.get_history()) == 3


def test_subjects_are_ranked_by_net_poker_energy() -> None:
    evaluator = PeriodicBenchmarkEvaluator(cfg=_tiny_config(), max_fish_per_pass=2)
    weak = MockFish(1, net_energy=1.0)
    strong = MockFish(2, net_energy=10.0)
    assert evaluator._top_fish([weak, strong]) == [strong, weak]
