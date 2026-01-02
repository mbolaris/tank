"""Petri-specific movement observation builder.

Petri world currently reuses tank logic, so this module just imports the
tank observation builder to ensure registration and then re-exports it.

The builder is registered automatically in the tank module for 'petri' world type.
"""

from __future__ import annotations

# Import tank module to trigger registration for both 'tank' and 'petri'
import core.worlds.tank.movement_observations as tank_obs  # noqa: F401

# Petri uses the same builder as tank (registered in tank module)
__all__ = ["tank_obs"]
