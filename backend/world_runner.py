"""Generic world runner that drives any WorldBackend implementation.

This module provides a world-agnostic runner that:
- Owns episode lifecycle (setup, step, reset)
- Uses a SnapshotBuilder to produce frontend payloads
- Does NOT import world-specific types directly

Usage:
    from backend.world_registry import create_world
    from backend.world_runner import WorldRunner

    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    # Step the simulation
    runner.step()

    # Get entity snapshots for frontend
    snapshots = runner.get_entities_snapshot()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.interfaces import WorldBackend
    from backend.snapshots.interfaces import SnapshotBuilder
    from backend.state_payloads import EntitySnapshot

logger = logging.getLogger(__name__)


class WorldRunner:
    """Generic world runner that drives any WorldBackend implementation.

    This class provides a world-agnostic interface for running simulations.
    It delegates entity snapshot building to a SnapshotBuilder, allowing
    each world type to define its own serialization logic.

    Attributes:
        world: The underlying world backend
        snapshot_builder: Converts entities to frontend snapshots
        world_type: String identifier for the world type
        view_mode: Default view mode for frontend ("side", "top", etc.)
    """

    def __init__(
        self,
        world: "WorldBackend",
        snapshot_builder: "SnapshotBuilder",
        world_type: str = "tank",
        view_mode: str = "side",
    ) -> None:
        """Initialize the world runner.

        Args:
            world: The world backend to drive
            snapshot_builder: Snapshot builder for entity serialization
            world_type: Type identifier (e.g., "tank", "petri", "soccer")
            view_mode: Default view mode for frontend rendering
        """
        self.world = world
        self.snapshot_builder = snapshot_builder
        self.world_type = world_type
        self.view_mode = view_mode

    @property
    def frame_count(self) -> int:
        """Current frame count from the world."""
        return self.world.frame_count

    @property
    def paused(self) -> bool:
        """Whether the world is paused."""
        return self.world.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the world's paused state."""
        self.world.paused = value

    @property
    def entities_list(self) -> List[Any]:
        """Get all entities from the world."""
        return self.world.entities_list

    def setup(self) -> None:
        """Initialize the world.

        Note: Most worlds are already set up by the factory.
        This is here for explicit re-initialization if needed.
        """
        self.world.setup()

    def step(self) -> None:
        """Advance the world by one frame/step."""
        self.world.update()

    def reset(self) -> None:
        """Reset the world to initial state."""
        self.world.reset()

    def get_stats(self) -> Dict[str, Any]:
        """Get current world statistics."""
        return self.world.get_stats()

    def get_entities_snapshot(self) -> List["EntitySnapshot"]:
        """Build entity snapshots for frontend rendering.

        Returns:
            List of EntitySnapshot DTOs sorted by z-order
        """
        return self.snapshot_builder.collect(self.world.entities_list)

    def get_world_info(self) -> Dict[str, str]:
        """Get world metadata for frontend.

        Returns:
            Dictionary with world_type and view_mode
        """
        return {
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }
