"""Petri world mode pack implementation.

This pack provides the Petri Dish simulation mode, which reuses
Tank-like simulation logic with mode-specific metadata for top-down
microbe visualization.

ARCHITECTURE NOTE: PetriPack inherits from the neutral TankLikePackBase
rather than TankPack. This clean boundary enables Petri to diverge
independently without creating tangled import chains through Tank.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.tank_like_pack_base import TankLikePackBase

if TYPE_CHECKING:
    from core.worlds.identity import EntityIdentityProvider


class PetriPack(TankLikePackBase):
    """System pack for the Petri Dish simulation.

    Inherits shared Tank-like wiring from TankLikePackBase and provides
    Petri-specific mode_id, metadata, and identity provider.

    Currently uses the same entity types and identity scheme as Tank,
    but can diverge independently for Petri-specific features.
    """

    def __init__(self, config: SimulationConfig):
        super().__init__(config)
        # Use shared Tank-like identity provider from shared namespace
        self._identity_provider = TankLikeEntityIdentityProvider()

    @property
    def mode_id(self) -> str:
        return "petri"

    def get_identity_provider(self) -> "EntityIdentityProvider":
        """Return the Petri identity provider."""
        return self._identity_provider

    def get_metadata(self) -> dict[str, Any]:
        """Return Petri-specific metadata."""
        return {
            "world_type": "petri",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }
