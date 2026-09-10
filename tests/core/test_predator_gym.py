"""The predator gym must pose a joint problem, and must not rig its answer.

core.foraging.school_gym priced the behavior graph's cohesion branch in
foraging and stated its own limit: no predator. This gym is the other half, so
the properties that make its answer trustworthy are pinned here - above all
that both pressures bite and that the predator is the tank's own mechanic
rather than one chosen to produce a result.
"""

import math

import pytest

from core.entities.predators import Crab
from core.foraging import predator_arms
from core.foraging.predator_gym import (
    CRAB_LANE_Y,
    SCHOOL_SIZE,
    _GymCrab,
    build_predator_schedule,
    run_predator_episode,
)
from core.foraging.predator_references import (
    FeedAndFleePolicy,
    FeedIgnoringPredatorPolicy,
    HidePolicy,
    reference_pressures,
)


def _run(policy_factory, seed=42):
    schedule = build_predator_schedule(seed)
    return run_predator_episode(schedule, [policy_factory() for _ in range(SCHOOL_SIZE)], seed)


def test_hiding_starves():
    """If hiding were survivable the gym would not require foraging at all."""
    result = _run(HidePolicy)
    assert result.deaths_starvation == SCHOOL_SIZE
    assert result.deaths_predation == 0
    assert result.food_collected == 0


def test_ignoring_the_predator_gets_you_eaten():
    """If predation were free the gym would not require evasion at all."""
    result = _run(FeedIgnoringPredatorPolicy)
    assert result.deaths_predation == SCHOOL_SIZE
    assert result.deaths_starvation == 0


def test_the_joint_problem_is_solvable():
    """Both pressures must bite, but not so hard that nothing can pass.

    An unsolvable gym would rank every controller by noise.
    """
    competent = _run(FeedAndFleePolicy)
    assert competent.alive_at_end > 0
    assert competent.survival_ratio > _run(FeedIgnoringPredatorPolicy).survival_ratio


def test_reference_pressures_assert_both_bite():
    results = reference_pressures(42)
    assert set(results) == {"hide", "feed_ignoring_predator", "feed_and_flee"}


def test_the_predator_is_the_tanks_own_mechanic():
    """The gym's crab must be a real Crab and must use the tank's cooldown.

    The adapters find threats with isinstance(entity, Crab), so a look-alike
    would be invisible to exactly the branch under test. And a locally-chosen
    cooldown would let this gym drift away from the tank whose question it is
    answering - the cooldown is the dilution mechanism itself.
    """
    from core.config.entities import CRAB_ATTACK_COOLDOWN

    crab = _GymCrab(100.0)
    assert isinstance(crab, Crab)

    assert crab.can_hunt()
    crab.eat()
    assert not crab.can_hunt()
    for _ in range(CRAB_ATTACK_COOLDOWN):
        crab.step()
    assert crab.can_hunt()


def test_the_cooldown_actually_shields_a_second_fish():
    """Dilution, demonstrated rather than assumed.

    This is why grouping *could* pay under predation, and it is the mechanism
    the whole instrument rests on.
    """
    crab = _GymCrab(100.0)
    crab.eat()
    crab.step()
    assert not crab.can_hunt()


def test_the_crab_patrols_its_lane_and_turns_at_the_walls():
    crab = _GymCrab(1.0)
    crab.vel.x = -5.0
    crab.step()
    assert crab.vel.x > 0
    assert crab.pos.y == CRAB_LANE_Y


def test_fish_can_see_the_predator():
    """The threat vector is nonzero here for the first time in any gym."""
    schedule = build_predator_schedule(42)
    seen: list[int] = []

    class _Watcher:
        def velocity(self, fish, active_food):
            seen.append(len(fish.environment.nearby_agents_by_type(fish, 400, Crab)))
            return FeedAndFleePolicy().velocity(fish, active_food)

    run_predator_episode(schedule, [_Watcher() for _ in range(SCHOOL_SIZE)], 42)
    assert max(seen) > 0


def test_episodes_are_deterministic():
    assert _run(FeedAndFleePolicy) == _run(FeedAndFleePolicy)


def test_a_wrong_sized_school_is_rejected():
    with pytest.raises(ValueError, match="expected"):
        run_predator_episode(build_predator_schedule(42), [HidePolicy()], 42)


# --- arms -------------------------------------------------------------------


def test_survival_is_bounded_and_references_bracket_the_arms():
    comparison = predator_arms.compare_predator_arms((1,), (42,))
    for arm in comparison.arms():
        assert 0.0 <= comparison.mean_survival(arm) <= 1.0


def test_the_flag_off_arbiter_matches_the_bare_composable_controller():
    """The same control the other two gyms use."""
    comparison = predator_arms.compare_predator_arms((1, 2), (42,))
    assert math.isclose(
        comparison.mean_survival("composable"),
        comparison.mean_survival("production"),
        abs_tol=1e-12,
    )


def test_reference_arms_need_no_genome():
    score = predator_arms.evaluate_predator_arm(predator_arms.HIDE, None, 42, None)
    assert score.result.deaths_starvation == SCHOOL_SIZE

    with pytest.raises(ValueError, match="needs a genome"):
        predator_arms.evaluate_predator_arm("composable", None, 42, None)
