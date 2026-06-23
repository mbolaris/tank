"""Food target prediction and selection for composable behaviors.

Extracted from ``actions.py`` to keep that mixin under the god-class ceiling.
Both functions are pure (they read only the fish and the world, never behavior
state): a fish decides which detected food to pursue (:func:`select_food_target`)
and where to intercept it (:func:`predict_food_target`).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from core.config.food import (
    BASE_FOOD_DETECTION_RANGE,
    FOOD_QUALITY_DISTANCE_WEIGHT,
    FOOD_SINK_ACCELERATION,
)
from core.entities import Food as FoodClass
from core.math_utils import Vector2
from core.predictive_movement import predict_falling_intercept

if TYPE_CHECKING:
    from core.entities import Fish


def predict_food_target(fish: Fish, food: Any, distance: float, prediction_skill: float) -> Vector2:
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
        sink_multiplier = food.food_properties.get("sink_multiplier", 1.0)
        acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
        if acceleration > 0 and food_vel.y >= 0:
            predicted_pos, _ = predict_falling_intercept(
                fish.pos, fish.speed, food.pos, food_vel, acceleration
            )
        else:
            time_to_reach = min(distance / max(fish.speed, 0.1), 60.0)
            predicted_pos = Vector2(
                food.pos.x + food_vel.x * time_to_reach,
                food.pos.y + food_vel.y * time_to_reach,
            )
    else:
        time_to_reach = min(distance / max(fish.speed, 0.1), 60.0)
        predicted_pos = Vector2(
            food.pos.x + food_vel.x * time_to_reach,
            food.pos.y + food_vel.y * time_to_reach,
        )

    skill_factor = 0.30 + prediction_skill * 0.70
    return Vector2(
        food.pos.x * (1 - skill_factor) + predicted_pos.x * skill_factor,
        food.pos.y * (1 - skill_factor) + predicted_pos.y * skill_factor,
    )


def select_food_target(fish: Fish) -> Any | None:
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
    env = fish.environment

    detection_modifier = getattr(env, "get_detection_modifier", lambda: 1.0)()
    max_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier
    max_distance_sq = max_distance * max_distance

    if hasattr(env, "nearby_resources"):
        nearby = env.nearby_resources(fish, int(max_distance) + 1)
    else:
        nearby = env.nearby_agents_by_type(fish, int(max_distance) + 1, FoodClass)
    if not nearby:
        return None

    fish_x = fish.pos.x
    fish_y = fish.pos.y
    best = None
    best_score = -1.0
    best_key: tuple[float, float] | None = None

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

        key = (food.pos.x, food.pos.y)
        if score > best_score or (score == best_score and (best_key is None or key < best_key)):
            best_score = score
            best = food
            best_key = key

    return best
