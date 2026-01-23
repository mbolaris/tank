"""Petri world action translator registration.

Uses the shared TankLikeActionTranslator for Petri world.
"""

from core.actions.action_registry import register_action_translator
from core.worlds.shared.action_translator import TankLikeActionTranslator


def register_petri_action_translator(world_type: str = "petri") -> None:
    """Register the Petri action translator."""
    translator = TankLikeActionTranslator()
    register_action_translator(world_type, translator)
