"""TankWorldAdapter - Adapts SimulationManager to the unified World API.

This adapter wraps the existing SimulationManager/SimulationRunner machinery
to expose the same interface as WorldRunner, enabling tank worlds to run
through the same WorldManager pipeline as petri/soccer worlds.

The adapter does NOT change any tank simulation behavior - it's purely a
bridge between the legacy tank machinery and the new unified world API.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from fastapi import WebSocket

if TYPE_CHECKING:
    from backend.simulation_manager import SimulationManager
    from backend.state_payloads import EntitySnapshot, FullStatePayload, DeltaStatePayload

logger = logging.getLogger(__name__)


class TankWorldAdapter:
    """Adapter that wraps SimulationManager to expose WorldRunner-compatible interface.

    This adapter enables tank worlds to be managed through the unified WorldManager
    pipeline while preserving all tank-specific functionality (poker games, evolution
    benchmarks, migration support, delta compression, etc.).

    The adapter delegates all operations to the underlying SimulationManager,
    translating between the unified World API and the tank-specific implementation.

    Attributes:
        manager: The underlying SimulationManager
        world_type: Always "tank" for this adapter
        mode_id: Always "tank" for this adapter
        view_mode: Always "side" for tank worlds
    """

    def __init__(self, manager: "SimulationManager") -> None:
        """Initialize the adapter with a SimulationManager.

        Args:
            manager: The SimulationManager to wrap
        """
        self._manager = manager
        self.world_type = "tank"
        self.mode_id = "tank"
        self.view_mode = "side"

    @property
    def manager(self) -> "SimulationManager":
        """Get the underlying SimulationManager."""
        return self._manager

    @property
    def runner(self) -> Any:
        """Get the underlying SimulationRunner for direct access.

        This is used for backward compatibility with code that expects
        to access the runner directly.
        """
        return self._manager.runner

    @property
    def world(self) -> Any:
        """Get the underlying TankWorld for direct access."""
        return self._manager.world

    @property
    def tank_id(self) -> str:
        """Get the tank ID."""
        return self._manager.tank_id

    @property
    def tank_info(self) -> Any:
        """Get the TankInfo for this tank."""
        return self._manager.tank_info

    # =========================================================================
    # WorldRunner-compatible interface
    # =========================================================================

    @property
    def frame_count(self) -> int:
        """Current frame count from the simulation."""
        return self._manager.world.frame_count

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        return self._manager.world.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the simulation paused state."""
        self._manager.world.paused = value

    @property
    def running(self) -> bool:
        """Whether the simulation thread is running."""
        return self._manager.running

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> None:
        """Step the simulation by one frame.

        For tank worlds, this is typically not called directly since the
        simulation runs in a background thread. This method is provided
        for API compatibility with other world types.

        Args:
            actions_by_agent: Not used for autonomous tank simulations
        """
        # Tank runs in background thread, but we can still force a step
        # through the world interface if needed
        runner = self._manager.runner
        with runner.lock:
            runner.world.step(actions_by_agent)

    def reset(
        self,
        seed: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Reset the simulation.

        Note: Full reset support for tank worlds is limited since they
        maintain persistent state. This primarily clears the world state.

        Args:
            seed: Random seed (not used for tank reset)
            config: Configuration (not used for tank reset)
        """
        # Tank doesn't support full reset like other worlds
        # We just handle pause/unpause through commands
        logger.warning("Tank worlds don't support full reset. Use commands instead.")

    def setup(self) -> None:
        """Initialize the world (no-op for tank, already initialized)."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary of simulation statistics including:
            - fish_count, plant_count, food_count
            - total_energy, fish_energy, plant_energy
            - generation, max_generation
            - fps, frame
            - poker_stats
        """
        runner = self._manager.runner
        frame = self._manager.world.frame_count
        stats_payload = runner._collect_stats(frame, include_distributions=False)

        # Convert StatsPayload to dict
        return {
            "fish_count": stats_payload.fish_count,
            "plant_count": stats_payload.plant_count,
            "food_count": stats_payload.food_count,
            "total_energy": stats_payload.total_energy,
            "fish_energy": stats_payload.fish_energy,
            "plant_energy": stats_payload.plant_energy,
            "generation": stats_payload.generation,
            "max_generation": stats_payload.max_generation,
            "fps": stats_payload.fps,
            "frame": stats_payload.frame,
            "fast_forward": stats_payload.fast_forward,
            "poker_score": stats_payload.poker_score,
        }

    def get_entities_snapshot(self) -> List["EntitySnapshot"]:
        """Get entity snapshots for rendering.

        Returns:
            List of EntitySnapshot DTOs for all entities
        """
        return self._manager.runner._collect_entities()

    def get_world_info(self) -> Dict[str, str]:
        """Get world metadata for frontend.

        Returns:
            Dictionary with mode_id, world_type, and view_mode
        """
        return {
            "mode_id": self.mode_id,
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }

    # =========================================================================
    # Tank-specific interface (exposed through adapter)
    # =========================================================================

    def start(self, start_paused: bool = False) -> None:
        """Start the simulation thread.

        Args:
            start_paused: Whether to start in paused state
        """
        self._manager.start(start_paused=start_paused)

    def stop(self) -> None:
        """Stop the simulation thread."""
        self._manager.stop()

    # =========================================================================
    # Client management (for WebSocket broadcasting)
    # =========================================================================

    @property
    def connected_clients(self) -> Set[WebSocket]:
        """Get the set of connected WebSocket clients."""
        return self._manager.connected_clients

    @property
    def client_count(self) -> int:
        """Get the number of connected clients."""
        return self._manager.client_count

    def add_client(self, websocket: WebSocket) -> None:
        """Register a new WebSocket client.

        Args:
            websocket: The WebSocket connection to track
        """
        self._manager.add_client(websocket)

    def remove_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client.

        Args:
            websocket: The WebSocket connection to remove
        """
        self._manager.remove_client(websocket)

    # =========================================================================
    # State serialization (for WebSocket broadcasting)
    # =========================================================================

    def get_state(
        self, force_full: bool = False, allow_delta: bool = True
    ) -> Union["FullStatePayload", "DeltaStatePayload"]:
        """Get current simulation state for WebSocket broadcast.

        Args:
            force_full: Force a full state update
            allow_delta: Allow delta compression

        Returns:
            State payload with delta compression if applicable
        """
        return self._manager.get_state(force_full=force_full, allow_delta=allow_delta)

    async def get_state_async(
        self, force_full: bool = False, allow_delta: bool = True
    ) -> Union["FullStatePayload", "DeltaStatePayload"]:
        """Async wrapper for get_state.

        Args:
            force_full: Force a full state update
            allow_delta: Allow delta compression

        Returns:
            State payload with delta compression if applicable
        """
        return await self._manager.get_state_async(
            force_full=force_full, allow_delta=allow_delta
        )

    def serialize_state(
        self, state: Union["FullStatePayload", "DeltaStatePayload"]
    ) -> bytes:
        """Serialize state payload to bytes.

        Args:
            state: State payload to serialize

        Returns:
            Serialized bytes for WebSocket transmission
        """
        return self._manager.serialize_state(state)

    # =========================================================================
    # Command handling
    # =========================================================================

    def handle_command(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a command from a client.

        Args:
            command: Command type (e.g., 'add_food', 'spawn_fish', 'pause')
            data: Optional command data

        Returns:
            Command response dictionary
        """
        return self._manager.runner.handle_command(command, data)

    async def handle_command_async(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Async wrapper for handle_command.

        Args:
            command: Command type
            data: Optional command data

        Returns:
            Command response dictionary
        """
        return await self._manager.handle_command_async(command, data)

    # =========================================================================
    # Persistence support
    # =========================================================================

    @property
    def persistent(self) -> bool:
        """Whether this tank should be persisted."""
        return self._manager.tank_info.persistent

    def capture_state_for_save(self) -> Optional[Dict[str, Any]]:
        """Capture a thread-safe snapshot for persistence.

        Returns:
            Snapshot data suitable for saving, or None if capture failed
        """
        return self._manager.capture_state_for_save()

    # =========================================================================
    # Status information
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive tank status.

        Returns:
            Dictionary with tank status information including:
            - tank info, running state, client count
            - frame count, paused state, fps
            - simulation statistics
        """
        return self._manager.get_status()

    @property
    def name(self) -> str:
        """Get the tank name."""
        return self._manager.tank_info.name

    @property
    def description(self) -> str:
        """Get the tank description."""
        return self._manager.tank_info.description

    @property
    def created_at(self) -> datetime:
        """Get the tank creation time."""
        return self._manager.tank_info.created_at

    # =========================================================================
    # Migration and distributed features
    # =========================================================================

    def set_migration_context(
        self,
        connection_manager: Any,
        tank_registry: Any,
    ) -> None:
        """Set migration context for distributed features.

        Args:
            connection_manager: ConnectionManager for tank connections
            tank_registry: TankRegistry for tank lookups
        """
        runner = self._manager.runner
        runner.connection_manager = connection_manager
        runner.tank_registry = tank_registry
        runner._update_environment_migration_context()

    # =========================================================================
    # Evolution benchmark data
    # =========================================================================

    def get_evolution_benchmark_data(self) -> Dict[str, Any]:
        """Get evolution benchmark tracking data.

        Returns:
            Dictionary with benchmark history and metrics
        """
        return self._manager.runner.get_evolution_benchmark_data()
