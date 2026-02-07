"""Backwards-compatible re-exports from core.interfaces.

All protocol definitions have been consolidated into core.interfaces as the
single source of truth. This module re-exports the entity capability protocols
that were originally defined here to avoid breaking existing imports.

Prefer importing from core.interfaces directly in new code:
    from core.interfaces import EnergyHolder, Movable, Mortal
"""

from core.interfaces import (Consumable, EnergyHolder, Identifiable,
                             LifecycleAware, Mortal, Movable, Predator,
                             Reproducible, SkillGamePlayer)

__all__ = [
    "Consumable",
    "EnergyHolder",
    "Identifiable",
    "LifecycleAware",
    "Mortal",
    "Movable",
    "Predator",
    "Reproducible",
    "SkillGamePlayer",
]
