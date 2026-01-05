"""Alias for Tank phase hooks.

The canonical implementation now lives in core.worlds.shared.fish_plant_phase_hooks.
This module re-exports for existing code.
"""

from core.worlds.shared.fish_plant_phase_hooks import (
    FishPlantPhaseHooks,
    TankPhaseHooks,
)

__all__ = ["FishPlantPhaseHooks", "TankPhaseHooks"]
