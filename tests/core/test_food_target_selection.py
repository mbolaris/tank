"""Regression tests for ComposableBehavior._select_food_target.

The composable behavior chooses which detected food to pursue by weighing each
item's energy value against the cost of swimming to it, instead of blindly
chasing the nearest morsel (see core/config/food.py::FOOD_QUALITY_DISTANCE_WEIGHT
and the foraging-contention diagnosis in docs/IMPROVEMENT_PROPOSALS.md).
"""

from unittest.mock import MagicMock

from core.algorithms.composable.behavior import ComposableBehavior
from core.config.food import FOOD_QUALITY_DISTANCE_WEIGHT
from core.math_utils import Vector2


def _food(x: float, y: float, energy: float) -> MagicMock:
    food = MagicMock()
    food.pos = Vector2(x, y)
    food.get_energy_value.return_value = energy
    return food


def _fish_in(env: MagicMock) -> MagicMock:
    fish = MagicMock()
    fish.pos = Vector2(0.0, 0.0)
    fish.environment = env
    return fish


def _env_with(foods: list) -> MagicMock:
    env = MagicMock()
    env.get_detection_modifier.return_value = 1.0
    env.nearby_resources.return_value = foods
    return env


def test_prefers_richer_food_when_comparably_close():
    """A richer item slightly farther beats a poor item that is closer."""
    near_poor = _food(10.0, 0.0, 65.0)  # 65/(1+0.02*10) = 54.2
    far_rich = _food(30.0, 0.0, 120.0)  # 120/(1+0.02*30) = 75.0
    behavior = ComposableBehavior()

    target = behavior._select_food_target(_fish_in(_env_with([near_poor, far_rich])))

    assert target is far_rich


def test_prefers_closer_food_when_quality_is_equal():
    """With equal energy, the nearer item wins (higher desirability)."""
    near = _food(10.0, 0.0, 100.0)
    far = _food(200.0, 0.0, 100.0)
    behavior = ComposableBehavior()

    target = behavior._select_food_target(_fish_in(_env_with([far, near])))

    assert target is near


def test_returns_none_when_no_food_detected():
    behavior = ComposableBehavior()
    assert behavior._select_food_target(_fish_in(_env_with([]))) is None


def test_ignores_food_beyond_detection_range():
    """Food outside BASE_FOOD_DETECTION_RANGE (580px) is not selectable."""
    too_far = _food(600.0, 0.0, 1000.0)  # very rich but out of range
    behavior = ComposableBehavior()
    assert behavior._select_food_target(_fish_in(_env_with([too_far]))) is None


def test_tie_break_is_deterministic_and_order_independent():
    """Equal-desirability foods resolve to the lowest (pos.x, pos.y), regardless
    of the order the spatial query returns them in."""
    a = _food(10.0, 0.0, 100.0)
    b = _food(0.0, 10.0, 100.0)  # same distance/energy, lower x -> should win
    behavior = ComposableBehavior()

    pick_ab = behavior._select_food_target(_fish_in(_env_with([a, b])))
    pick_ba = behavior._select_food_target(_fish_in(_env_with([b, a])))

    assert pick_ab is b
    assert pick_ba is b


def test_weight_zero_picks_globally_richest_in_range():
    """As the distance weight -> 0 the selector ignores distance (sanity check on
    the documented limiting behavior)."""
    import core.algorithms.composable.actions as actions_mod

    near_poor = _food(10.0, 0.0, 65.0)
    far_rich = _food(400.0, 0.0, 120.0)
    behavior = ComposableBehavior()

    original = actions_mod.FOOD_QUALITY_DISTANCE_WEIGHT
    try:
        actions_mod.FOOD_QUALITY_DISTANCE_WEIGHT = 0.0
        target = behavior._select_food_target(_fish_in(_env_with([near_poor, far_rich])))
    finally:
        actions_mod.FOOD_QUALITY_DISTANCE_WEIGHT = original

    assert target is far_rich
    # Guard against accidentally shipping weight=0 (which disables proximity).
    assert FOOD_QUALITY_DISTANCE_WEIGHT > 0.0
