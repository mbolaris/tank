"""Tank world mode pack implementation.

This pack encapsulates the specific systems, environment, and entity seeding
logic for the standard fish tank simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.tank_like_pack_base import TankLikePackBase
from core.worlds.tank.movement_observations import register_tank_movement_observation_builder
from core.worlds.tank.tank_actions import register_tank_action_translator

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine
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

    def register_contracts(self, engine: SimulationEngine) -> None:
        """Register Tank-specific contracts."""
        register_tank_action_translator("tank")
        register_tank_movement_observation_builder("tank")

    def get_identity_provider(self) -> EntityIdentityProvider:
        """Return the Tank identity provider."""
        return self._identity_provider

    def get_metadata(self) -> dict[str, Any]:
        """Return Tank-specific metadata."""
        return {
            "world_type": "tank",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }
