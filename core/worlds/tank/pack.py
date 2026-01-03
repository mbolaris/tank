"""Tank world mode pack implementation.

This pack encapsulates the specific systems, environment, and entity seeding
logic for the standard fish tank simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.tank_like_pack_base import TankLikePackBase

if TYPE_CHECKING:
    from core.worlds.identity import EntityIdentityProvider


class TankPack(TankLikePackBase):
    """System pack for the standard Fish Tank simulation.

    Inherits shared Tank-like wiring from TankLikePackBase and provides
    Tank-specific mode_id, metadata, and identity provider.
    """

    def __init__(self, config: SimulationConfig):
        super().__init__(config)
        self._identity_provider = TankLikeEntityIdentityProvider()

    @property
    def mode_id(self) -> str:
        return "tank"

    def get_identity_provider(self) -> "EntityIdentityProvider":
        """Return the Tank identity provider."""
        return self._identity_provider

    def get_metadata(self) -> dict[str, Any]:
        """Return Tank-specific metadata."""
        return {
            "world_type": "tank",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }
