"""Simulation manager for coordinating tank simulations.

This module provides the SimulationManager class which manages simulation
lifecycle, client connections, and prepares for future multi-tank support
in Tank World Net.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


@dataclass
class TankInfo:
    """Metadata about a tank simulation.

    This dataclass holds identifying information about a tank that will be
    used for network registration and discovery in Tank World Net.
    """

    tank_id: str
    name: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    owner: Optional[str] = None

    # Network visibility settings (for future use)
    is_public: bool = True
    allow_transfers: bool = False  # Allow fish/plants to transfer between tanks

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tank info for API responses."""
        return {
            "tank_id": self.tank_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "owner": self.owner,
            "is_public": self.is_public,
            "allow_transfers": self.allow_transfers,
        }


class SimulationManager:
    """Manages a tank simulation and its connected clients.

    This class encapsulates the lifecycle management of a simulation,
    including starting/stopping, client tracking, and state retrieval.
    Designed to support future multi-tank scenarios in Tank World Net.
    """

    def __init__(
        self,
        tank_name: str = "Local Tank",
        tank_description: str = "A local fish tank simulation",
        seed: Optional[int] = None,
    ):
        """Initialize the simulation manager.

        Args:
            tank_name: Human-readable name for this tank
            tank_description: Description of this tank
            seed: Optional random seed for deterministic behavior
        """
        # Generate unique tank ID
        self.tank_info = TankInfo(
            tank_id=str(uuid.uuid4()),
            name=tank_name,
            description=tank_description,
        )

        # Create simulation runner
        self._runner = SimulationRunner(seed=seed)

        # Track connected WebSocket clients
        self._connected_clients: Set[WebSocket] = set()

        logger.info(
            "SimulationManager initialized: tank_id=%s, name=%s",
            self.tank_info.tank_id,
            self.tank_info.name,
        )

    @property
    def tank_id(self) -> str:
        """Get the unique tank identifier."""
        return self.tank_info.tank_id

    @property
    def runner(self) -> SimulationRunner:
        """Access the underlying simulation runner."""
        return self._runner

    @property
    def world(self):
        """Access the TankWorld instance."""
        return self._runner.world

    @property
    def running(self) -> bool:
        """Check if the simulation is running."""
        return self._runner.running

    @property
    def connected_clients(self) -> Set[WebSocket]:
        """Get the set of connected WebSocket clients."""
        return self._connected_clients

    @property
    def client_count(self) -> int:
        """Get the number of connected clients."""
        self._prune_closed_clients()
        return len(self._connected_clients)

    def start(self, start_paused: bool = False) -> None:
        """Start the simulation.

        Args:
            start_paused: Whether to start in paused state
        """
        logger.info("Starting simulation for tank %s", self.tank_id)
        self._runner.start(start_paused=start_paused)

    def stop(self) -> None:
        """Stop the simulation."""
        logger.info("Stopping simulation for tank %s", self.tank_id)
        self._runner.stop()

    def _prune_closed_clients(self) -> None:
        """Remove any WebSocket connections that are no longer open."""
        stale_clients = {
            websocket
            for websocket in self._connected_clients
            if websocket.client_state not in {WebSocketState.CONNECTED, WebSocketState.CONNECTING}
        }

        if stale_clients:
            self._connected_clients.difference_update(stale_clients)
            logger.info(
                "Pruned %d stale clients from tank %s. Total clients: %d",
                len(stale_clients),
                self.tank_id,
                len(self._connected_clients),
            )

    def add_client(self, websocket: WebSocket) -> None:
        """Register a new WebSocket client.

        Args:
            websocket: The WebSocket connection to track
        """
        self._connected_clients.add(websocket)
        logger.info(
            "Client added to tank %s. Total clients: %d",
            self.tank_id,
            self.client_count,
        )

    def remove_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client.

        Args:
            websocket: The WebSocket connection to remove
        """
        self._connected_clients.discard(websocket)
        logger.info(
            "Client removed from tank %s. Total clients: %d",
            self.tank_id,
            self.client_count,
        )

    def get_state(self, force_full: bool = False, allow_delta: bool = True):
        """Get current simulation state.

        Args:
            force_full: Force a full state update
            allow_delta: Allow delta compression

        Returns:
            State payload with tank_id included
        """
        state = self._runner.get_state(force_full=force_full, allow_delta=allow_delta)
        # Inject tank_id for network identification
        state.tank_id = self.tank_id
        return state

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True):
        """Async wrapper for get_state.

        Args:
            force_full: Force a full state update
            allow_delta: Allow delta compression

        Returns:
            State payload with tank_id included
        """
        state = await self._runner.get_state_async(
            force_full=force_full, allow_delta=allow_delta
        )
        # Inject tank_id for network identification
        state.tank_id = self.tank_id
        return state

    def serialize_state(self, state) -> bytes:
        """Serialize state payload to bytes.

        Args:
            state: State payload to serialize

        Returns:
            Serialized bytes
        """
        return self._runner.serialize_state(state)

    async def handle_command_async(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ):
        """Handle a command from a client.

        Args:
            command: Command type
            data: Optional command data

        Returns:
            Command result
        """
        return await self._runner.handle_command_async(command, data)

    def get_status(self) -> Dict[str, Any]:
        """Get current tank status for API responses.

        Returns:
            Dictionary with tank status information
        """
        stats: Dict[str, Any] = {}
        try:
            world_stats = self.world.get_stats()
            stats = {
                "fish_count": world_stats.get("fish_count", 0),
                "generation": world_stats.get("current_generation", 0),
                "max_generation": world_stats.get(
                    "max_generation", world_stats.get("current_generation", 0)
                ),
                "total_extinctions": world_stats.get("total_extinctions", 0),
                "total_energy": world_stats.get("total_energy", 0.0),
                "fish_energy": world_stats.get("fish_energy", 0.0),
                "plant_energy": world_stats.get("plant_energy", 0.0),
            }
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to collect stats for tank %s: %s", self.tank_id, exc)

        return {
            "tank": self.tank_info.to_dict(),
            "running": self.running,
            "client_count": self.client_count,
            "frame": self.world.frame_count if self.running else 0,
            "paused": self.world.paused if self.running else True,
            "stats": stats,
        }
