"""Petri world action translator registration.

Allows Petri mode to register contracts without importing Tank wiring directly.
"""
from core.worlds.tank.tank_actions import TankActionTranslator
from core.actions.action_registry import register_action_translator

def register_petri_action_translator(world_type: str = "petri") -> None:
    """Register the Petri action translator."""
    # Petri reuses Tank actions for now
    translator = TankActionTranslator()
    register_action_translator(world_type, translator)
