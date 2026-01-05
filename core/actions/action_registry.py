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
from typing import Any, Dict, Protocol

from core.brains.contracts import BrainAction

# Backward-compatibility alias
Action = BrainAction

logger = logging.getLogger(__name__)

# Type alias for action space descriptors
ActionSpace = Dict[str, Any]
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


# =============================================================================
# Default/Fallback Translator
# =============================================================================


class DefaultActionTranslator:
    """Default action translator for worlds without specific translators.

    Provides a basic pass-through translation that works for simple cases.
    """

    def get_action_space(self) -> ActionSpace:
        """Return a generic action space."""
        return {
            "movement": {
                "type": "continuous",
                "shape": (2,),
                "description": "Target velocity (vx, vy)",
            },
        }

    def translate_action(self, agent_id: str, raw_action: Any) -> Action:
        """Translate raw action to Action with best-effort parsing."""
        # Handle various input formats
        if isinstance(raw_action, Action):
            return raw_action

        if isinstance(raw_action, dict):
            target_velocity = raw_action.get("target_velocity", (0.0, 0.0))
            if isinstance(target_velocity, (list, tuple)) and len(target_velocity) >= 2:
                target_velocity = (float(target_velocity[0]), float(target_velocity[1]))
            else:
                target_velocity = (0.0, 0.0)

            return Action(
                entity_id=agent_id,
                target_velocity=target_velocity,
                extra=raw_action.get("extra", {}),
            )

        if isinstance(raw_action, (list, tuple)) and len(raw_action) >= 2:
            return Action(
                entity_id=agent_id,
                target_velocity=(float(raw_action[0]), float(raw_action[1])),
            )

        # Fallback: no movement
        return Action(entity_id=agent_id, target_velocity=(0.0, 0.0))


# Singleton default translator
_DEFAULT_TRANSLATOR = DefaultActionTranslator()


def get_action_space_or_default(world_type: str) -> ActionSpace:
    """Get action space, falling back to default if not registered.

    Args:
        world_type: World identifier

    Returns:
        Action space descriptor (never None)
    """
    space = get_action_space(world_type)
    if space is None:
        return _DEFAULT_TRANSLATOR.get_action_space()
    return space


def translate_action_or_default(
    world_type: str,
    agent_id: str,
    raw_action: Any,
) -> Action:
    """Translate action, falling back to default if not registered.

    Args:
        world_type: World identifier
        agent_id: The agent taking the action
        raw_action: Raw action data

    Returns:
        Action object (never raises for missing translator)
    """
    translator = get_action_translator(world_type)
    if translator is None:
        return _DEFAULT_TRANSLATOR.translate_action(agent_id, raw_action)
    return translator.translate_action(agent_id, raw_action)
