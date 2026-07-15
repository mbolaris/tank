"""Regression tests for the frozen, isolated target-memory transfer benchmark (v1)."""

from __future__ import annotations

import math
import os
import time

import pytest

from benchmarks.tank import target_memory_transfer
from core.behavior.target_memory import TargetId, TargetMemoryParams
from core.behavior.target_memory_transfer_evolution import (
    TargetMemoryTransferEvaluation,
    evaluate_target_memory_transfer,
)
from core.behavior.target_memory_transfer_gym import (
    MAX_FRAMES,
    MIN_REFERENCE_EFFECT,
    CandidateTrack,
    TargetMemoryScenario,
    evaluate_naive_greedy_on_set,
    evaluate_params_on_set,
    generate_scenario_set,
    run_naive_greedy_episode,
    run_target_memory_episode,
)
from core.math_utils import Vector2


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
        "drifting_food",
        "decelerating_drift",
        "occluded_turn",
        "competing_drifters",
    }
    assert {s.family_name for s in ball} == {
        "decelerating",
        "bouncing",
        "swerve",
        "sudden_kick_with_decoy",
    }


def test_moving_food_families_actually_move_and_stay_catchable():
    """The v2 families exist to put selection pressure on
    motion_extrapolation_duration, which stationary food cannot do - so their
    primary tracks must genuinely move, but slower than the pursuer or the
    scenario tests steering, not commitment."""
    from core.behavior.target_memory_transfer_gym import PURSUER_SPEED

    food = generate_scenario_set("train", 42)
    moving = {"drifting_food", "decelerating_drift", "occluded_turn", "competing_drifters"}
    for scenario in food:
        primary = scenario.tracks[0]
        speeds = [math.hypot(v.x, v.y) for v in primary.velocities]
        if scenario.family_name in moving:
            assert max(speeds) > 0.0, scenario.family_name
            assert max(speeds) < PURSUER_SPEED, scenario.family_name
        else:
            assert max(speeds) == 0.0, scenario.family_name


def test_occluded_turn_reappears_off_the_linear_extrapolation():
    """The direction change is hidden inside the occlusion window, so a pure
    linear extrapolation from the last-seen state must NOT predict the true
    reappearance position - that divergence is the capability under test."""
    for seed in (42, 7, 0):
        food = generate_scenario_set("train", seed)
        scenario = next(s for s in food if s.family_name == "occluded_turn")
        track = scenario.tracks[0]
        mask = track.visible_mask
        gap_start = mask.index(False)
        gap_end = gap_start
        while gap_end < len(mask) and not mask[gap_end]:
            gap_end += 1
        assert gap_end < len(mask), "occlusion must end within the episode"

        last_seen_pos = track.positions[gap_start - 1]
        last_seen_vel = track.velocities[gap_start - 1]
        gap_frames = gap_end - (gap_start - 1)
        predicted = last_seen_pos + last_seen_vel * gap_frames
        actual = track.positions[gap_end]
        divergence = math.hypot(actual.x - predicted.x, actual.y - predicted.y)
        assert divergence > 5.0, f"seed={seed}: reappearance too close to linear prediction"


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


def _synthetic_occlusion_scenario() -> TargetMemoryScenario:
    """Single stationary target that vanishes for frames 10-60: long enough
    that memory-driven (stale) pursuit must happen, short enough that default
    memory_duration (90) never gives up."""
    length = MAX_FRAMES + 1
    visible = [True] * length
    for i in range(10, 61):
        visible[i] = False
    track = CandidateTrack(
        target_id=TargetId("food", 0),
        value=50.0,
        start_frame=0,
        positions=tuple(Vector2(100.0, 0.0) for _ in range(length)),
        velocities=tuple(Vector2(0.0, 0.0) for _ in range(length)),
        visible_mask=tuple(visible),
    )
    return TargetMemoryScenario(
        scenario_id="synthetic_occlusion",
        family_name="synthetic",
        observer_start=Vector2(0.0, 0.0),
        tracks=(track,),
        max_frames=MAX_FRAMES,
    )


def test_diagnostic_metrics_separate_memory_from_greedy_behavior():
    """The diagnostic fields must reflect the mechanism, not just the score:
    memory pursues through the gap (stale frames, a reacquisition event),
    naive greedy structurally cannot pursue an invisible target."""
    scenario = _synthetic_occlusion_scenario()

    memory_result = run_target_memory_episode(TargetMemoryParams(), scenario)
    assert memory_result.stale_pursuit_frames > 0
    assert memory_result.switches == 0
    assert memory_result.reacquisition_events == 1
    assert memory_result.captures == 1
    assert memory_result.distance_traveled > 0.0

    greedy_result = run_naive_greedy_episode(scenario)
    assert greedy_result.stale_pursuit_frames == 0
    assert greedy_result.captures == 1


