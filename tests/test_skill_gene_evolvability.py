"""Tests for newly evolvable skill-substrate genes.

Two skill substrates gained heritable variation that they previously lacked:

* Poker ``learning_rate`` - a heritable field that scales every CFR regret
  update but was frozen at 1.0 (never randomized, never mutated). It now has
  declared bounds, mutates in ``ComposablePokerStrategy.mutate``, and is
  clamped at every boundary.
* Soccer on-ball pursuit control - the previously hard-coded steering
  constants (align-before-dash threshold and dash-commit distance) are now the
  evolvable ``approach_precision`` / ``pursuit_commit`` params. Both are
  neutral at a raw genome value of 0.0 (they reproduce the old constants).
"""

import random

import pytest

from core.code_pool.pool import (
    SOCCER_POLICY_PARAM_KEYS,
    _soccer_policy_core,
    _steer_action,
    default_soccer_policy_params,
)
from core.poker.strategy.composable.definitions import LEARNING_RATE_BOUNDS
from core.poker.strategy.composable.strategy import ComposablePokerStrategy


class TestPokerLearningRateGene:
    """The CFR learning rate is now a real, bounded, mutable gene."""

    def test_default_is_neutral_and_in_bounds(self):
        strat = ComposablePokerStrategy()
        assert strat.learning_rate == 1.0
        assert LEARNING_RATE_BOUNDS[0] <= strat.learning_rate <= LEARNING_RATE_BOUNDS[1]

    def test_post_init_clamps_out_of_range_learning_rate(self):
        assert ComposablePokerStrategy(learning_rate=99.0).learning_rate == LEARNING_RATE_BOUNDS[1]
        assert ComposablePokerStrategy(learning_rate=-5.0).learning_rate == LEARNING_RATE_BOUNDS[0]

    def test_zero_mutation_rate_leaves_learning_rate_untouched(self):
        strat = ComposablePokerStrategy(learning_rate=0.7)
        strat.mutate(mutation_rate=0.0, sub_behavior_switch_rate=0.0, rng=random.Random(1))
        assert strat.learning_rate == pytest.approx(0.7)

    def test_mutation_can_change_learning_rate_within_bounds(self):
        # Force mutation every call; confirm it actually moves and stays bounded.
        changed = False
        for seed in range(50):
            strat = ComposablePokerStrategy(learning_rate=1.0)
            strat.mutate(mutation_rate=1.0, mutation_strength=0.3, rng=random.Random(seed))
            assert LEARNING_RATE_BOUNDS[0] <= strat.learning_rate <= LEARNING_RATE_BOUNDS[1]
            if strat.learning_rate != pytest.approx(1.0):
                changed = True
        assert changed, "learning_rate must be able to mutate away from its default"

    def test_offspring_inherit_and_can_diverge_in_learning_rate(self):
        rng = random.Random(7)
        p1 = ComposablePokerStrategy(learning_rate=0.5)
        p2 = ComposablePokerStrategy(learning_rate=2.0)
        child = ComposablePokerStrategy.from_parents(
            p1, p2, weight1=0.5, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        assert LEARNING_RATE_BOUNDS[0] <= child.learning_rate <= LEARNING_RATE_BOUNDS[1]


class TestSoccerPursuitGenes:
    """approach_precision / pursuit_commit widen the soccer substrate."""

    def test_new_keys_present_and_seeded(self):
        assert "approach_precision" in SOCCER_POLICY_PARAM_KEYS
        assert "pursuit_commit" in SOCCER_POLICY_PARAM_KEYS
        params = default_soccer_policy_params()
        assert set(params.keys()) == set(SOCCER_POLICY_PARAM_KEYS)
        # Un-jittered defaults are exactly neutral.
        assert params["approach_precision"] == 0.0
        assert params["pursuit_commit"] == 0.0

    def test_neutral_at_zero_matches_missing_params(self):
        base_obs = {
            "position": {"x": 0.0, "y": 0.0},
            "ball_relative_pos": {"x": 8.0, "y": 3.0},
            "goal_direction": {"x": 40.0, "y": 0.0},
            "ball_vel_x": 0.5,
            "ball_vel_y": 0.0,
            "facing_angle": 1.2,
            "stamina_ratio": 0.9,
            "field_length": 100.0,
        }
        missing = _soccer_policy_core({**base_obs, "params": {}}, role="chaser")
        zeroed = _soccer_policy_core(
            {**base_obs, "params": dict.fromkeys(SOCCER_POLICY_PARAM_KEYS, 0.0)},
            role="chaser",
        )
        assert missing == zeroed

    def test_steer_defaults_reproduce_old_constants(self):
        # Old hard-coded constants were align_threshold=0.25, commit_dist=0.4.
        import math

        ang, dist = 0.35, 5.0
        tx, ty = dist * math.cos(ang), dist * math.sin(ang)
        explicit = _steer_action(tx, ty, 0.0, 0.9, 0.35, align_threshold=0.25, commit_dist=0.4)
        defaulted = _steer_action(tx, ty, 0.0, 0.9, 0.35)
        assert explicit == defaulted

    def test_align_threshold_changes_alignment_behavior(self):
        import math

        ang, dist = 0.35, 5.0
        tx, ty = dist * math.cos(ang), dist * math.sin(ang)
        # A 0.35 rad heading error is above the tight 0.25 threshold (keep
        # turning, dash suppressed) but below the loose 0.49 one (commit to a
        # dash despite the error) - align_threshold must flip the mode.
        tight = _steer_action(tx, ty, 0.0, 0.9, 0.35, align_threshold=0.25)
        loose = _steer_action(tx, ty, 0.0, 0.9, 0.35, align_threshold=0.49)
        assert tight["turn"] != 0.0 and tight["dash"] == 0.0
        assert loose["dash"] == pytest.approx(1.0)

    def test_pursuit_commit_changes_dash_cutoff(self):
        near = _steer_action(0.6, 0.0, 0.0, 0.9, 0.35, commit_dist=0.4)
        wide = _steer_action(0.6, 0.0, 0.0, 0.9, 0.35, commit_dist=0.9)
        assert near["dash"] == pytest.approx(1.0)
        assert wide["dash"] == pytest.approx(0.0)
