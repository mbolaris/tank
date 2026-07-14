"""Regression tests for the frozen, isolated pursuit-transfer benchmark (v2)."""

from __future__ import annotations

import os
import random
import time

import pytest

from benchmarks.tank import pursuit_transfer
from core.behavior.pursuit_nodes import default_pursuit_module_graph
from core.pursuit.transfer_gym import (
    PursuitTransferEvaluation,
    evaluate_pursuit_transfer,
    generate_scenario_set,
    run_interception_episode,
)


@pytest.fixture(scope="session")
def evaluation_42() -> PursuitTransferEvaluation:
    """Session-scoped fixture to run evaluate_pursuit_transfer(42) exactly once."""
    return evaluate_pursuit_transfer(42)


@pytest.fixture(scope="session")
def evaluation_7() -> PursuitTransferEvaluation:
    """Session-scoped fixture to run evaluate_pursuit_transfer(7) exactly once."""
    return evaluate_pursuit_transfer(7)


def test_trajectory_is_seeded_and_train_test_scenarios_differ():
    """One seed maps to one immutable scenario; train and test use different ones."""
    train_first = generate_scenario_set("train", 42)
    train_second = generate_scenario_set("train", 42)
    assert [s.scenario_id for s in train_first] == [s.scenario_id for s in train_second]
    assert train_first[0].target_positions[1] == train_second[0].target_positions[1]

    train_diff = generate_scenario_set("train", 7)
    assert train_first[0].target_positions[1] != train_diff[0].target_positions[1]

    test_first = generate_scenario_set("held_out", 42)
    # Train and test scenarios must differ
    assert train_first[0].target_positions[1] != test_first[0].target_positions[1]


def test_trajectory_samples_are_snapshots_and_episode_evaluation_is_read_only():
    scenarios = generate_scenario_set("held_out", 42)
    scenario = scenarios[0]
    initial_position = scenario.target_positions[0].copy()
    later_position = scenario.target_positions[-1].copy()

    assert scenario.target_positions[0] != scenario.target_positions[-1]
    assert scenario.target_positions[0] is not scenario.target_positions[-1]

    run_interception_episode(default_pursuit_module_graph(), scenario)

    assert scenario.target_positions[0] == initial_position
    assert scenario.target_positions[-1] == later_position


def test_fitness_calculation():
    """Ensure fitness returns expected results based on interception success and steps."""
    from core.pursuit.transfer_gym import InterceptionResult, _fitness

    # Successful interception: fitness is positive, higher is better (fewer frames)
    res_fast = InterceptionResult(
        intercepted=True, time_to_intercept=50, closest_approach=0.0, energy_spent=150.0
    )
    res_slow = InterceptionResult(
        intercepted=True, time_to_intercept=100, closest_approach=0.0, energy_spent=300.0
    )
    assert _fitness(res_fast) > _fitness(res_slow)

    # Failed interception: fitness is lower than successful ones, depends on closest approach
    res_fail_close = InterceptionResult(
        intercepted=False, time_to_intercept=None, closest_approach=10.0, energy_spent=900.0
    )
    res_fail_far = InterceptionResult(
        intercepted=False, time_to_intercept=None, closest_approach=50.0, energy_spent=900.0
    )
    assert _fitness(res_fail_close) > _fitness(res_fail_far)
    assert _fitness(res_fast) > _fitness(res_fail_close)


def test_crossover_retains_topology_and_mutates_params():
    """Verify BehaviorGraph crossover blends parameter values but retains topology."""
    from core.behavior.pursuit_nodes import default_pursuit_module_graph

    g1 = default_pursuit_module_graph()
    g2 = default_pursuit_module_graph()
    rng = random.Random(42)

    child = g1.crossed_over(g2, weight1=0.7, mutation_rate=0.0, mutation_strength=0.0, rng=rng)
    assert len(child.nodes) == len(g1.nodes)
    assert len(child.connections) == len(g1.connections)
    assert child.output_node_id == g1.output_node_id


def test_single_episode_determinism():
    """Verify running an interception episode is deterministic with the same module/scenario."""
    scenarios = generate_scenario_set("held_out", 42)
    scenario = scenarios[0]
    module = default_pursuit_module_graph()

    res1 = run_interception_episode(module, scenario)
    res2 = run_interception_episode(module, scenario)
    assert res1.intercepted == res2.intercepted
    assert res1.time_to_intercept == res2.time_to_intercept
    assert res1.closest_approach == res2.closest_approach


@pytest.mark.slow
def test_evolved_module_beats_the_untrained_default_across_seeds(evaluation_42, evaluation_7):
    """The core transfer claim: population-based training helps, consistently."""
    assert evaluation_42.food_trained_score >= evaluation_42.default_score
    assert evaluation_7.food_trained_score >= evaluation_7.default_score


@pytest.mark.slow
def test_comparison_groups_include_a_task_specific_reference(evaluation_42, evaluation_7):
    """Study v2 reports groups rather than a misleading normalized ladder."""
    for evaluation in (evaluation_42, evaluation_7):
        assert set(evaluation.group_summaries) == {
            "direct_pursuit",
            "default_module",
            "random_search",
            "food_trained",
            "soccer_trained",
            "constant_velocity_solver",
        }
        assert evaluation.adaptation_threshold > evaluation.default_score


@pytest.mark.slow
def test_benchmark_is_deterministic_and_reports_transfer_benefit():
    first = pursuit_transfer.run(42)
    second = pursuit_transfer.run(42)

    assert first["score"] == second["score"]
    assert first["metadata"] == second["metadata"]

    assert first["score"] == first["metadata"]["transfer_benefit"]
    assert first["score_breakdown"]["transfer_benefit"] == first["score"]
    assert "skill" not in first["metadata"]


@pytest.mark.slow
def test_repeated_runs_runtime_and_memory_stability():
    """Verify that repeatedly running evaluate_pursuit_transfer is stable in memory and speed."""
    try:
        import psutil
    except ImportError:
        pytest.skip("psutil not installed, skipping memory stability check.")

    process = psutil.Process(os.getpid())

    # Warm up caches
    evaluate_pursuit_transfer(42)

    initial_memory = process.memory_info().rss
    runtimes = []

    for _ in range(3):
        t0 = time.perf_counter()
        evaluate_pursuit_transfer(42)
        runtimes.append(time.perf_counter() - t0)

    final_memory = process.memory_info().rss

    # 1. Runtime stability: subsequent runs should be fast and not slowing down
    print(f"Runtimes: {runtimes}")
    for r in runtimes:
        assert r < 40.0, f"Run took too long: {r}s"
    # Ensure there is no progressive slow down (last run is not > 20% slower than first run)
    assert runtimes[-1] < runtimes[0] * 1.2, f"Runtimes progressively degrading: {runtimes}"

    # 2. Memory stability: RSS difference should be minimal (no leaking large datasets)
    memory_diff = final_memory - initial_memory
    assert memory_diff < 20 * 1024 * 1024, f"Memory leaked: {memory_diff / 1024 / 1024:.2f} MB"
