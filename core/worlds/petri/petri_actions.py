"""Petri world action translator registration.

Uses the shared FishActionTranslator for Petri world.
"""

from core.actions.action_registry import register_action_translator
from core.worlds.shared.action_translator import FishActionTranslator


def register_petri_action_translator(world_type: str = "petri") -> None:
    """Register the Petri action translator."""
    translator = FishActionTranslator()
    register_action_translator(world_type, translator)
