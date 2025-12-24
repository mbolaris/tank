"""Simulation manager for coordinating tank simulations.

This module provides the SimulationManager class which manages simulation
lifecycle, client connections, and prepares for future multi-tank support
in Tank World Net.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    owner: Optional[str] = None
    server_id: str = "local-server"  # Which server this tank is running on
    seed: Optional[int] = None  # Random seed for deterministic behavior

    # Network visibility settings (for future use)
    is_public: bool = True
    allow_transfers: bool = True  # Allow fish/plants to transfer between tanks

    # Persistence settings
    persistent: bool = True  # Whether this tank should be saved/restored
    auto_save_interval: float = 300.0  # Auto-save interval in seconds (default: 5 minutes)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tank info for API responses."""
        return {
            "tank_id": self.tank_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "owner": self.owner,
            "server_id": self.server_id,
            "seed": self.seed,
            "is_public": self.is_public,
            "allow_transfers": self.allow_transfers,
            "persistent": self.persistent,
            "auto_save_interval": self.auto_save_interval,
        }


class SimulationManager:
    """Manages a tank simulation and its connected clients.

    This class encapsulates the lifecycle management of a simulation,
    including starting/stopping, client tracking, and state retrieval.
    Designed to support future multi-tank scenarios in Tank World Net.
    """

    def __init__(
        self,
        tank_name: str = "Tank 1",
        tank_description: str = "A local fish tank simulation",
        seed: Optional[int] = None,
        persistent: bool = True,
        auto_save_interval: float = 300.0,
    ):
        """Initialize the simulation manager.

        Args:
            tank_name: Human-readable name for this tank
            tank_description: Description of this tank
            seed: Optional random seed for deterministic behavior
            persistent: Whether this tank should auto-save and restore
            auto_save_interval: Auto-save interval in seconds (default: 5 minutes)
        """
        # Generate unique tank ID
        self.tank_info = TankInfo(
            tank_id=str(uuid.uuid4()),
            name=tank_name,
            description=tank_description,
            seed=seed,
            persistent=persistent,
            auto_save_interval=auto_save_interval,
        )

        # Create simulation runner
        self._runner = SimulationRunner(
            seed=seed, tank_id=self.tank_info.tank_id, tank_name=self.tank_info.name
        )

        # Track connected WebSocket clients
        self._connected_clients: Set[WebSocket] = set()

        # Track whether we're waiting for first client connection.
        # Simulations start paused and auto-unpause when first client connects.
        # After that, the simulation keeps running even if all clients disconnect.
        # Users can still manually pause/resume via API.
        self._awaiting_first_client: bool = True

        logger.info(
            "SimulationManager initialized: tank_id=%s, name=%s, persistent=%s",
            self.tank_info.tank_id,
            self.tank_info.name,
            persistent,
        )
        # Cache last successful stats to return on transient failures
        self._last_status_cache: Optional[Dict[str, Any]] = None

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
        self._prune_closed_clients()
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
        self._prune_closed_clients()
        self._connected_clients.add(websocket)

        # Auto-unpause only when first client connects after startup.
        # This ensures fish don't age before anyone sees them.
        # After first client, simulation keeps running regardless of client count.
        if self._awaiting_first_client and self._runner.world.paused:
            self._runner.world.paused = False
            self._awaiting_first_client = False
            logger.info("First client connected to tank %s, simulation unpaused", self.tank_id)

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
        self._prune_closed_clients()

        # Simulation keeps running even when all clients disconnect.
        # Users can manually pause via API if needed.
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

    def capture_state_for_save(self) -> Optional[Dict[str, Any]]:
        """Capture a thread-safe snapshot of the tank state for saving.

        This method acquires the simulation lock to ensure a consistent state,
        then creates a deep copy of the necessary data so that serialization
        and file I/O can happen outside the lock.
        """
        if not self.running:
            # If not running, we can just access the world directly
            # But we should still be careful about concurrent access
            pass

        try:
            # Phase 1: Capture mutable state inside the lock (FAST)
            captured_data = {}
            captured_entities = []

            # Try to acquire lock with timeout to prevent blocking indefinitely
            # This is critical because this runs in the main thread (via auto_save_service)
            lock_acquired = self._runner.lock.acquire(timeout=0.5)
            if not lock_acquired:
                logger.warning(f"capture_state_for_save: Lock acquisition timed out for tank {self.tank_id}")
                return None

            try:
                # Import here to avoid circular imports
                from backend.entity_transfer import (
                    capture_fish_mutable_state,
                    capture_plant_mutable_state,
                )
                from core.entities import Fish, Food, Plant, PlantNectar
                from core.entities.base import Castle
                from core.entities.predators import Crab

                world = self.world
                engine = world.engine

                # 1. Capture metadata
                captured_data["version"] = "2.0"
                captured_data["tank_id"] = self.tank_id
                captured_data["saved_at"] = datetime.now(UTC).isoformat()
                captured_data["frame"] = world.frame_count
                captured_data["metadata"] = {
                    "name": self.tank_info.name,
                    "description": self.tank_info.description,
                    "allow_transfers": self.tank_info.allow_transfers,
                    "is_public": self.tank_info.is_public,
                    "owner": self.tank_info.owner,
                    "seed": self.tank_info.seed,
                }
                captured_data["paused"] = world.paused

                # 2. Capture ecosystem stats
                captured_data["ecosystem"] = {
                    "total_births": engine.ecosystem.total_births,
                    "total_deaths": engine.ecosystem.total_deaths,
                    "current_generation": engine.ecosystem.current_generation,
                    "death_causes": dict(engine.ecosystem.death_causes),
                    "poker_stats": {
                        "total_fish_games": engine.ecosystem.total_fish_poker_games,
                        "total_plant_games": engine.ecosystem.total_plant_poker_games,
                    },
                }

                # 3. Capture entities (mutable state only)
                for entity in engine.entities_list:
                    if isinstance(entity, Fish):
                        captured_entities.append(("fish", entity, capture_fish_mutable_state(entity)))
                    elif isinstance(entity, Plant):
                        captured_entities.append(("plant", entity, capture_plant_mutable_state(entity)))
                    elif isinstance(entity, (PlantNectar, Food, Castle, Crab)):
                        # For simple entities, we can just capture them directly or copy needed data
                        # Since they are small/few, full copy here is fine
                        captured_entities.append(("other", entity, None))
            finally:
                self._runner.lock.release()

            # Phase 2: Finalize serialization outside the lock (SLOW)
            from backend.entity_transfer import (
                finalize_fish_serialization,
                finalize_plant_serialization,
            )
            from core.entities import Fish, Food, Plant, PlantNectar
            from core.entities.base import Castle
            from core.entities.predators import Crab

            entities_data = []
            for idx, (entity_type, entity, mutable_state) in enumerate(captured_entities):
                try:
                    if entity_type == "fish":
                        serialized = finalize_fish_serialization(entity, mutable_state)
                        entities_data.append(serialized)
                    elif entity_type == "plant":
                        serialized = finalize_plant_serialization(entity, mutable_state)
                        entities_data.append(serialized)
                    else:
                        # Manual serialization for other types (same as before)
                        if isinstance(entity, PlantNectar):
                            entities_data.append({
                                "type": "plant_nectar",
                                "id": id(entity),
                                "x": entity.pos.x,
                                "y": entity.pos.y,
                                "energy": entity.energy,
                                "source_plant_id": getattr(entity, "source_plant_id", None),
                                "source_plant_x": getattr(entity, "source_plant_x", entity.pos.x),
                                "source_plant_y": getattr(entity, "source_plant_y", entity.pos.y),
                            })
                        elif isinstance(entity, Food):
                            entities_data.append({
                                "type": "food",
                                "id": id(entity),
                                "x": entity.pos.x,
                                "y": entity.pos.y,
                                "energy": entity.energy,
                                "food_type": entity.food_type,
                            })
                        elif isinstance(entity, Castle):
                            entities_data.append({
                                "type": "castle",
                                "x": entity.pos.x,
                                "y": entity.pos.y,
                                "width": entity.width,
                                "height": entity.height,
                            })
                        elif isinstance(entity, Crab):
                            # Serialize crab with genome
                            genome_data = {
                                "speed_modifier": entity.genome.speed_modifier,
                                "size_modifier": entity.genome.physical.size_modifier.value,
                                "metabolism_rate": entity.genome.metabolism_rate,
                                "color_hue": entity.genome.physical.color_hue.value,
                                "vision_range": entity.genome.vision_range,
                            }
                            entities_data.append({
                                "type": "crab",
                                "x": entity.pos.x,
                                "y": entity.pos.y,
                                "energy": entity.energy,
                                "max_energy": entity.max_energy,
                                "genome": genome_data,
                                "hunt_cooldown": entity.hunt_cooldown,
                            })
                except Exception as e:
                    logger.warning(f"Failed to serialize entity {type(entity).__name__}: {e}")
                    continue

                # Yield GIL periodically to prevent starving other threads
                if idx % 50 == 0 and idx > 0:
                    time.sleep(0.001)

            captured_data["entities"] = entities_data
            return captured_data

        except Exception as e:
            logger.error(f"Failed to capture state for tank {self.tank_id}: {e}", exc_info=True)
            return None

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
            # Acquire the runner lock to read a consistent snapshot of world stats.
            # This avoids transient exceptions or partial reads while the simulation
            # thread is mutating state which could cause the API to return zeros.
            runner_lock = getattr(self._runner, "lock", None)
            lock_acquired = False
            try:
                if runner_lock:
                    lock_acquired = runner_lock.acquire(timeout=0.1)

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
                    "poker_stats": world_stats.get("poker_stats", {}),
                }
            
                # Add poker score from evolution benchmark tracker
                tracker = getattr(self._runner, "evolution_benchmark_tracker", None)
                if tracker is not None:
                    latest = tracker.get_latest_snapshot()
                    if latest is not None and latest.confidence_vs_strong is not None:
                        stats["poker_score"] = latest.confidence_vs_strong
                        history = tracker.get_history()
                        if history:
                            valid_scores = [s.confidence_vs_strong for s in history if s.confidence_vs_strong is not None]
                            stats["poker_score_history"] = valid_scores[-20:]

                # Cache a copy of last-good stats for fallback
                try:
                    self._last_status_cache = dict(stats)
                except Exception:
                    pass
            finally:
                if runner_lock and lock_acquired:
                    try:
                        runner_lock.release()
                    except Exception:
                        pass
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to collect stats for tank %s: %s", self.tank_id, exc)
            if self._last_status_cache is not None:
                stats = dict(self._last_status_cache)
            else:
                stats = {}

        return {
            "tank": self.tank_info.to_dict(),
            "running": self.running,
            "client_count": self.client_count,
            "frame": self.world.frame_count if self.running else 0,
            "paused": self.world.paused if self.running else True,
            "fps": round(self._runner.current_actual_fps, 1)
            if self.running
            else 0.0,
            "stats": stats,
            "fast_forward": self._runner.fast_forward if self.running else False,
        }
