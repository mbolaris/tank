"""Runner protocol for unified world execution interface.

This module defines the RunnerProtocol that both WorldRunner and SimulationRunner
satisfy. This enables backend systems (broadcast, WorldManager) to work with
any runner type through a single interface without unions or special casing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from backend.state_payloads import DeltaStatePayload, EntitySnapshot, FullStatePayload


@runtime_checkable
class RunnerProtocol(Protocol):
    """Protocol for world runners (WorldRunner, SimulationRunner).

    This protocol defines the interface that broadcast/state building code
    needs from any runner. Both WorldRunner and SimulationRunner satisfy
    this protocol, enabling unified handling without type unions.

    Properties:
        world_id: Unique identifier for this world instance
        running: Whether the simulation is currently running (readable and writable)
        world_type: Type of world (tank, petri, etc.)
        mode_id: Mode identifier for UI display
        view_mode: Default view mode (side, topdown)
        frame_count: Current simulation frame
        paused: Whether simulation is paused (readable and writable)
        world: The underlying world adapter
    """

    @property
    def world(self) -> Any:
        """The underlying world adapter (MultiAgentWorldBackend)."""
        ...

    @property
    def world_id(self) -> str:
        """Unique identifier for this world instance."""
        ...

    @property
    def running(self) -> bool:
        """Whether the simulation is currently running."""
        ...

    @running.setter
    def running(self, value: bool) -> None:
        """Set the simulation running state."""
        ...

    @property
    def world_type(self) -> str:
        """Type of world (tank, petri, etc.)."""
        ...

    @property
    def mode_id(self) -> str:
        """Mode identifier for UI display."""
        ...

    @property
    def view_mode(self) -> str:
        """Default view mode (side, topdown)."""
        ...

    @property
    def frame_count(self) -> int:
        """Current simulation frame number."""
        ...

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        ...

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the simulation paused state."""
        ...

    @property
    def fast_forward(self) -> bool:
        """Whether fast forward mode is enabled."""
        ...

    @fast_forward.setter
    def fast_forward(self, value: bool) -> None:
        """Set fast forward mode."""
        ...

    def get_entities_snapshot(self) -> list[EntitySnapshot]:
        """Get entity snapshots for frontend rendering.

        Returns:
            List of EntitySnapshot DTOs for all entities
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary of simulation statistics
        """
        ...

    def get_world_info(self) -> dict[str, str]:
        """Get world metadata for frontend.

        Returns:
            Dictionary with mode_id, world_type, and view_mode
        """
        ...

    def get_state(
        self, force_full: bool = False, allow_delta: bool = True
    ) -> FullStatePayload | DeltaStatePayload:
        # returns FullStatePayload | DeltaStatePayload
        ...

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
        """Advance the simulation by one step.

        Args:
            actions_by_agent: Optional agent actions for this step
        """
        ...

    def reset(
        self,
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            config: World-specific configuration

        Returns:
            Reset result (typically StepResult or None)
        """
        ...

    def switch_world_type(self, new_world_type: str) -> None:
        """Switch to a different world type while preserving entities.

        Only supported for tank <-> petri switching. Other runners
        should raise ValueError if called.

        Args:
            new_world_type: Target world type ("tank" or "petri")

        Raises:
            ValueError: If switching is not supported or invalid
        """
        ...

    def get_evolution_benchmark_data(self) -> dict[str, Any]:
        """Get evolution benchmark data for this world instance.

        Returns:
            Dictionary with benchmark history and metrics
        """
        ...
