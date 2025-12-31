"""Policy interfaces and observation builders for code-driven behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from core.entities import Fish

Observation = Dict[str, Any]


@dataclass(frozen=True)
class MovementAction:
    """Normalized movement action returned by code policies."""

    vx: float
    vy: float


def build_movement_observation(fish: Fish) -> Observation:
    """Build a minimal observation payload for movement policies."""
    from core.config.food import BASE_FOOD_DETECTION_RANGE
    from core.entities import Crab, Food

    environment = fish.environment
    detection_modifier = getattr(environment, "get_detection_modifier", lambda: 1.0)()
    max_food_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier

    nearest_food_vector = _nearest_vector(
        fish, Food, max_distance=max_food_distance, use_resources=True
    )
    nearest_threat_vector = _nearest_vector(fish, Crab, max_distance=200.0, use_resources=False)

    return {
        "position": {"x": fish.pos.x, "y": fish.pos.y},
        "velocity": {"x": fish.vel.x, "y": fish.vel.y},
        "nearest_food_vector": nearest_food_vector,
        "nearest_threat_vector": nearest_threat_vector,
        "energy": fish.energy,
        "age": getattr(getattr(fish, "_lifecycle_component", None), "age", 0),
        "can_play_poker": getattr(fish, "can_play_skill_games", False),
    }


def _nearest_vector(
    fish: Fish,
    agent_type: type,
    *,
    max_distance: float | None,
    use_resources: bool,
) -> dict[str, float]:
    environment = fish.environment
    fish_x = fish.pos.x
    fish_y = fish.pos.y

    if max_distance is not None:
        radius = int(max_distance) + 1
        if use_resources and hasattr(environment, "nearby_resources"):
            agents = environment.nearby_resources(fish, radius)
        else:
            agents = environment.nearby_agents_by_type(fish, radius, agent_type)
    else:
        agents = environment.get_agents_of_type(agent_type)

    if not agents:
        return {"x": 0.0, "y": 0.0}

    max_distance_sq = max_distance * max_distance if max_distance is not None else None
    nearest_dx = 0.0
    nearest_dy = 0.0
    nearest_dist_sq = float("inf")

    for agent in agents:
        dx = agent.pos.x - fish_x
        dy = agent.pos.y - fish_y
        dist_sq = dx * dx + dy * dy
        if max_distance_sq is not None and dist_sq > max_distance_sq:
            continue
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest_dx = dx
            nearest_dy = dy

    if nearest_dist_sq == float("inf"):
        return {"x": 0.0, "y": 0.0}

    return {"x": nearest_dx, "y": nearest_dy}
