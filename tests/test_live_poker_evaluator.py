"""Tests for the bounded, isolated live poker skill evaluator."""

from __future__ import annotations

import copy
import random
from dataclasses import replace

import core.poker.evaluation.auto_evaluate_poker as auto_poker
from core.fish.poker_stats_component import FishPokerStats
from core.genetics import Genome
from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    SingleBenchmarkResult,
    evaluate_vs_single_benchmark_duplicate,
    iter_vs_single_benchmark_duplicate,
)
from core.poker.evaluation.periodic_benchmark import (
    POKER_LADDER_RUNGS,
    PeriodicBenchmarkEvaluator,
    _clone_strategy,
)
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
    # 4 rungs x 1 duplicate set x 2 seats: one heads-up match per frame.
    for frame in range(1, 9):
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

    def fake_evaluation(candidate, benchmark_id, cfg, *, yield_between_hands=True):
        return SingleBenchmarkResult(
            benchmark_id=benchmark_id,
            hands_played=cfg.hands_per_match * 2 * cfg.num_duplicate_sets,
            bb_per_100=1.0,
            bb_per_100_ci_95=(0.5, 1.5),
            sample_variance=0.0,
            is_statistically_significant=True,
        )

    def fake_steps(candidate, benchmark_id, cfg, *, yield_between_hands=True):
        return fake_evaluation(candidate, benchmark_id, cfg)
        yield  # makes this a generator that finishes on its first step

    monkeypatch.setattr(periodic, "iter_vs_single_benchmark_duplicate", fake_steps)
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


# ---------------------------------------------------------------------------
# Frame budget. The evaluator runs inside the simulation frame: on a Windows
# server a restored world sat at 0.1 FPS (4-13 s per frame) for minutes while
# it played a whole 500-hand rung per frame with a 1 ms sleep after each hand.
# ---------------------------------------------------------------------------


def _count_matches(monkeypatch) -> list[int]:
    """Record how many heads-up matches each ``maybe_run`` call plays."""
    calls: list[int] = [0]
    original = auto_poker.AutoEvaluatePokerGame.run_heads_up

    def counting(*args, **kwargs):
        calls[-1] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(auto_poker.AutoEvaluatePokerGame, "run_heads_up", staticmethod(counting))
    return calls


def test_each_frame_plays_at_most_one_heads_up_match(monkeypatch) -> None:
    calls = _count_matches(monkeypatch)
    cfg = replace(_tiny_config(), num_duplicate_sets=3)
    evaluator = PeriodicBenchmarkEvaluator(cfg=cfg, eval_interval_frames=1, max_fish_per_pass=1)
    fish = MockFish(4)

    frame = 0
    while True:
        frame += 1
        evaluator.maybe_run(frame, [fish])
        if not evaluator.active:
            break
        calls.append(0)

    assert max(calls) == 1
    # 4 rungs x 3 duplicate sets x 2 seats, with no idle frame between rungs.
    assert frame == len(POKER_LADDER_RUNGS) * 3 * 2
    assert sum(calls) == frame


def test_live_evaluation_never_sleeps_on_the_simulation_thread(monkeypatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(auto_poker.time, "sleep", slept.append)
    evaluator, store = _run_one(MockFish(5))
    assert len(store.get_snapshots(domain="poker")) == 1
    assert slept == []


def test_background_heads_up_still_yields_the_gil_by_default(monkeypatch) -> None:
    # The EvolutionBenchmarkTracker runs off-thread and relies on this.
    slept: list[float] = []
    monkeypatch.setattr(auto_poker.time, "sleep", slept.append)
    fish = MockFish(6)
    evaluate_vs_single_benchmark_duplicate(
        _clone_strategy(fish.genome.behavioral.poker_strategy.value, 1), "random", _tiny_config()
    )
    assert len(slept) == 2 * 2  # 2 seats x 2 hands


def test_stepped_evaluation_matches_the_one_shot_result() -> None:
    fish = MockFish(7)
    cfg = replace(_tiny_config(), hands_per_match=5, num_duplicate_sets=3)

    def strategy():
        return _clone_strategy(fish.genome.behavioral.poker_strategy.value, 99)

    random.seed(3)
    one_shot = evaluate_vs_single_benchmark_duplicate(strategy(), "tight_aggressive", cfg)

    random.seed(3)
    steps = iter_vs_single_benchmark_duplicate(
        strategy(), "tight_aggressive", cfg, yield_between_hands=False
    )
    n_steps = 0
    while True:
        n_steps += 1
        try:
            next(steps)
        except StopIteration as done:
            stepped = done.value
            break

    assert n_steps == 3 * 2, "N matches take exactly N steps"
    assert stepped == one_shot
