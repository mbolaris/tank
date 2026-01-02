"""Observation builder for Tank world.

This module constructs per-agent observations from the Tank world state.
Observations are used by brains (legacy or external) to make decisions.

Design Notes:
    - "Omniscient" mode: full visibility, no noise or FOV limits yet
    - Lightweight: avoids deep copies, uses references where safe
    - Deterministic: same world state produces same observations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.sim.contracts import Observation, ObservationMap

if TYPE_CHECKING:
    from core.entities import Fish
    from core.tank_world import TankWorld


# Perception radius for nearby entities (matches existing fish detection)
DEFAULT_PERCEPTION_RADIUS = 200.0


def build_tank_observations(
    world: "TankWorld",
    config: Optional[Dict[str, Any]] = None,
) -> ObservationMap:
    """Build per-agent observations from Tank world state.

    This is the "omniscient" observation builder - each fish sees the full
    world state without noise or FOV restrictions. Future implementations
    can add perception limits.

    Args:
        world: The TankWorld instance to observe
        config: Optional configuration (perception_radius, etc.)

    Returns:
        Dictionary mapping entity_id (as string) to Observation
    """
    if config is None:
        config = {}

    perception_radius = config.get("perception_radius", DEFAULT_PERCEPTION_RADIUS)
    observations: ObservationMap = {}

    # Get environment from TankWorld (uses world.environment property)
    env = world.environment
    frame = world.frame_count

    # Import Fish type for isinstance checks
    from core.entities import Fish, Food

    # Build observation for each fish
    for entity in world.entities_list:
        if not isinstance(entity, Fish):
            continue

        if entity.is_dead():
            continue

        fish_id = str(entity.fish_id)

        # Query nearby entities using spatial grid
        nearby_food = _build_food_observations(entity, env, perception_radius, Food)
        nearby_fish = _build_fish_observations(entity, env, perception_radius)
        nearby_threats = _build_threat_observations(entity, env, perception_radius)

        observations[fish_id] = Observation(
            entity_id=fish_id,
            position=(entity.pos.x, entity.pos.y),
            velocity=(entity.vel.x, entity.vel.y),
            energy=entity.energy,
            max_energy=entity.max_energy,
            age=entity._lifecycle_component.age,
            nearby_food=nearby_food,
            nearby_fish=nearby_fish,
            nearby_threats=nearby_threats,
            frame=frame,
            extra={
                "species": entity.species,
                "generation": entity.generation,
                "size": getattr(entity, "size", 1.0),
            },
        )

    return observations


def _build_food_observations(
    fish: "Fish",
    env: Any,
    radius: float,
    food_type: type,
) -> List[Dict[str, Any]]:
    """Build observations of nearby food items."""
    food_obs = []

    # Use spatial grid query for efficiency
    nearby = env.spatial_grid.query_food(fish, radius)

    for food in nearby:
        dx = food.pos.x - fish.pos.x
        dy = food.pos.y - fish.pos.y
        distance = (dx * dx + dy * dy) ** 0.5

        food_obs.append(
            {
                "x": food.pos.x,
                "y": food.pos.y,
                "energy": getattr(food, "energy_value", 10.0),
                "distance": distance,
                "dx": dx,
                "dy": dy,
            }
        )

    return food_obs


def _build_fish_observations(
    fish: "Fish",
    env: Any,
    radius: float,
) -> List[Dict[str, Any]]:
    """Build observations of nearby fish (non-threats)."""
    fish_obs = []

    # Use spatial grid query for efficiency
    nearby = env.spatial_grid.query_fish(fish, radius)

    for other in nearby:
        if other is fish:
            continue

        # Skip dead fish
        if other.is_dead():
            continue

        # Skip threats (will be in separate list)
        if _is_threat(fish, other):
            continue

        dx = other.pos.x - fish.pos.x
        dy = other.pos.y - fish.pos.y
        distance = (dx * dx + dy * dy) ** 0.5

        fish_obs.append(
            {
                "fish_id": other.fish_id,
                "x": other.pos.x,
                "y": other.pos.y,
                "vx": other.vel.x,
                "vy": other.vel.y,
                "energy": other.energy,
                "species": other.species,
                "distance": distance,
                "dx": dx,
                "dy": dy,
            }
        )

    return fish_obs


def _build_threat_observations(
    fish: "Fish",
    env: Any,
    radius: float,
) -> List[Dict[str, Any]]:
    """Build observations of nearby threats (larger fish)."""
    threat_obs = []

    # Use spatial grid query for efficiency
    nearby = env.spatial_grid.query_fish(fish, radius)

    for other in nearby:
        if other is fish:
            continue

        if other.is_dead():
            continue

        # Only include actual threats
        if not _is_threat(fish, other):
            continue

        dx = other.pos.x - fish.pos.x
        dy = other.pos.y - fish.pos.y
        distance = (dx * dx + dy * dy) ** 0.5

        threat_obs.append(
            {
                "fish_id": other.fish_id,
                "x": other.pos.x,
                "y": other.pos.y,
                "vx": other.vel.x,
                "vy": other.vel.y,
                "size": getattr(other, "size", 1.0),
                "distance": distance,
                "dx": dx,
                "dy": dy,
            }
        )

    return threat_obs


def _is_threat(fish: "Fish", other: "Fish") -> bool:
    """Check if another fish is a threat (larger = potential predator)."""
    # Use size comparison - larger fish are threats
    fish_size = getattr(fish, "size", 1.0)
    other_size = getattr(other, "size", 1.0)

    # Threat if significantly larger (same threshold as existing logic)
    return other_size > fish_size * 1.2