def test_summary_carries_diagnostic_metrics():
    scenarios = generate_scenario_set("held_out", 42)
    summary = evaluate_params_on_set(TargetMemoryParams(), scenarios)
    payload = summary.to_dict()
    for key in (
        "mean_switches",
        "mean_stale_pursuit_frames",
        "mean_reacquisition_frames",
        "mean_distance_traveled",
    ):
        assert key in payload
        assert payload[key] >= 0.0
    assert payload["mean_distance_traveled"] > 0.0
    # Diagnostics must never leak into the score.
    assert summary.overall_score == summary.capture_ratio


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
    board's design) - the group must exist for every seed regardless of
    whether an adaptation reference was established."""
    for evaluation in (evaluation_42, evaluation_7):
        assert set(evaluation.group_summaries) == {
            "naive_greedy",
            "default_params",
            "neutral_evolution",
            "food_trained",
            "ball_trained",
        }


@pytest.mark.slow
def test_adaptation_fields_are_null_unless_reference_established(evaluation_42, evaluation_7):
    """ball_trained must clear MIN_REFERENCE_EFFECT over default on the
    ball-validation set (never on the training or held-out sets) before
    generations-to-adapt is reported; otherwise every adaptation field must be
    None rather than a threshold manufactured from a near-zero or negative
    gap."""
    for evaluation in (evaluation_42, evaluation_7):
        if evaluation.adaptation_reference_established:
            assert evaluation.adaptation_reference_gap >= MIN_REFERENCE_EFFECT
            assert evaluation.adaptation_threshold is not None
            assert evaluation.adaptation_generations_food is not None
            assert evaluation.adaptation_generations_default is not None
            assert evaluation.adaptation_generations_food >= 0
            assert evaluation.adaptation_generations_default >= 0
        else:
            assert evaluation.adaptation_reference_gap < MIN_REFERENCE_EFFECT
            assert evaluation.adaptation_threshold is None
            assert evaluation.adaptation_generations_food is None
            assert evaluation.adaptation_generations_default is None

    # Locks in the current v1.1 behavior so a regression that silently
    # re-widens or re-narrows MIN_REFERENCE_EFFECT, reintroduces held-out
    # leakage, or moves the reference back onto the training set is caught
    # rather than passing unnoticed. Under v1.1 (reference measured on
    # ball-validation instead of ball-training) NO tested seed establishes a
    # reference at the current tiny budget: seed 42's v1 "established"
    # reference was a training-fit artifact - its ball-trained params score
    # a full -0.08 BELOW default on unseen ball scenarios. Growing the study
    # (v2 multi-run budgets) is the sanctioned way to flip these, not
    # loosening the measurement.
    assert evaluation_42.adaptation_reference_established is False
    assert evaluation_42.adaptation_reference_gap < 0
    assert evaluation_7.adaptation_reference_established is False


@pytest.mark.slow
def test_benchmark_is_deterministic_and_reports_both_transfer_benefits():
    first = target_memory_transfer.run(42)
    second = target_memory_transfer.run(42)

    assert first["score"] == second["score"]
    assert first["metadata"] == second["metadata"]
    assert first["score"] == first["metadata"]["transfer_benefit_vs_disjoint"]
    assert first["score_breakdown"]["transfer_benefit_vs_disjoint"] == first["score"]
    assert "transfer_benefit_vs_neutral" in first["metadata"]
    assert first["metadata"]["mutation_schedule"]["mutation_rate"] > 0

    # The validity block is the machine-readable contract for what this run's
    # numbers support; adaptation fields must never be read without it.
    validity = first["metadata"]["validity"]
    from core.behavior.target_memory_transfer_scenarios import SCENARIO_SET_VERSION

    assert validity["adaptation_reference_measured_on"] == f"ball_validation_{SCENARIO_SET_VERSION}"
    assert validity["held_out_used_only_for_zero_shot_scoring"] is True
    assert validity["min_reference_effect"] == MIN_REFERENCE_EFFECT
    assert (
        validity["adaptation_fields_meaningful"]
        == first["metadata"]["adaptation"]["reference_established"]
    )
    assert validity["known_limitations"]


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
