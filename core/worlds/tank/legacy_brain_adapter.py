"""Legacy brain adapter for Tank world.

This module wraps the existing fish decision logic (movement_strategy.move)
to produce Action objects for the action pipeline. This preserves current
behavior exactly while enabling external brain integration.

Design Notes:
    - Does NOT change fish behavior - just captures the result as Action
    - Fish still use their movement_strategy.move() method internally
    - Actions are derived from the velocity changes the fish made
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from core.brains.contracts import BrainAction, BrainActionMap, BrainObservationMap

# Backward-compatibility aliases
Action = BrainAction
ActionMap = BrainActionMap
ObservationMap = BrainObservationMap

if TYPE_CHECKING:
    from core.entities import Fish
    from core.tank_world import TankWorld


def decide_actions(
    observations: ObservationMap,
    world: TankWorld,
    rng: random.Random | None = None,
) -> ActionMap:
    """Call existing fish decision path and translate to Actions.

    This adapter preserves current behavior by:
    1. Finding each fish entity from observation.entity_id
    2. Capturing their current velocity (already set by update cycle)
    3. Returning it as an Action

    In legacy mode, fish have already made their movement decisions during
    the entity update phase. This adapter just packages those decisions
    as Actions for pipeline consistency.

    Args:
        observations: Per-agent observations (used for entity lookup)
        world: The TankWorld instance
        rng: Optional random number generator (unused in legacy mode)

    Returns:
        Dictionary mapping entity_id to Action
    """
    actions: ActionMap = {}

    # Build fish lookup by ID for efficient access
    fish_by_id: dict[str, Fish] = {}
    from core.entities import Fish

    for entity in world.entities_list:
        if isinstance(entity, Fish) and not entity.is_dead():
            fish_by_id[str(entity.fish_id)] = entity

    # Create action for each observed fish
    for entity_id, obs in observations.items():
        fish = fish_by_id.get(entity_id)
        if fish is None:
            continue

        # In legacy mode, fish velocity is already set by movement_strategy.move()
        # We just capture it as an Action for pipeline consistency
        actions[entity_id] = Action(
            entity_id=entity_id,
            target_velocity=(fish.vel.x, fish.vel.y),
            extra={
                "source": "legacy",
                "movement_strategy": type(fish.movement_strategy).__name__,
            },
        )

    return actions


def apply_actions(
    actions: ActionMap,
    world: TankWorld,
) -> None:
    """Apply actions to fish entities.

    In external brain mode, this applies actions from an external decision maker.
    In legacy mode, this is effectively a no-op since fish already moved.

    Args:
        actions: Per-agent actions to apply
        world: The TankWorld instance
    """
    from core.entities import Fish

    # Build fish lookup
    fish_by_id: dict[str, Fish] = {}
    for entity in world.entities_list:
        if isinstance(entity, Fish) and not entity.is_dead():
            fish_by_id[str(entity.fish_id)] = entity

    # Apply each action
    for entity_id, action in actions.items():
        fish = fish_by_id.get(entity_id)
        if fish is None:
            continue

        # Skip legacy actions (fish already moved)
        if action.extra.get("source") == "legacy":
            continue

        # Apply external brain velocity
        vx, vy = action.target_velocity
        fish.vel.x = vx
        fish.vel.y = vy
