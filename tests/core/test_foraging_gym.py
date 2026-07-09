"""Regression tests for the frozen, isolated foraging skill ruler."""

import math

from benchmarks.tank import foraging_gym
from core.foraging.gym import FOOD_COUNT, build_food_schedule, evaluate_foraging_gym


def test_schedule_is_seeded_and_lane_transitions_are_oracle_feasible():
    """A seed maps to one immutable schedule whose ceiling policy can traverse it."""
    first = build_food_schedule(42)
    assert first == build_food_schedule(42)
    assert first != build_food_schedule(7)
    assert len(first) == FOOD_COUNT


def test_oracle_attains_the_full_scripted_energy_ceiling():
    """The claimed ceiling is a reachable bound, never a fitted reference score."""
    for seed in (42, 7, 123):
        evaluation = evaluate_foraging_gym(seed)
        assert evaluation.oracle.food_collected == FOOD_COUNT
        assert math.isclose(evaluation.oracle.energy_collected, evaluation.oracle_energy)
        assert 0.0 <= evaluation.composable_ratio <= 1.0
        assert 0.0 <= evaluation.random_walk_ratio <= 1.0


def test_benchmark_is_deterministic_and_emits_frozen_ruler_metadata():
    first = foraging_gym.run(42)
    second = foraging_gym.run(42)

    assert first["score"] == second["score"]
    assert 0.0 <= first["score"] <= 1.0
    assert first["score_breakdown"]["oracle_energy_ratio"] == 1.0

    skill = first["metadata"]["skill"]
    assert skill["domain"] == "foraging"
    assert [rung["rung_id"] for rung in skill["rungs"]] == [
        "random_walk_v1",
        "full_information_greedy_v1",
    ]
