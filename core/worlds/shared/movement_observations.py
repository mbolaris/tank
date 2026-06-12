"""Shared movement observation builder for fish-based worlds.

This module contains the shared logic for building movement policy observations
that works for any world with fish-like agents (Tank, Petri, etc.).

Entity types (Food, Crab) are passed as parameters rather than being imported
directly, keeping this module world-agnostic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.food import BASE_FOOD_DETECTION_RANGE

if TYPE_CHECKING:
    from core.entities import Fish


Observation = dict[str, Any]

# Quality-weighted food targeting weights, ported from the
# food_quality_optimizer monolith (ADR-006): targets are scored as
#   quality * FOOD_QUALITY_WEIGHT - distance * FOOD_DISTANCE_WEIGHT
# so fish trade extra travel for higher-energy food. Values are the midpoints
# of the monolith's evolved parameter ranges (quality 0.5-1.0, distance
# 0.3-0.7 in ALGORITHM_PARAMETER_BOUNDS).
#
# These live here, not in core/config: champion comparisons are only valid
# across identical config (core/solutions/config_hash.py snapshots core.config
# constants), and these weights are algorithm-internal tuning that evolves
# WITH the code - exactly what champion scores are meant to measure.
FOOD_QUALITY_WEIGHT = 0.75
FOOD_DISTANCE_WEIGHT = 0.5
# Hungry fish value a bigger meal more; starving fish penalize distance more
# (cannot afford long chases). Same modifiers as the monolith.
FOOD_QUALITY_WEIGHT_LOW_ENERGY_BOOST = 1.5
FOOD_DISTANCE_WEIGHT_CRITICAL_BOOST = 1.3


class TankLikeMovementObservationBuilder:
    """Observation builder for tank-like world movement policies.

    This is the shared implementation used by Tank, Petri, and other kinematic
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
        food_type: type | None = None,
        threat_type: type | None = None,
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
            _best_food_vector(fish, self.food_type, max_distance=max_food_distance)
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
            # NOTE: despite the historical name, this is the vector to the
            # fish's best food *target*: quality-weighted scoring (ADR-006
            # food_quality_optimizer port), not necessarily the nearest item.
            "nearest_food_vector": nearest_food_vector,
            "nearest_threat_vector": nearest_threat_vector,
            "energy": fish.energy,
            "age": fish.age or 0,
            "can_play_poker": getattr(fish, "can_play_skill_games", False),
        }


def _best_food_vector(
    fish: Fish,
    food_type: type,
    *,
    max_distance: float,
) -> dict[str, float]:
    """Pick a food target using quality-weighted scoring and return vector to it.

    Ported from the food_quality_optimizer monolith (ADR-006, the only
    food-seeking algorithm that beat the production baseline on every
    benchmark seed): each detectable food item is scored as

        score = quality * FOOD_QUALITY_WEIGHT - distance * FOOD_DISTANCE_WEIGHT

    where quality is the food's current energy value. Hungry fish weight
    quality higher (a bigger meal matters more) and starving fish weight
    distance higher (they cannot afford long chases). Items without an energy
    value (exotic worlds) score quality 0, which degenerates to nearest-food
    selection - the pre-port behavior.

    Deterministic: consumes no RNG; ties resolve to the first item in the
    spatial query's stable iteration order.

    Args:
        fish: The fish looking for food
        food_type: Entity type to search for when no resource query exists
        max_distance: Maximum search distance (detection range)

    Returns:
        Vector {x, y} from fish to the chosen food, or {0, 0} if none found
    """
    import math

    environment = fish.environment

    if hasattr(environment, "nearby_resources"):
        agents = environment.nearby_resources(fish, max_distance)
    else:
        agents = environment.nearby_agents_by_type(fish, max_distance, food_type)

    if not agents:
        return {"x": 0.0, "y": 0.0}

    quality_weight = FOOD_QUALITY_WEIGHT
    distance_weight = FOOD_DISTANCE_WEIGHT

    # Energy-state modifiers (same shape as the monolith's): duck-typed so
    # non-fish agents in exotic worlds simply use the base weights.
    is_low = getattr(fish, "is_low_energy", lambda: False)()
    is_critical = getattr(fish, "is_critical_energy", lambda: False)()
    if is_low:
        quality_weight *= FOOD_QUALITY_WEIGHT_LOW_ENERGY_BOOST
    if is_critical:
        distance_weight *= FOOD_DISTANCE_WEIGHT_CRITICAL_BOOST

    fish_x = fish.pos.x
    fish_y = fish.pos.y
    max_distance_sq = max_distance * max_distance

    best_dx = 0.0
    best_dy = 0.0
    best_score = -float("inf")
    found = False

    for agent in agents:
        dx = agent.pos.x - fish_x
        dy = agent.pos.y - fish_y
        dist_sq = dx * dx + dy * dy
        if dist_sq > max_distance_sq:
            continue
        get_quality = getattr(agent, "get_energy_value", None)
        quality = float(get_quality()) if get_quality is not None else 0.0
        score = quality * quality_weight - math.sqrt(dist_sq) * distance_weight
        if score > best_score:
            best_score = score
            best_dx = dx
            best_dy = dy
            found = True

    if not found:
        return {"x": 0.0, "y": 0.0}

    return {"x": best_dx, "y": best_dy}


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

        # Optimization: use specialized fish search if available
        # This name check is intentional for the optimization path; the generic
        # fallback at line 143+ handles all cases if this doesn't match.
        if (
            not use_resources
            and getattr(agent_type, "__name__", None) == "Fish"
            and hasattr(environment, "closest_fish")
        ):
            agent = environment.closest_fish(fish, radius)
            if agent:
                dx = agent.pos.x - fish.pos.x
                dy = agent.pos.y - fish.pos.y
                return {"x": dx, "y": dy}
            return {"x": 0.0, "y": 0.0}

    if max_distance is not None:
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
