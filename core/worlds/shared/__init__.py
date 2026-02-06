"""Shared infrastructure for Tank-like world modes.

This module contains shared base classes and utilities used by multiple
world modes (Tank, Petri) that share similar simulation mechanics.
"""

from core.worlds.shared.action_translator import TankLikeActionTranslator
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.movement_observations import TankLikeMovementObservationBuilder
from core.worlds.shared.tank_like_pack_base import TankLikePackBase
from core.worlds.shared.tank_like_phase_hooks import TankLikePhaseHooks, TankPhaseHooks

__all__ = [
    "TankLikeActionTranslator",
    "TankLikeEntityIdentityProvider",
    "TankLikeMovementObservationBuilder",
    "TankLikePackBase",
    "TankLikePhaseHooks",
    "TankPhaseHooks",
]
