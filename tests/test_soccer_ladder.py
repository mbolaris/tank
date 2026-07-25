"""Tests for the frozen soccer reference ladder.

These guard the properties that make the ladder a *ruler*: the reference teams
must be immutable in identity, blind to the evolvable parameter space, and
deterministic; and the benchmark harness must cancel the side advantage so a
goal difference means skill rather than which end you kicked off from.
"""

from __future__ import annotations

import math
import random
from typing import Any

import pytest

from benchmarks.soccer import ladder_5k
from core.code_pool import create_default_genome_code_pool
from core.minigames.soccer.reference_teams import (
    REFERENCE_CHASE_SHOOT_ID,
    REFERENCE_FORMATION_ID,
    REFERENCE_FORMATION_STRIKER_ID,
    REFERENCE_LADDER,
    REFERENCE_POLICY_KIND,
    REFERENCE_RANDOM_WALK_ID,
    REFERENCE_STATIONARY_ID,
    chase_shoot_reference_policy,
    formation_defender_reference_policy,
    formation_striker_reference_policy,
    random_walk_reference_policy,
    register_reference_policies,
    stationary_reference_policy,
)

# A short match keeps the harness tests fast; the ladder's scoring behavior is
# frame-count independent.
_TEST_FRAMES = 250


def _observation(**overrides: Any) -> dict[str, Any]:
    """A representative mid-field observation as build_observation emits it."""
    observation: dict[str, Any] = {
        "position": {"x": -5.0, "y": 3.0},
        "ball_relative_pos": {"x": 12.0, "y": -4.0},
        "goal_direction": {"x": 45.0, "y": -3.0},
        "ball_vel_x": 0.8,
        "ball_vel_y": -0.2,
        "facing_angle": 0.1,
        "stamina_ratio": 0.9,
        "field_length": 105.0,
    }
    observation.update(overrides)
    return observation


def test_ladder_rung_identities_are_stable() -> None:
    """Rung ids are the ledger's join key; renaming one rewrites history."""
    assert [(team.rung, team.rung_id) for team in REFERENCE_LADDER] == [
        ("L0", "stationary_v1"),
        ("L1", "random_walk_v1"),
        ("L2", "chase_shoot_v1"),
        ("L3", "formation_v1"),
    ]


def test_formation_rung_binds_three_distinct_roles() -> None:
    """L3 is the only rung whose slots differ, and it cycles deterministically."""
    formation = REFERENCE_LADDER[3]
    assert formation.slot_policy_ids == (
        REFERENCE_FORMATION_ID,
        REFERENCE_CHASE_SHOOT_ID,
        REFERENCE_FORMATION_STRIKER_ID,
    )
    assert formation.policy_id_for_slot(0) == REFERENCE_FORMATION_ID
    assert formation.policy_id_for_slot(3) == REFERENCE_FORMATION_ID
    assert formation.policy_id_for_slot(4) == REFERENCE_CHASE_SHOOT_ID


def test_stationary_ruler_never_issues_an_action() -> None:
    action = stationary_reference_policy(_observation(), random.Random(0))
    assert action == {"turn": 0.0, "dash": 0.0, "kick_power": 0.0, "kick_angle": 0.0}


def test_random_walk_ruler_ignores_the_observation() -> None:
    """The floor-plus-noise rung must not accidentally become ball-aware."""
    from_default = random_walk_reference_policy(_observation(), random.Random(7))
    from_elsewhere = random_walk_reference_policy(
        _observation(ball_relative_pos={"x": -30.0, "y": 25.0}, goal_direction={"x": -50.0}),
        random.Random(7),
    )
    assert from_default == from_elsewhere


def test_random_walk_ruler_rng_draw_count_is_fixed() -> None:
    """Stable RNG consumption keeps the rung reproducible across refactors."""
    rng = random.Random(11)
    random_walk_reference_policy(_observation(), rng)
    consumed = random.Random(11)
    consumed.uniform(-1.0, 1.0)
    consumed.uniform(0.0, 1.0)
    assert rng.random() == consumed.random()


@pytest.mark.parametrize(
    "policy",
    [
        stationary_reference_policy,
        chase_shoot_reference_policy,
        formation_defender_reference_policy,
        formation_striker_reference_policy,
    ],
)
def test_rulers_ignore_the_evolvable_param_space(policy: Any) -> None:
    """A ruler that read soccer_policy_params would drift with the substrate."""
    baseline = policy(_observation(), None)
    extreme_params = {
        "intercept_lead": 10.0,
        "shot_range": -10.0,
        "dribble_power": 10.0,
        "stamina_floor": 10.0,
        "hold_depth": -10.0,
        "press_radius": 10.0,
        "approach_precision": 10.0,
        "pursuit_commit": -10.0,
    }
    assert policy(_observation(params=extreme_params), None) == baseline


def test_rulers_survive_a_malformed_observation() -> None:
    """A ruler must never crash a match; it stands still instead."""
    assert chase_shoot_reference_policy({"position": "not-a-dict"}, None) == {
        "turn": 0.0,
        "dash": 0.0,
        "kick_power": 0.0,
        "kick_angle": 0.0,
    }


