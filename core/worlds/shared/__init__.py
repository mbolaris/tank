"""Shared infrastructure for Tank-like world modes.

This module contains shared base classes and utilities used by multiple
world modes (Tank, Petri) that share similar simulation mechanics.
"""

from core.worlds.shared.action_translator import FishActionTranslator
from core.worlds.shared.fish_plant_phase_hooks import (
    FishPlantPhaseHooks,
    TankPhaseHooks,
)
from core.worlds.shared.identity import (
    TankEntityIdentityProvider,
    TankLikeEntityIdentityProvider,
)
from core.worlds.shared.movement_observations import (
    FishMovementObservationBuilder,
    create_tank_observation_builder,
)
from core.worlds.shared.tank_like_pack_base import TankLikePackBase

__all__ = [
    "FishActionTranslator",
    "FishMovementObservationBuilder",
    "FishPlantPhaseHooks",
    "TankEntityIdentityProvider",
    "TankLikeEntityIdentityProvider",
    "TankLikePackBase",
    "TankPhaseHooks",
    "create_tank_observation_builder",
]
