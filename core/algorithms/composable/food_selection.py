"""Food target prediction and selection for composable behaviors.

Extracted from ``actions.py`` to keep that mixin under the god-class ceiling.
Both functions are pure (they read only the fish and the world, never behavior
state): a fish decides which detected food to pursue (:func:`select_food_target`)
and where to intercept it (:func:`predict_food_target`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from core.behavior.primitives.steering import blend_prediction, predict_linear_intercept
from core.config.fish import CRITICAL_ENERGY_THRESHOLD_RATIO, SAFE_ENERGY_THRESHOLD_RATIO
from core.config.food import (
    BASE_FOOD_DETECTION_RANGE,
    CHASE_DISTANCE_LOW,
    CHASE_DISTANCE_SAFE_BASE,
    FOOD_QUALITY_DISTANCE_WEIGHT,
    FOOD_SINK_ACCELERATION,
)
from core.entities import Food
from core.math_utils import Vector2
from core.predictive_movement import predict_falling_intercept

if TYPE_CHECKING:
    from core.entities import Fish


# Critical fish keep the status-quo detection reach; the low/safe caps below
# are the actual energy-saving change for fish with enough energy to be choosy.
COMPOSABLE_CHASE_DISTANCE_CRITICAL = BASE_FOOD_DETECTION_RANGE


def _numeric_energy_ratio(fish: Fish) -> float | None:
    """Return the fish energy ratio when the object exposes it numerically."""
    get_energy_ratio = getattr(fish, "get_energy_ratio", None)
    if callable(get_energy_ratio):
        ratio = get_energy_ratio()
        if isinstance(ratio, (int, float)):
            return max(0.0, ratio)

    energy = getattr(fish, "energy", None)
    max_energy = getattr(fish, "max_energy", None)
    if isinstance(energy, (int, float)) and isinstance(max_energy, (int, float)) and max_energy > 0:
        return max(0.0, energy / max_energy)

    return None


def _food_chase_distance_for_energy(fish: Fish) -> float:
    """Return the energy-state chase cap for composable food selection."""
    energy_ratio = _numeric_energy_ratio(fish)
    if energy_ratio is None:
        return BASE_FOOD_DETECTION_RANGE

    if energy_ratio < CRITICAL_ENERGY_THRESHOLD_RATIO:
        return COMPOSABLE_CHASE_DISTANCE_CRITICAL
    if energy_ratio < SAFE_ENERGY_THRESHOLD_RATIO:
        return float(CHASE_DISTANCE_LOW)
    return float(CHASE_DISTANCE_SAFE_BASE)


def predict_food_target(
    fish: Fish, food: Food, distance: float, prediction_skill: float
) -> Vector2:
    """Return the predicted intercept position for a food item.

    Falls back to the food's current position when it isn't moving.
    skill_factor floor of 0.30 preserves useful prediction even for
    unskilled fish without over-committing to noisy long-horizon intercepts.
    """
    target_pos: Vector2 = food.pos

    if not hasattr(food, "vel"):
        return target_pos

    food_vel = food.vel
    if food_vel.length() <= 0.01:
        return target_pos

    if hasattr(food, "food_properties"):
        sink_multiplier = cast(float, food.food_properties.get("sink_multiplier", 1.0))
        acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
        if acceleration > 0 and food_vel.y >= 0:
            predicted_pos, _ = predict_falling_intercept(
                fish.pos, fish.speed, food.pos, food_vel, acceleration
            )
        else:
            predicted_pos = predict_linear_intercept(
                fish.pos, fish.speed, food.pos, food_vel, distance
            )
    else:
        predicted_pos = predict_linear_intercept(fish.pos, fish.speed, food.pos, food_vel, distance)

    return blend_prediction(food.pos, predicted_pos, prediction_skill)


@dataclass(frozen=True)
class FoodCandidateScore:
    """A food item within detection/chase range, with its selection score.

    ``score`` is the exact distance-discounted desirability
    ``select_food_target`` picks the winner by - exposed per-candidate (not
    just for the winner) so other callers needing to compare multiple
    candidates - e.g. target-memory's continue/switch decision - use the same
    definition of "value" instead of recomputing a different one.
    """

    food: Food
    position: tuple[float, float]
    velocity: tuple[float, float]
    score: float


def score_food_candidates(fish: Fish) -> list[FoodCandidateScore]:
    """Score every food item within detection/chase range.

    See ``select_food_target`` for the desirability formula this applies.
    Returns every in-range candidate (not just the best) in iteration order;
    ``select_food_target`` is a thin wrapper that picks the max from this list,
    so the two can never disagree on what "value" means.
    """
    env = fish.environment

    detection_modifier = getattr(env, "get_detection_modifier", lambda: 1.0)()
    detection_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier
    chase_distance = _food_chase_distance_for_energy(fish)
    max_distance = min(detection_distance, chase_distance)
    max_distance_sq = max_distance * max_distance

    if hasattr(env, "nearby_resources"):
        nearby = cast(list[Food], env.nearby_resources(fish, int(max_distance) + 1))
    else:
        nearby = cast(list[Food], env.nearby_agents_by_type(fish, int(max_distance) + 1, Food))
    if not nearby:
        return []

    fish_x = fish.pos.x
    fish_y = fish.pos.y
    candidates: list[FoodCandidateScore] = []

    for food in nearby:
        dx = food.pos.x - fish_x
        dy = food.pos.y - fish_y
        dist_sq = dx * dx + dy * dy
        if dist_sq > max_distance_sq:
            continue

        get_energy = getattr(food, "get_energy_value", None)
        energy = get_energy() if callable(get_energy) else 1.0
        distance = math.sqrt(dist_sq)
        score = energy / (1.0 + FOOD_QUALITY_DISTANCE_WEIGHT * distance)

        candidates.append(
            FoodCandidateScore(
                food=food,
                position=(float(food.pos.x), float(food.pos.y)),
                velocity=(float(food.vel.x), float(food.vel.y)),
                score=score,
            )
        )

    return candidates


def select_food_target(fish: Fish) -> Food | None:
    """Pick the best food to pursue within detection range.

    Unlike the proximity-only ``_find_nearest_food`` helper (kept for the cheap
    "is any food in range?" survival-priority check and the legacy algorithms),
    this weighs each detected food's energy value against the cost of swimming
    to it, so a fish prefers a richer morsel when it is not much farther than a
    poorer one:

        desirability = energy / (1 + FOOD_QUALITY_DISTANCE_WEIGHT * distance)

    As ``FOOD_QUALITY_DISTANCE_WEIGHT`` -> 0 the choice ignores distance (take
    the richest food in range); larger values increasingly favor closer food
    (energy-per-distance), approaching pure proximity.

    Determinism: basic float arithmetic only (``sqrt`` is correctly rounded in
    IEEE-754), with an explicit ``(pos.x, pos.y)`` tie-break so the choice never
    depends on spatial-query iteration order.
    """
    best: Food | None = None
    best_score = -1.0
    best_key: tuple[float, float] | None = None

    for candidate in score_food_candidates(fish):
        key = candidate.position
        if candidate.score > best_score or (
            candidate.score == best_score and (best_key is None or key < best_key)
        ):
            best_score = candidate.score
            best = candidate.food
            best_key = key

    return best
