"""Action registry for world-agnostic action translation.

This module provides a registry pattern for translating raw actions
from external brains to domain-specific actions for each world type.
It mirrors the ObservationRegistry pattern for consistency.

Usage:
    # In world-specific module (e.g., core/worlds/tank/tank_actions.py):
    from core.actions.action_registry import register_action_translator

    class TankActionTranslator:
        def get_action_space(self) -> ActionSpace:
            return {"movement": {"type": "continuous", "shape": (2,)}}

        def translate_action(self, agent_id: str, raw_action: Any) -> Action:
            return Action(entity_id=agent_id, target_velocity=raw_action["velocity"])

    register_action_translator("tank", TankActionTranslator())

    # In policy code:
    from core.actions.action_registry import get_action_space, translate_action

    space = get_action_space("tank")
    action = translate_action("tank", fish_id, raw_action)
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from core.brains.contracts import BrainAction

# Backward-compatibility alias
Action = BrainAction

logger = logging.getLogger(__name__)

# Type alias for action space descriptors
ActionSpace = dict[str, Any]
"""Describes valid actions for a world type.

Example:
    {
        "movement": {
            "type": "continuous",
            "shape": (2,),
            "low": (-5.0, -5.0),
            "high": (5.0, 5.0),
        },
        "interact": {
            "type": "discrete",
            "n": 3,
            "labels": ["none", "eat", "poker"],
        },
    }
"""


class ActionTranslator(Protocol):
    """Protocol for world-specific action translators.

    Each world implements this protocol to define its action space
    and translate raw actions from external brains to domain actions.
    """

    def get_action_space(self) -> ActionSpace:
        """Get the action space descriptor for this world type.

        Returns:
            Dictionary describing valid actions and their constraints
        """
        ...

    def translate_action(self, agent_id: str, raw_action: Any) -> Action:
        """Translate a raw action to a domain Action.

        Args:
            agent_id: The agent taking the action
            raw_action: Raw action data from external brain

        Returns:
            Action object for the simulation pipeline
        """
        ...


# Registry storage: {world_type: translator}
_ACTION_TRANSLATORS: dict[str, ActionTranslator] = {}


def register_action_translator(
    world_type: str,
    translator: ActionTranslator,
) -> None:
    """Register an action translator for a world type.

    Args:
        world_type: World identifier (e.g., "tank", "petri", "soccer")
        translator: ActionTranslator instance
    """
    existing = _ACTION_TRANSLATORS.get(world_type)
    if existing is not None:
        # Skip if same translator type is already registered (idempotent)
        if type(existing).__name__ == type(translator).__name__:
            return
        logger.warning("Overwriting action translator for world_type='%s'", world_type)
    _ACTION_TRANSLATORS[world_type] = translator


def get_action_translator(world_type: str) -> ActionTranslator | None:
    """Get a registered action translator.

    Args:
        world_type: World identifier

    Returns:
        Registered translator or None if not found
    """
    return _ACTION_TRANSLATORS.get(world_type)


def get_action_space(world_type: str) -> ActionSpace | None:
    """Get the action space for a world type.

    Args:
        world_type: World identifier

    Returns:
        Action space descriptor or None if no translator registered
    """
    translator = get_action_translator(world_type)
    if translator is None:
        return None
    return translator.get_action_space()


def translate_action(
    world_type: str,
    agent_id: str,
    raw_action: Any,
) -> Action:
    """Translate a raw action using the registered translator.

    Args:
        world_type: World identifier (e.g., "tank", "petri", "soccer")
        agent_id: The agent taking the action
        raw_action: Raw action data from external brain

    Returns:
        Action object for the simulation pipeline

    Raises:
        ValueError: If no translator is registered for the world_type
    """
    translator = get_action_translator(world_type)
    if translator is None:
        raise ValueError(
            f"No action translator registered for world_type='{world_type}'. "
            f"Available: {list(_ACTION_TRANSLATORS.keys())}"
        )
    return translator.translate_action(agent_id, raw_action)


def list_registered_translators() -> list[str]:
    """List all registered world types with action translators.

    Returns:
        List of world type identifiers
    """
    return list(_ACTION_TRANSLATORS.keys())
