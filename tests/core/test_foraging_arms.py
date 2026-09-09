"""Regression tests for the foraging-gym controller ablation arms (backlog 12.4)."""

import math

import pytest

from core.foraging import arms
from core.foraging.gym import evaluate_foraging_gym
from core.math_utils import Vector2
from core.movement.kinematics import (
    ALGORITHMIC_MAX_SPEED_MULTIPLIER,
    ALGORITHMIC_MOVEMENT_SMOOTHING,
    MAX_ACTION_VELOCITY,
    apply_movement_kinematics,
)

# Gross energy the neutral composable ruler collects on these seeds. Recorded
# before the gym's fish/environment grew the surface the arbiter-driven arms
# need; the point of pinning them is that growing that surface must not move
# the frozen ruler this benchmark's published scores rest on.
FROZEN_COMPOSABLE_ENERGY = {42: 748.0, 7: 820.0, 123: 766.0}


def test_frozen_composable_ruler_is_untouched_by_the_arm_surface():
    for seed, energy in FROZEN_COMPOSABLE_ENERGY.items():
        evaluation = evaluate_foraging_gym(seed)
        assert evaluation.composable.energy_collected == energy


class _StuckRng:
    """A random.Random stand-in that records whether the nudge branch fired."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value
        self.draws = 0

    def random(self) -> float:
        self.draws += 1
        return self.value


def test_kinematics_scale_the_desired_direction_by_speed():
    """A unit-magnitude controller and a larger one both reach top speed.

    This is what makes a normalized behavior graph comparable with the
    composable behavior at all, so it is pinned rather than assumed.
    """
    rng = _StuckRng()
    unit = apply_movement_kinematics(Vector2(2.0, 0.0), (1.0, 0.0), 2.0, rng)
    bigger = apply_movement_kinematics(Vector2(2.0, 0.0), (1.5, 0.0), 2.0, rng)
    assert math.isclose(unit.length(), 2.0)
    assert math.isclose(bigger.length(), 2.0 * ALGORITHMIC_MAX_SPEED_MULTIPLIER)
    assert rng.draws == 0


def test_kinematics_smooth_toward_the_target_rather_than_snapping():
    rng = _StuckRng()
    velocity = apply_movement_kinematics(Vector2(0.0, 1.0), (0.0, 1.0), 2.0, rng)
    expected = 1.0 + (2.0 - 1.0) * ALGORITHMIC_MOVEMENT_SMOOTHING
    assert math.isclose(velocity.y, expected)


def test_kinematics_clamp_the_action_bound_before_scaling():
    rng = _StuckRng()
    huge = apply_movement_kinematics(Vector2(0.0, 0.0), (1e9, 0.0), 1.0, rng)
    bound = apply_movement_kinematics(Vector2(0.0, 0.0), (MAX_ACTION_VELOCITY, 0.0), 1.0, rng)
    assert huge.x == bound.x


def test_kinematics_only_consume_rng_when_the_fish_is_stopped():
    moving = _StuckRng()
    apply_movement_kinematics(Vector2(1.0, 0.0), (1.0, 0.0), 2.0, moving)
    assert moving.draws == 0

    stopped = _StuckRng()
    nudged = apply_movement_kinematics(Vector2(0.0, 0.0), (0.0, 0.0), 2.0, stopped)
    assert stopped.draws == 1
    assert nudged.length() > 0.0


def test_arms_are_deterministic():
    config = arms.gym_config(graph=True, pursuit_module=True)
    genome = arms.make_founder_genome(1, config)
    for arm in arms.ARM_NAMES:
        first = arms.evaluate_arm(arm, genome, 42, config)
        second = arms.evaluate_arm(arm, genome, 42, config)
        assert first.result == second.result


def test_flag_off_arbiter_scores_exactly_the_bare_composable_controller():
    """With the graph flag off, no other drive fires, so the arms must agree.

    This is the comparison's own control: if these two ever diverge, the
    ``production`` baseline has stopped being "the composable behavior driving"
    and the flag-flip delta would be measuring something else.
    """
    config = arms.gym_config(graph=False, pursuit_module=True)
    for genome_seed in (1, 2, 3):
        genome = arms.make_founder_genome(genome_seed, config)
        for seed in (42, 7):
            bare = arms.evaluate_arm(arms.COMPOSABLE, genome, seed, config)
            production = arms.evaluate_arm(arms.PRODUCTION, genome, seed, config)
            assert bare.result == production.result


def test_graph_arm_needs_its_urgency_threshold_raised_in_a_single_fish_gym():
    """The bare graph's default score is about gym geometry, not steering.

    Above its urgency threshold the default foraging graph steers toward
    social cohesion, and a one-fish gym has no school, so it emits nothing.
    Pinning the graph on its food branch is what turns the bare arm into a
    statement about foraging - callers that skip that get the low number.
    """
    config = arms.gym_config(graph=True, pursuit_module=True)
    genome = arms.make_founder_genome(1, config)
    default = arms.evaluate_arm(arms.GRAPH, genome, 42, config)
    food_branch = arms.evaluate_arm(arms.GRAPH, genome, 42, config, urgency_threshold=1.0)
    assert food_branch.energy_ratio > default.energy_ratio


def test_urgency_override_leaves_the_genome_graph_untouched():
    config = arms.gym_config(graph=True, pursuit_module=True)
    genome = arms.make_founder_genome(1, config)
    before = genome.behavioral.behavior_graph.value.to_dict()
    arms.evaluate_arm(arms.GRAPH, genome, 42, config, urgency_threshold=1.0)
    assert genome.behavioral.behavior_graph.value.to_dict() == before


def test_unknown_arm_is_rejected():
    config = arms.gym_config(graph=False, pursuit_module=True)
    genome = arms.make_founder_genome(1, config)
    with pytest.raises(ValueError, match="Unknown foraging-gym arm"):
        arms.evaluate_arm("no_such_arm", genome, 42, config)


def test_comparison_reports_a_mean_per_arm():
    comparison = arms.compare_arms((1,), (42, 7), arms=(arms.COMPOSABLE, arms.PRODUCTION))
    assert comparison.arms() == (arms.COMPOSABLE, arms.PRODUCTION)
    assert len(comparison.scores) == 4
    for arm in comparison.arms():
        assert 0.0 <= comparison.mean_ratio(arm) <= 1.0
    assert comparison.mean_ratio("absent_arm") == 0.0


def test_founder_genome_installs_exactly_what_the_flags_opt_into():
    off = arms.make_founder_genome(1, arms.gym_config(graph=False, pursuit_module=False))
    assert off.behavioral.behavior_graph is None
    assert off.behavioral.target_pursuit_module is None

    on = arms.make_founder_genome(1, arms.gym_config(graph=True, pursuit_module=True))
    assert on.behavioral.behavior_graph is not None
    assert on.behavioral.target_pursuit_module is not None


def test_kinematics_are_reused_by_the_live_movement_strategy():
    """The live tank and the offline arms must share one kinematics body.

    A second copy is how an offline replica silently drifts from production -
    the version this replaced had already picked up a different anti-stuck
    turn constant that way - so the duplicate is pinned out rather than
    guarded by convention.
    """
    from pathlib import Path

    import core.movement_strategy as movement_strategy

    assert movement_strategy.apply_movement_kinematics is apply_movement_kinematics
    source = Path(movement_strategy.__file__).read_text(encoding="utf-8")
    assert "nudge_speed" not in source
    assert "ALGORITHMIC_MOVEMENT_SMOOTHING\n" not in source


def test_seeded_founders_differ_so_a_genome_cohort_is_a_real_sample():
    """Averaging over founders only means something if founders differ."""
    config = arms.gym_config(graph=False, pursuit_module=False)
    behaviors = {
        arms.make_founder_genome(seed, config).behavioral.behavior.value.behavior_id
        for seed in range(1, 9)
    }
    assert len(behaviors) > 1
