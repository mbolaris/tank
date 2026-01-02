"""Action module for world-agnostic action translation.

This module provides the ActionRegistry for translating raw actions
from external brains to domain-specific actions for each world type.
"""

from core.actions.action_registry import (
    ActionSpace,
    ActionTranslator,
    get_action_space,
    list_registered_translators,
    register_action_translator,
    translate_action,
)

__all__ = [
    "ActionSpace",
    "ActionTranslator",
    "register_action_translator",
    "get_action_space",
    "translate_action",
    "list_registered_translators",
]
