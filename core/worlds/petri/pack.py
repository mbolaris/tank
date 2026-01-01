"""Petri world mode pack implementation.

This pack reuses the Tank simulation logic but identifies as 'petri'.
"""

from __future__ import annotations

from typing import Any, Dict

from core.worlds.tank.pack import TankPack


class PetriPack(TankPack):
    """System pack for the Petri Dish simulation."""

    @property
    def mode_id(self) -> str:
        return "petri"

    def get_metadata(self) -> Dict[str, Any]:
        """Return Petri-specific metadata."""
        metadata = super().get_metadata()
        metadata["world_type"] = "petri"
        return metadata
