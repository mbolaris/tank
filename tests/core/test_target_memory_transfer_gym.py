"""Regression tests for the frozen, isolated target-memory transfer benchmark (v1)."""

from __future__ import annotations

import os
import time

import pytest

from benchmarks.tank import target_memory_transfer
from core.behavior.target_memory import TargetMemoryParams
from core.behavior.target_memory_transfer_evolution import (
    TargetMemoryTransferEvaluation,
    evaluate_target_memory_transfer,
)
from core.behavior.target_memory_transfer_gym import (
    evaluate_naive_greedy_on_set,
    evaluate_params_on_set,
    generate_scenario_set,
    run_naive_greedy_episode,
    run_target_memory_episode,
)


@pytest.fixture(scope="session")
def evaluation_42() -> TargetMemoryTransferEvaluation:
    return evaluate_target_memory_transfer(42)


@pytest.fixture(scope="session")
def evaluation_7() -> TargetMemoryTransferEvaluation:
    return evaluate_target_memory_transfer(7)


def test_scenario_set_is_seeded_and_train_test_scenarios_differ():
    """One seed maps to one immutable scenario set; different seeds diverge."""
    train_first = generate_scenario_set("train", 42)
    train_second = generate_scenario_set("train", 42)
    assert [s.scenario_id for s in train_first] == [s.scenario_id for s in train_second]
    assert train_first[0].tracks[0].positions[0] == train_second[0].tracks[0].positions[0]

    train_diff = generate_scenario_set("train", 7)
    assert train_first[0].tracks[0].positions[0] != train_diff[0].tracks[0].positions[0]

    test_ball = generate_scenario_set("held_out", 42)
    assert train_first[0].tracks[0].positions[0] != test_ball[0].tracks[0].positions[0]


def test_food_and_ball_sets_use_distinct_family_names():
    food = generate_scenario_set("train", 42)
    ball = generate_scenario_set("held_out", 42)
    assert {s.family_name for s in food} == {
        "stable_commitment",
        "true_switch_required",
        "occlusion_survival",
    }
    assert {s.family_name for s in ball} == {
        "decelerating",
        "bouncing",
        "swerve",
        "sudden_kick_with_decoy",
    }


def test_episode_evaluation_is_read_only():
    scenarios = generate_scenario_set("held_out", 42)
    scenario = scenarios[0]
    track_snapshot = scenario.tracks[0].positions[0]

    run_target_memory_episode(TargetMemoryParams(), scenario)

    assert scenario.tracks[0].positions[0] == track_snapshot


def test_single_episode_determinism():
    scenarios = generate_scenario_set("held_out", 42)
    scenario = scenarios[0]
    params = TargetMemoryParams()

    res1 = run_target_memory_episode(params, scenario)
    res2 = run_target_memory_episode(params, scenario)
    assert res1.captured_value == res2.captured_value
    assert res1.captures == res2.captures


def test_naive_greedy_has_no_memory_and_still_captures_visible_targets():
    scenarios = generate_scenario_set("train", 42)
    stable = next(s for s in scenarios if s.family_name == "stable_commitment")
    result = run_naive_greedy_episode(stable)
    assert result.captures == 1
    assert result.captured_value > 0.0


@pytest.mark.slow
def test_memory_beats_naive_greedy_on_occlusion_across_seeds():
    """The core mechanism claim: persistence through a brief occlusion gap
    should beat forgetting on every gap-driven frame, for both seeds."""
    for seed in (42, 7):
        ball = generate_scenario_set("held_out", seed)
        default_score = evaluate_params_on_set(TargetMemoryParams(), ball).overall_score
        naive_score = evaluate_naive_greedy_on_set(ball).overall_score
        assert default_score >= naive_score, f"seed={seed}: {default_score} < {naive_score}"


@pytest.mark.slow
def test_comparison_groups_include_the_disjoint_control(evaluation_42, evaluation_7):
    """default_params doubles as the disjoint-arm's zero-shot baseline (a
    target_memory that food selection never touched, per the substrate
    board's design) - the group must exist and the adaptation threshold must
    sit strictly above it."""
    for evaluation in (evaluation_42, evaluation_7):
        assert set(evaluation.group_summaries) == {
            "naive_greedy",
            "default_params",
            "random_search",
            "food_trained",
            "ball_trained",
        }
        assert evaluation.adaptation_threshold > evaluation.default_score


@pytest.mark.slow
def test_benchmark_is_deterministic_and_reports_both_transfer_benefits():
    first = target_memory_transfer.run(42)
    second = target_memory_transfer.run(42)

    assert first["score"] == second["score"]
    assert first["metadata"] == second["metadata"]
    assert first["score"] == first["metadata"]["transfer_benefit_vs_disjoint"]
    assert first["score_breakdown"]["transfer_benefit_vs_disjoint"] == first["score"]
    assert "transfer_benefit_vs_random" in first["metadata"]
    assert first["metadata"]["mutation_schedule"]["mutation_rate"] > 0


@pytest.mark.slow
def test_repeated_runs_runtime_and_memory_stability():
    try:
        import psutil
    except ImportError:
        pytest.skip("psutil not installed, skipping memory stability check.")

    process = psutil.Process(os.getpid())
    evaluate_target_memory_transfer(42)  # warm up caches

    initial_memory = process.memory_info().rss
    runtimes = []
    for _ in range(3):
        t0 = time.perf_counter()
        evaluate_target_memory_transfer(42)
        runtimes.append(time.perf_counter() - t0)

    final_memory = process.memory_info().rss

    for r in runtimes:
        assert r < 40.0, f"Run took too long: {r}s"
    assert runtimes[-1] < runtimes[0] * 1.5, f"Runtimes progressively degrading: {runtimes}"

    memory_diff = final_memory - initial_memory
    assert memory_diff < 20 * 1024 * 1024, f"Memory leaked: {memory_diff / 1024 / 1024:.2f} MB"
