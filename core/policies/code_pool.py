"""Code policy pool for runtime behavior overrides."""

from __future__ import annotations

import math
import random
from typing import Callable

from core.policies.interfaces import MovementAction, Observation

MovementPolicyCallable = Callable[[Observation, random.Random], object]

BUILTIN_SEEK_NEAREST_FOOD_ID = "builtin_seek_nearest_food"


class CodePool:
    """Stores callable policy components keyed by ID."""

    def __init__(self) -> None:
        self._components: dict[str, MovementPolicyCallable] = {}

    def register(self, component_id: str, func: MovementPolicyCallable) -> None:
        self._components[str(component_id)] = func

    def get_callable(self, component_id: str) -> MovementPolicyCallable | None:
        return self._components.get(str(component_id))


def seek_nearest_food_policy(observation: Observation, rng: random.Random) -> MovementAction:
    """Simple built-in movement policy that heads toward the nearest food vector."""
    _ = rng
    food_vector = observation.get("nearest_food_vector")
    if isinstance(food_vector, dict):
        try:
            dx = float(food_vector.get("x", 0.0))
            dy = float(food_vector.get("y", 0.0))
        except (TypeError, ValueError):
            dx = 0.0
            dy = 0.0
        length_sq = dx * dx + dy * dy
        if length_sq > 0:
            length = math.sqrt(length_sq)
            return MovementAction(dx / length, dy / length)
    return MovementAction(0.0, 0.0)
