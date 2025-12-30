"""Generic world runner that drives any MultiAgentWorldBackend implementation.

This module provides a world-agnostic runner that:
- Owns episode lifecycle (reset, step)
- Uses StepResult as the primary data flow
- Uses a SnapshotBuilder to produce frontend payloads
- Does NOT import world-specific types directly

Usage:
    from backend.world_registry import create_world
    from backend.world_runner import WorldRunner

    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    # Reset the world
    result = runner.reset(seed=42)

    # Step the simulation
    runner.step()

    # Get entity snapshots for frontend
    snapshots = runner.get_entities_snapshot()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.worlds.interfaces import MultiAgentWorldBackend, StepResult
    from backend.snapshots.interfaces import SnapshotBuilder
    from backend.state_payloads import EntitySnapshot

logger = logging.getLogger(__name__)


class WorldRunner:
    """Generic world runner that drives any MultiAgentWorldBackend implementation.

    This class provides a world-agnostic interface for running simulations.
    It delegates entity snapshot building to a SnapshotBuilder, allowing
    each world type to define its own serialization logic.

    The runner uses StepResult as the primary data flow:
    - reset() calls world.reset() and stores the returned StepResult
    - step() calls world.step() and stores the returned StepResult
    - get_entities_snapshot() uses the snapshot builder's build() method

    Attributes:
        world: The underlying world backend (MultiAgentWorldBackend)
        snapshot_builder: Converts entities to frontend snapshots
        world_type: String identifier for the world type
        view_mode: Default view mode for frontend ("side", "top", etc.)
    """

    def __init__(
        self,
        world: "MultiAgentWorldBackend",
        snapshot_builder: "SnapshotBuilder",
        world_type: str = "tank",
        view_mode: str = "side",
    ) -> None:
        """Initialize the world runner.

        Args:
            world: The MultiAgentWorldBackend to drive
            snapshot_builder: Snapshot builder for entity serialization
            world_type: Type identifier (e.g., "tank", "petri", "soccer")
            view_mode: Default view mode for frontend rendering
        """
        self.world = world
        self.snapshot_builder = snapshot_builder
        self.world_type = world_type
        self.view_mode = view_mode
        self._last_step_result: Optional["StepResult"] = None

    @property
    def frame_count(self) -> int:
        """Current frame count from the last StepResult."""
        if self._last_step_result is not None:
            return self._last_step_result.info.get("frame", 0)
        return 0

    @property
    def paused(self) -> bool:
        """Whether the world is paused."""
        if self._last_step_result is not None:
            return self._last_step_result.snapshot.get("paused", False)
        return False

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the world's paused state.
        
        Note: This currently accesses the underlying world directly.
        Future versions may use actions_by_agent to control pause state.
        """
        # Access underlying world for pause control (temporary bridge)
        if hasattr(self.world, "world") and self.world.world is not None:
            self.world.world.paused = value
        elif hasattr(self.world, "paused"):
            self.world.paused = value

    @property
    def entities_list(self) -> List[Any]:
        """Get all entities from the world.
        
        Note: This is a compatibility bridge. Prefer using get_entities_snapshot()
        which goes through the StepResult-driven build() method.
        """
        # Access underlying world for entities (temporary bridge)
        if hasattr(self.world, "world") and self.world.world is not None:
            return self.world.world.entities_list
        elif hasattr(self.world, "entities_list"):
            return self.world.entities_list
        return []

    def reset(
        self,
        seed: Optional[int] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> "StepResult":
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            scenario: World-specific configuration

        Returns:
            StepResult with initial observations, snapshot, and metrics
        """
        self._last_step_result = self.world.reset(seed, scenario)
        return self._last_step_result

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> None:
        """Advance the world by one frame/step.

        Args:
            actions_by_agent: Actions for each agent (agent_id -> action).
                             May be None/empty for autonomous worlds like Tank.
        """
        self._last_step_result = self.world.step(actions_by_agent)

    def setup(self) -> None:
        """Initialize the world.

        This is a convenience method that calls reset() with no arguments.
        Prefer using reset(seed=...) for explicit initialization.
        """
        self.reset()

    def get_stats(self) -> Dict[str, Any]:
        """Get current world statistics."""
        if self._last_step_result is not None:
            return self._last_step_result.metrics
        return self.world.get_current_metrics()

    def get_entities_snapshot(self) -> List["EntitySnapshot"]:
        """Build entity snapshots for frontend rendering.

        Uses the snapshot builder's build() method with the last StepResult.
        Falls back to collect() if no StepResult is available yet.

        Returns:
            List of EntitySnapshot DTOs sorted by z-order
        """
        if self._last_step_result is not None:
            return self.snapshot_builder.build(self._last_step_result, self.world)
        # Fallback for compatibility (before first reset/step)
        return self.snapshot_builder.collect(self.entities_list)

    def get_world_info(self) -> Dict[str, str]:
        """Get world metadata for frontend.

        Returns:
            Dictionary with world_type and view_mode
        """
        return {
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }

    @property
    def last_step_result(self) -> Optional["StepResult"]:
        """Get the last StepResult from reset() or step().
        
        Returns:
            The most recent StepResult, or None if never reset/stepped
        """
        return self._last_step_result
