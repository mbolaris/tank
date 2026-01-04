"""Shared movement observation builder for fish-based worlds.

This module contains the shared logic for building movement policy observations
that works for any world with fish-like agents (Tank, Petri, etc.).

Entity types (Food, Crab) are passed as parameters rather than being imported
directly, keeping this module world-agnostic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Type

from core.config.food import BASE_FOOD_DETECTION_RANGE
from core.policies.observation_registry import register_observation_builder

if TYPE_CHECKING:
    from core.entities import Fish

Observation = Dict[str, Any]


class FishMovementObservationBuilder:
    """Observation builder for fish-based world movement policies.

    This is the shared implementation used by Tank, Petri, and other fish-based
    worlds. The entity types (food_type, threat_type) are passed during construction
    to avoid hard-coding Tank-specific imports.

    Builds observations containing:
    - position: {x, y}
    - velocity: {x, y}
    - nearest_food_vector: {x, y} relative to agent
    - nearest_threat_vector: {x, y} relative to agent
    - energy: current energy level
    - age: agent age in frames
    - can_play_poker: whether agent can engage in poker
    """

    def __init__(
        self,
        food_type: Type | None = None,
        threat_type: Type | None = None,
        threat_detection_range: float = 200.0,
    ) -> None:
        """Initialize the observation builder.

        Args:
            food_type: Entity type to search for as food (e.g., Food class)
            threat_type: Entity type to search for as threats (e.g., Crab class)
            threat_detection_range: Maximum range to detect threats
        """
        self.food_type = food_type
        self.threat_type = threat_type
        self.threat_detection_range = threat_detection_range

    def build(self, agent: Any, env: Any) -> Observation:
        """Build movement observation for the given fish."""
        fish: Fish = agent
        environment = env

        detection_modifier = getattr(environment, "get_detection_modifier", lambda: 1.0)()
        max_food_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier

        nearest_food_vector = (
            _nearest_vector(
                fish, self.food_type, max_distance=max_food_distance, use_resources=True
            )
            if self.food_type is not None
            else {"x": 0.0, "y": 0.0}
        )
        nearest_threat_vector = (
            _nearest_vector(
                fish,
                self.threat_type,
                max_distance=self.threat_detection_range,
                use_resources=False,
            )
            if self.threat_type is not None
            else {"x": 0.0, "y": 0.0}
        )

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
    """Find the nearest entity of the given type and return vector to it.

    Args:
        fish: The fish looking for entities
        agent_type: Type to search for (Food, Crab, etc.)
        max_distance: Maximum search distance (None for unlimited)
        use_resources: If True, use optimized resource query

    Returns:
        Vector {x, y} from fish to nearest entity, or {0, 0} if none found
    """
    environment = fish.environment
    fish_x = fish.pos.x
    fish_y = fish.pos.y

    # OPTIMIZATION: Use specialized closest_agent search if available
    # Only use if max_distance is set (spatial query requires finite radius)
    if max_distance is not None:
        radius = max_distance

        if use_resources and hasattr(environment, "closest_food"):
            agent = environment.closest_food(fish, radius)
            if agent:
                dx = agent.pos.x - fish.pos.x
                dy = agent.pos.y - fish.pos.y
                return {"x": dx, "y": dy}
            return {"x": 0.0, "y": 0.0}

        if (
            not use_resources
            and agent_type.__name__ == "Fish"
            and hasattr(environment, "closest_fish")
        ):
            agent = environment.closest_fish(fish, radius)
            if agent:
                dx = agent.pos.x - fish.pos.x
                dy = agent.pos.y - fish.pos.y
                return {"x": dx, "y": dy}
            return {"x": 0.0, "y": 0.0}

    if max_distance is not None:
        grid_radius = int(max_distance) + 1
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


# =============================================================================
# Factory function for common configurations
# =============================================================================


def create_tank_observation_builder() -> FishMovementObservationBuilder:
    """Create observation builder configured for Tank/Petri worlds.

    This factory imports Tank-specific entity types and creates a properly
    configured builder instance.
    """
    from core.entities import Crab, Food

    return FishMovementObservationBuilder(
        food_type=Food,
        threat_type=Crab,
        threat_detection_range=200.0,
    )
