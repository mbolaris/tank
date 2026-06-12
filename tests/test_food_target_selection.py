"""Tests for quality-weighted food target selection (ADR-006 port).

Covers ComposableBehavior._select_food_target (the evolvable per-genome path)
and the shared observation builder's _best_food_vector (the builtin movement
path). Both were ported from the food_quality_optimizer monolith - the only
food-seeking algorithm that beat the production baseline on every benchmark
seed.
"""

from core.algorithms.composable.behavior import ComposableBehavior
from core.math_utils import Vector2
from core.worlds.shared.movement_observations import _best_food_vector


class StubFood:
    def __init__(self, x: float, y: float, energy: float):
        self.pos = Vector2(x, y)
        self._energy = energy

    def get_energy_value(self) -> float:
        return self._energy


class StubEnvironment:
    def __init__(self, foods):
        self._foods = foods

    def nearby_resources(self, fish, max_distance):
        return list(self._foods)


class StubFish:
    def __init__(self, foods, *, low=False, critical=False):
        self.pos = Vector2(0.0, 0.0)
        self.environment = StubEnvironment(foods)
        self._low = low
        self._critical = critical

    def is_low_energy(self) -> bool:
        return self._low

    def is_critical_energy(self) -> bool:
        return self._critical


def behavior(quality_weight: float, distance_weight: float) -> ComposableBehavior:
    return ComposableBehavior(
        parameters={
            "food_quality_weight": quality_weight,
            "food_distance_weight": distance_weight,
        }
    )


class TestSelectFoodTarget:
    def test_prefers_higher_quality_over_nearer_food(self):
        near_poor = StubFood(50, 0, energy=5.0)
        far_rich = StubFood(150, 0, energy=200.0)
        fish = StubFish([near_poor, far_rich])
        target = behavior(quality_weight=1.0, distance_weight=0.3)._select_food_target(fish)
        assert target is far_rich

    def test_zero_quality_weight_degenerates_to_nearest(self):
        near_poor = StubFood(50, 0, energy=5.0)
        far_rich = StubFood(150, 0, energy=200.0)
        fish = StubFish([near_poor, far_rich])
        target = behavior(quality_weight=0.0, distance_weight=0.5)._select_food_target(fish)
        assert target is near_poor

    def test_selectivity_skips_chases_that_cost_more_than_the_meal(self):
        # Comfortable fish, distant low-quality food: best score is below the
        # NORMAL threshold, so no target - the shared tactic of all three
        # ADR-006 winners.
        junk_far_away = StubFood(400, 0, energy=1.0)
        fish = StubFish([junk_far_away])
        target = behavior(quality_weight=1.0, distance_weight=0.5)._select_food_target(fish)
        assert target is None

    def test_critical_fish_loosens_threshold(self):
        # The same junk chase is accepted when starving (CRITICAL threshold).
        junk = StubFood(120, 0, energy=1.0)
        comfortable = StubFish([junk])
        starving = StubFish([junk], low=True, critical=True)
        b = behavior(quality_weight=1.0, distance_weight=0.5)
        assert b._select_food_target(comfortable) is None
        assert b._select_food_target(starving) is junk

    def test_no_food_returns_none(self):
        assert behavior(0.5, 0.5)._select_food_target(StubFish([])) is None

    def test_out_of_detection_range_ignored(self):
        beyond_range = StubFood(10_000, 0, energy=500.0)
        fish = StubFish([beyond_range])
        assert behavior(1.0, 0.3)._select_food_target(fish) is None


class TestBestFoodVector:
    def test_vector_points_at_quality_weighted_choice(self):
        near_poor = StubFood(50, 0, energy=5.0)
        far_rich = StubFood(0, 150, energy=200.0)
        fish = StubFish([near_poor, far_rich])
        vec = _best_food_vector(fish, StubFood, max_distance=600.0)
        assert (vec["x"], vec["y"]) == (0.0, 150.0)

    def test_no_food_returns_zero_vector(self):
        vec = _best_food_vector(StubFish([]), StubFood, max_distance=600.0)
        assert vec == {"x": 0.0, "y": 0.0}

    def test_items_without_energy_value_degenerate_to_nearest(self):
        class PlainItem:
            def __init__(self, x, y):
                self.pos = Vector2(x, y)

        near = PlainItem(40, 0)
        far = PlainItem(200, 0)
        fish = StubFish([near, far])
        vec = _best_food_vector(fish, PlainItem, max_distance=600.0)
        assert (vec["x"], vec["y"]) == (40.0, 0.0)
