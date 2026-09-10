"""The school gym must measure distribution, not travel.

Backlog 12.4 could not evaluate the behavior graph's cohesion branch because
the single-fish gym has no school. This instrument exists to see it, so the
properties that make it able to are pinned here: neighbours are real, the
ceiling is attainable only by a school that splits up, and staying together
actually costs energy.
"""

import math

import pytest

from core.foraging import school_arms
from core.foraging.school_gym import (
    SCHOOL_SIZE,
    STATIONS,
    AssignedOraclePolicy,
    GreedyShoalPolicy,
    RandomWalkPolicy,
    build_wave_schedule,
    oracle_energy_ceiling,
    run_school_episode,
)


def _run(policy_factory, seed=42):
    schedule = build_wave_schedule(seed)
    policies = [policy_factory(index) for index in range(SCHOOL_SIZE)]
    return schedule, run_school_episode(schedule, policies, seed)


def test_every_wave_offers_one_item_per_fish():
    """The ceiling is only reachable by a school that splits SCHOOL_SIZE ways."""
    schedule = build_wave_schedule(42)
    by_frame: dict[int, set[int]] = {}
    for spawn in schedule:
        by_frame.setdefault(spawn.frame, set()).add(spawn.station)
    assert by_frame, "expected at least one wave"
    for stations in by_frame.values():
        assert stations == set(range(len(STATIONS)))


def test_the_ceiling_is_attainable_not_fitted():
    for seed in (42, 7, 123):
        schedule, result = _run(lambda _index: AssignedOraclePolicy(), seed)
        assert math.isclose(result.energy_collected, oracle_energy_ceiling(schedule))
        assert result.food_expired == 0


def test_a_clustered_school_loses_food_to_expiry():
    """The instrument's whole premise: staying together has a price.

    Every fish independently chasing the best item converges on one, and the
    other three expire. If this ever stops being true the gym has stopped
    measuring distribution and its scores mean something else.
    """
    schedule, greedy = _run(lambda _index: GreedyShoalPolicy())
    _, oracle = _run(lambda _index: AssignedOraclePolicy())

    assert greedy.food_expired > 0
    assert greedy.energy_collected < oracle.energy_collected
    assert greedy.mean_neighbour_distance < oracle.mean_neighbour_distance


def test_the_floor_is_below_the_shoal():
    _, random_walk = _run(lambda index: RandomWalkPolicy(index))
    _, greedy = _run(lambda _index: GreedyShoalPolicy())
    assert random_walk.energy_collected < greedy.energy_collected


def test_fish_can_see_each_other():
    """The single-fish gym's blind spot, closed.

    Without real neighbours the graph's cohesion vector is identically zero,
    which is exactly what made 12.4's bare graph score uninterpretable.
    """
    schedule = build_wave_schedule(42)
    seen: list[int] = []

    class _Watcher:
        def velocity(self, fish, active_food):
            seen.append(len(fish.environment.nearby_evolving_agents(fish, 500.0)))
            return GreedyShoalPolicy().velocity(fish, active_food)

    run_school_episode(schedule, [_Watcher() for _ in range(SCHOOL_SIZE)], 42)
    assert seen, "expected the policy to be stepped"
    assert max(seen) == SCHOOL_SIZE - 1


def test_episodes_are_deterministic():
    for _ in range(2):
        first = _run(lambda _index: GreedyShoalPolicy())[1]
        second = _run(lambda _index: GreedyShoalPolicy())[1]
        assert first == second


def test_a_wrong_sized_school_is_rejected():
    schedule = build_wave_schedule(42)
    with pytest.raises(ValueError, match="expected"):
        run_school_episode(schedule, [GreedyShoalPolicy()], 42)


# --- arms -------------------------------------------------------------------


def test_arms_keep_their_own_identities_in_a_school():
    """A school whose members share one fish_id reads as empty to the graph.

    core.foraging.arms installs an arbiter surface onto the single-fish gym's
    bare fish, including fish_id = 1. Applying that here would give every
    member the same id, and the graph's school vectors filter neighbours by
    id - reintroducing the exact blindness this gym removes.
    """
    import random

    from core.foraging.arms import _install_arbiter_surface
    from core.foraging.school_gym import _SchoolEnvironment, _SchoolFish
    from core.math_utils import Vector2

    environment = _SchoolEnvironment(random.Random(0))
    school = [
        _SchoolFish(pos=Vector2(float(index), 0.0), environment=environment, fish_id=index)
        for index in range(SCHOOL_SIZE)
    ]
    environment.fish = school

    for fish in school:
        _install_arbiter_surface(fish)

    assert [fish.fish_id for fish in school] == list(range(SCHOOL_SIZE))
    assert len(environment.nearby_evolving_agents(school[0], 500.0)) == SCHOOL_SIZE - 1


def test_reference_arms_bracket_the_evolvable_ones():
    comparison = school_arms.compare_school_arms((1,), (42,))
    oracle = comparison.mean_ratio(school_arms.ORACLE)
    floor = comparison.mean_ratio(school_arms.RANDOM_WALK)

    assert math.isclose(oracle, 1.0)
    for arm in comparison.arms():
        assert floor <= comparison.mean_ratio(arm) <= oracle


def test_the_flag_off_arbiter_matches_the_bare_composable_controller():
    """The comparison's own control, as in the single-fish gym."""
    comparison = school_arms.compare_school_arms((1, 2), (42,))
    assert math.isclose(
        comparison.mean_ratio("composable"), comparison.mean_ratio("production"), abs_tol=1e-12
    )


def test_the_urgency_threshold_changes_the_graph_arm():
    """If it did not, the sweep this gym exists to run would be meaningless."""
    hungry = school_arms.compare_school_arms((1,), (42,), arms=("graph",), urgency_threshold=1.0)
    social = school_arms.compare_school_arms((1,), (42,), arms=("graph",), urgency_threshold=0.0)
    assert hungry.mean_ratio("graph") != social.mean_ratio("graph")


def test_reference_arms_need_no_genome():
    score = school_arms.evaluate_school_arm(school_arms.ORACLE, None, 42, None)
    assert math.isclose(score.energy_ratio, 1.0)

    with pytest.raises(ValueError, match="needs a genome"):
        school_arms.evaluate_school_arm("composable", None, 42, None)
