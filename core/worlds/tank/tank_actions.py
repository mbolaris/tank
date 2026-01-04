"""Tank world action translator.

This module provides the Tank-specific action translator by using
the shared FishActionTranslator.

For backward compatibility, TankActionTranslator is exported as
an alias to the shared implementation.
"""

from __future__ import annotations

from core.actions.action_registry import register_action_translator
from core.worlds.shared.action_translator import FishActionTranslator


# Alias for backward compatibility
TankActionTranslator = FishActionTranslator


# =============================================================================
# Registration
# =============================================================================


def register_tank_action_translator(world_type: str = "tank") -> None:
    """Register the Tank action translator for the specified world type."""
    translator = TankActionTranslator()
    register_action_translator(world_type, translator)
