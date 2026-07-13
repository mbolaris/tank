"""Regression tests for the frozen, isolated pursuit-transfer benchmark (v2)."""

from __future__ import annotations

from benchmarks.tank import pursuit_transfer
from core.pursuit.transfer_gym import (
    evaluate_pursuit_transfer,
    generate_scenario_set,
    run_interception_episode,
)


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

    from core.behavior.pursuit_nodes import default_pursuit_module_graph

    run_interception_episode(default_pursuit_module_graph(), scenario)

    assert scenario.target_positions[0] == initial_position
    assert scenario.target_positions[-1] == later_position


def test_evolved_module_beats_the_untrained_default_across_seeds():
    """The core transfer claim: population-based training helps, consistently."""
    for seed in (42, 7):
        evaluation = evaluate_pursuit_transfer(seed)
        assert evaluation.food_trained_score >= evaluation.default_score


def test_comparison_groups_include_a_task_specific_reference():
    """Study v2 reports groups rather than a misleading normalized ladder."""
    for seed in (42, 7):
        evaluation = evaluate_pursuit_transfer(seed)
        assert set(evaluation.group_summaries) == {
            "direct_pursuit",
            "default_module",
            "random_search",
            "food_trained",
            "soccer_trained",
            "constant_velocity_solver",
        }
        assert evaluation.adaptation_threshold > evaluation.default_score


def test_benchmark_is_deterministic_and_reports_transfer_benefit():
    first = pursuit_transfer.run(42)
    second = pursuit_transfer.run(42)

    assert first["score"] == second["score"]
    assert first["metadata"] == second["metadata"]

    assert first["score"] == first["metadata"]["transfer_benefit"]
    assert first["score_breakdown"]["transfer_benefit"] == first["score"]
    assert "skill" not in first["metadata"]
