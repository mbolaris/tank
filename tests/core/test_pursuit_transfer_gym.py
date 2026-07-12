"""Regression tests for the frozen, isolated pursuit-transfer benchmark."""

from __future__ import annotations

from benchmarks.tank import pursuit_transfer
from core.pursuit.transfer_gym import _target_trajectory, evaluate_pursuit_transfer


def test_trajectory_is_seeded_and_train_test_scenarios_differ():
    """One seed maps to one immutable scenario; train and test use different ones."""
    first = _target_trajectory(42, speed_scale=1.2)
    assert first == _target_trajectory(42, speed_scale=1.2)
    assert first != _target_trajectory(7, speed_scale=1.2)
    # Training (seed) and zero-shot test (seed+1, different speed_scale) must differ.
    assert first != _target_trajectory(43, speed_scale=1.8)


def test_evolved_module_beats_the_untrained_default_across_seeds():
    """The core transfer claim: mutate-and-select training helps, consistently."""
    for seed in (42, 7, 123, 999):
        evaluation = evaluate_pursuit_transfer(seed)
        assert evaluation.evolved_score >= evaluation.untrained_score


def test_ceiling_is_never_worse_than_the_untrained_default():
    """A per-episode-tuned reference must not be embarrassingly miscalibrated."""
    for seed in (42, 7, 123, 999):
        evaluation = evaluate_pursuit_transfer(seed)
        assert evaluation.ceiling_score >= evaluation.untrained_score


def test_benchmark_is_deterministic_and_emits_frozen_ruler_metadata():
    first = pursuit_transfer.run(42)
    second = pursuit_transfer.run(42)

    assert first["score"] == second["score"]
    assert first["metadata"] == second["metadata"]

    skill = first["metadata"]["skill"]
    assert skill["domain"] == "pursuit"
    assert [rung["rung_id"] for rung in skill["rungs"]] == [
        "no_prediction_direct_chase_v1",
        "untrained_default_module_v1",
        "generous_prediction_v1",
    ]
    # The transfer claim, expressed as a benchmark rung: evolved beats untrained.
    assert next(r for r in skill["rungs"] if r["rung_id"] == "untrained_default_module_v1")[
        "beaten"
    ]