def test_chase_ruler_shoots_when_the_ball_is_kickable() -> None:
    action = chase_shoot_reference_policy(
        _observation(ball_relative_pos={"x": 0.2, "y": 0.1}, goal_direction={"x": 20.0, "y": 0.0}),
        None,
    )
    assert action["kick_power"] == pytest.approx(1.0)


def test_chase_ruler_dribbles_when_the_goal_is_out_of_shot_range() -> None:
    action = chase_shoot_reference_policy(
        _observation(ball_relative_pos={"x": 0.2, "y": 0.1}, goal_direction={"x": 55.0, "y": 0.0}),
        None,
    )
    assert 0.0 < action["kick_power"] < 1.0


def test_registering_rulers_leaves_the_evolvable_roster_untouched() -> None:
    """Mutation draws from the soccer_policy roster; rulers must stay out of it.

    If a ruler shared that kind, an evolving genome could mutate onto the very
    opponent it is scored against.
    """
    pool = create_default_genome_code_pool()
    default_before = pool.get_default("soccer_policy")
    roster_before = pool.get_components_by_kind("soccer_policy")

    register_reference_policies(pool)

    assert pool.get_default("soccer_policy") == default_before
    assert pool.get_components_by_kind("soccer_policy") == roster_before
    for component_id in (
        REFERENCE_STATIONARY_ID,
        REFERENCE_RANDOM_WALK_ID,
        REFERENCE_CHASE_SHOOT_ID,
        REFERENCE_FORMATION_ID,
        REFERENCE_FORMATION_STRIKER_ID,
    ):
        assert pool.has_component(component_id)
        assert component_id not in roster_before


def test_registering_rulers_twice_is_idempotent() -> None:
    pool = create_default_genome_code_pool()
    register_reference_policies(pool)
    once = pool.get_components_by_kind(REFERENCE_POLICY_KIND)
    register_reference_policies(pool)
    assert pool.get_components_by_kind(REFERENCE_POLICY_KIND) == once
    assert len(once) == len(set(once)) == 5


def test_ladder_result_is_deterministic() -> None:
    first = ladder_5k.run(42, n_seeds=1, frames=_TEST_FRAMES)
    second = ladder_5k.run(42, n_seeds=1, frames=_TEST_FRAMES)
    assert first["score"] == second["score"]
    assert first["score_breakdown"] == second["score_breakdown"]


def test_ladder_result_matches_the_benchmark_contract() -> None:
    result = ladder_5k.run(42, n_seeds=1, frames=_TEST_FRAMES)

    assert result["benchmark_id"] == "soccer/ladder_5k"
    assert result["seed"] == 42
    assert isinstance(result["score"], float)
    assert set(result["score_breakdown"]) == {team.rung_id for team in REFERENCE_LADDER}

    skill = result["metadata"]["skill"]
    assert skill["domain"] == "soccer"
    assert [rung["rung"] for rung in skill["rungs"]] == ["L0", "L1", "L2", "L3"]
    assert 0.0 <= skill["skill_index"] <= 100.0


def test_every_rung_is_played_on_both_sides() -> None:
    """Side-swapping is what makes the goal difference a skill measure."""
    result = ladder_5k.run(42, n_seeds=2, frames=_TEST_FRAMES)

    for rung in result["metadata"]["per_rung_results"]:
        sides = [match["hero_side"] for match in rung["matches"]]
        assert sides.count("left") == sides.count("right") == 2
        assert rung["matches_played"] == 4


def test_side_swap_cancels_the_side_advantage() -> None:
    """The substrate playing its own frozen snapshot must come out level.

    L2 is a frozen copy of the neutral substrate chaser, so today the two teams
    are behaviorally identical and any nonzero mean goal difference would be a
    harness artifact - an uncancelled kickoff or formation advantage - rather
    than skill. This stays a valid harness check as the substrate improves: it
    only asserts the identity holds while the two remain equivalent, which the
    accompanying margin check reports rather than assumes.
    """
    result = ladder_5k.run(42, n_seeds=2, frames=_TEST_FRAMES)
    by_rung = {rung["rung_id"]: rung for rung in result["metadata"]["per_rung_results"]}

    l2 = by_rung["chase_shoot_v1"]
    per_seed_pairs = [
        (l2["matches"][index]["goal_diff"], l2["matches"][index + 1]["goal_diff"])
        for index in range(0, len(l2["matches"]), 2)
    ]
    for left_diff, right_diff in per_seed_pairs:
        assert left_diff == -right_diff, "swapped sides did not mirror on the same engine seed"
    assert l2["goal_diff_mean"] == pytest.approx(0.0)


def test_stationary_rung_cannot_score() -> None:
    """A ruler that never acts must never score - the floor stays a floor."""
    result = ladder_5k.run(42, n_seeds=1, frames=_TEST_FRAMES)
    by_rung = {rung["rung_id"]: rung for rung in result["metadata"]["per_rung_results"]}
    assert by_rung["stationary_v1"]["reference_goals_mean"] == 0.0


def test_confidence_interval_brackets_the_mean() -> None:
    result = ladder_5k.run(42, n_seeds=2, frames=_TEST_FRAMES)
    for rung in result["metadata"]["per_rung_results"]:
        low, high = rung["goal_diff_ci_95"]
        assert low <= rung["goal_diff_mean"] <= high
        assert math.isfinite(low) and math.isfinite(high)
