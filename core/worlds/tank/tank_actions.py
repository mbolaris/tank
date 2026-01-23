"""Tank world action translator.

This module provides the Tank-specific action translator by using
the shared TankLikeActionTranslator.
"""

from __future__ import annotations

from core.actions.action_registry import register_action_translator
from core.worlds.shared.action_translator import TankLikeActionTranslator

# =============================================================================
# Registration
# =============================================================================


def register_tank_action_translator(world_type: str = "tank") -> None:
    """Register the Tank action translator for the specified world type."""
    translator = TankLikeActionTranslator()
    register_action_translator(world_type, translator)
