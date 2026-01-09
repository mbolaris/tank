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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.snapshots.interfaces import SnapshotBuilder
    from backend.state_payloads import EntitySnapshot
    from core.worlds.interfaces import MultiAgentWorldBackend, StepResult

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
        world: MultiAgentWorldBackend,
        snapshot_builder: SnapshotBuilder,
        world_type: str = "tank",
        mode_id: str | None = None,
        view_mode: str = "side",
    ) -> None:
        """Initialize the world runner.

        Args:
            world: The MultiAgentWorldBackend to drive
            snapshot_builder: Snapshot builder for entity serialization
            world_type: Type identifier (e.g., "tank", "petri")
            view_mode: Default view mode for frontend rendering
        """
        self.world = world
        self.snapshot_builder = snapshot_builder
        self.world_type = world_type
        self.world_id = "default"  # Default world ID for generic runners
        self.running = False
        self.mode_id = mode_id or world_type
        self.view_mode = view_mode
        self._last_step_result: StepResult | None = None

    @property
    def frame_count(self) -> int:
        """Current frame count from the last StepResult."""
        if self._last_step_result is not None:
            return self._last_step_result.info.get("frame", 0)
        return 0

    @property
    def paused(self) -> bool:
        """Whether the world is paused.

        Uses the protocol's is_paused property for world-agnostic access.
        """
        return self.world.is_paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the world's paused state.

        Uses the protocol's set_paused method for world-agnostic access.
        """
        self.world.set_paused(value)

    @property
    def fast_forward(self) -> bool:
        """Fast forward is not applicable for step-based worlds."""
        return False

    @fast_forward.setter
    def fast_forward(self, value: bool) -> None:
        """No-op for step-based worlds."""
        pass

    @property
    def entities_list(self) -> list[Any]:
        """Get all entities from the world.

        Uses the protocol's get_entities_for_snapshot method.
        Prefer using get_entities_snapshot() for frontend rendering.
        """
        return self.world.get_entities_for_snapshot()

    def reset(
        self,
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> StepResult:
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            config: World-specific configuration

        Returns:
            StepResult with initial observations, snapshot, and metrics
        """
        self._last_step_result = self.world.reset(seed, config)
        return self._last_step_result

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
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

    def get_stats(self) -> dict[str, Any]:
        """Get current world statistics."""
        if self._last_step_result is not None:
            return self._last_step_result.metrics
        return self.world.get_current_metrics()

    def get_entities_snapshot(self) -> list[EntitySnapshot]:
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

    def get_world_info(self) -> dict[str, str]:
        """Get world metadata for frontend.

        Returns:
            Dictionary with mode_id, world_type, and view_mode
        """
        mode_id = getattr(self, "mode_id", self.world_type)
        return {
            "mode_id": mode_id,
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }

    @property
    def last_step_result(self) -> StepResult | None:
        """Get the last StepResult from reset() or step().

        Returns:
            The most recent StepResult, or None if never reset/stepped
        """
        return self._last_step_result

    def get_state(self, force_full: bool = False, allow_delta: bool = True) -> Any:
        """Get current simulation state for WebSocket broadcast.

        Simple implementation for generic runners that returns a full update.
        """
        from backend.state_payloads import FullStatePayload, StatsPayload

        frame = self.frame_count
        # Simplified stats for generic world types
        metrics = self.get_stats()

        # Build StatsPayload from metrics dict
        # We fill only common fields, others get defaults
        stats = StatsPayload(
            frame=frame,
            population=metrics.get("population", 0),
            generation=metrics.get("generation", 0),
            max_generation=metrics.get("max_generation", 0),
            births=metrics.get("births", 0),
            deaths=metrics.get("deaths", 0),
            capacity=metrics.get("capacity", "0%"),
            time=metrics.get("time", "00:00"),
            death_causes=metrics.get("death_causes", {}),
            fish_count=metrics.get("fish_count", metrics.get("population", 0)),
            food_count=metrics.get("food_count", 0),
            plant_count=metrics.get("plant_count", 0),
            total_energy=metrics.get("total_energy", 0.0),
            food_energy=metrics.get("food_energy", 0.0),
            live_food_count=metrics.get("live_food_count", 0),
            live_food_energy=metrics.get("live_food_energy", 0.0),
            fish_energy=metrics.get("fish_energy", 0.0),
            plant_energy=metrics.get("plant_energy", 0.0),
        )

        return FullStatePayload(
            frame=frame,
            elapsed_time=int(frame * 33),  # Placeholder
            entities=self.get_entities_snapshot(),
            stats=stats,
            poker_events=[],
            poker_leaderboard=[],
            world_id=self.world_id,
            mode_id=self.mode_id,
            world_type=self.world_type,
            view_mode=self.view_mode,
        )

    def switch_world_type(self, new_world_type: str) -> None:
        """Switch to a different world type.

        Not supported for generic WorldRunner - only SimulationRunner
        supports hot-swapping between tank and petri modes.

        Args:
            new_world_type: Target world type

        Raises:
            ValueError: Always, as switching is not supported
        """
        raise ValueError(f"World type switching not supported for {self.world_type} worlds")

    def get_evolution_benchmark_data(self) -> dict[str, Any]:
        """Get evolution benchmark data for this world instance.

        Generic worlds typically don't track evolution benchmarks yet.

        Returns:
            Dictionary with benchmark history and metrics (empty for generic runner)
        """
        return {}
