"""Central manager for active world instances across all types.

This module provides the WorldManager class which manages active world instances
for all world types (tank, petri, soccer) through a unified pipeline.

All world types now flow through the same creation/loop/broadcast path:
WorldManager → WorldInstance → SimulationRunner → Broadcast
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from fastapi import WebSocket

from backend.runner.runner_protocol import RunnerProtocol
from backend.simulation_runner import SimulationRunner
from backend.world_registry import create_world, get_all_world_metadata, get_world_metadata
from backend.world_runner import WorldRunner

if TYPE_CHECKING:
    from backend.world_broadcast_adapter import WorldBroadcastAdapter

logger = logging.getLogger(__name__)

# Type alias for broadcast callbacks
BroadcastCallback = Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class WorldInstance:
    """Represents an active world instance.

    This is the unified container for all world types. The runner field
    is always a SimulationRunner for tank worlds or WorldRunner for others.
    """

    world_id: str
    world_type: str
    mode_id: str
    name: str
    runner: RunnerProtocol  # SimulationRunner or WorldRunner
    created_at: datetime = field(default_factory=datetime.now)
    persistent: bool = True
    view_mode: str = "side"
    description: str = ""
    broadcast_adapter: WorldBroadcastAdapter | None = None
    # WebSocket clients connected to this world
    _connected_clients: set[WebSocket] = field(default_factory=set)

    def is_tank(self) -> bool:
        """Check if this is a tank (or petri) world using SimulationRunner."""
        return self.world_type in ("tank", "petri")

    @property
    def connected_clients(self) -> set[WebSocket]:
        """Get the set of connected WebSocket clients."""
        return self._connected_clients


@dataclass
class WorldStatus:
    """Status information for a world instance."""

    world_id: str
    world_type: str
    mode_id: str
    name: str
    view_mode: str
    frame_count: int
    paused: bool
    persistent: bool
    created_at: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "world_id": self.world_id,
            "world_type": self.world_type,
            "mode_id": self.mode_id,
            "name": self.name,
            "view_mode": self.view_mode,
            "frame_count": self.frame_count,
            "paused": self.paused,
            "persistent": self.persistent,
            "created_at": self.created_at,
            "description": self.description,
        }


class WorldManager:
    """Central manager for all active world instances.

    This class provides unified management of world instances across all world
    types (tank, petri, soccer). All worlds are stored in a single dictionary
    and accessed through the same interface.

    For tank worlds, SimulationRunner is used directly (no intermediate adapter).

    Attributes:
        _worlds: Dictionary of all world instances by world_id
        _default_world_id: ID of the default world
    """

    def __init__(self) -> None:
        """Initialize the world manager."""
        self._worlds: dict[str, WorldInstance] = {}
        self._default_world_id: str | None = None
        self._start_broadcast_callback: BroadcastCallback | None = None
        self._stop_broadcast_callback: BroadcastCallback | None = None
        self.connection_manager: Any = None

    def set_connection_manager(self, connection_manager: Any) -> None:
        """Set the connection manager instance."""
        self.connection_manager = connection_manager

    @property
    def default_world_id(self) -> str | None:
        """Get the default world ID."""
        return self._default_world_id

    def set_broadcast_callbacks(
        self,
        start_callback: BroadcastCallback,
        stop_callback: BroadcastCallback,
    ) -> None:
        """Set callbacks for starting/stopping broadcasts."""
        self._start_broadcast_callback = start_callback
        self._stop_broadcast_callback = stop_callback

    def create_world(
        self,
        world_type: str,
        name: str,
        *,
        config: dict[str, Any] | None = None,
        persistent: bool = True,
        seed: int | None = None,
        description: str = "",
        world_id: str | None = None,
        start_paused: bool = False,
    ) -> WorldInstance:
        """Create a new world instance.

        All world types flow through this unified creation path.

        Args:
            world_type: The type of world to create (tank, petri, soccer)
            name: Human-readable name for the world
            config: Optional configuration for the world
            persistent: Whether the world should be persisted
            seed: Optional random seed for deterministic behavior
            description: Optional description of the world
            world_id: Optional specific world ID (generated if not provided)
            start_paused: Whether to start the simulation paused

        Returns:
            The created WorldInstance

        Raises:
            ValueError: If the world type is not registered
        """
        metadata = get_world_metadata(world_type)
        if metadata is None:
            available = [m.mode_id for m in get_all_world_metadata()]
            raise ValueError(f"Unknown world type '{world_type}'. Available: {available}")

        # Check persistence capability
        if persistent and not metadata.supports_persistence:
            logger.warning(
                "World type '%s' does not support persistence. Creating as non-persistent.",
                world_type,
            )
            persistent = False

        # Generate world ID if not provided
        if world_id is None:
            world_id = str(uuid.uuid4())

        # Unified creation path - dispatch by world type
        if world_type == "tank" or world_type == "petri":
            return self._create_tank_world(
                world_id=world_id,
                world_type=world_type,
                name=name,
                config=config,
                seed=seed,
                persistent=persistent,
                description=description,
                start_paused=start_paused,
            )

        return self._create_generic_world(
            world_id=world_id,
            world_type=world_type,
            mode_id=metadata.mode_id,
            view_mode=metadata.view_mode,
            name=name,
            config=config,
            seed=seed,
            persistent=persistent,
            description=description,
        )

    def _create_tank_world(
        self,
        world_id: str,
        world_type: str,
        name: str,
        config: dict[str, Any] | None,
        seed: int | None,
        persistent: bool,
        description: str,
        start_paused: bool = False,
    ) -> WorldInstance:
        """Create a tank/petri world using SimulationRunner directly.

        SimulationRunner handles both tank and petri worlds via switch_world_type().
        """
        # Create SimulationRunner directly (no SimulationManager intermediary)
        runner = SimulationRunner(
            seed=seed,
            tank_id=world_id,
            tank_name=name,
            world_type=world_type,
        )
        runner.world_manager = self

        # Start the simulation thread
        runner.start(start_paused=start_paused)

        # Get view mode from runner
        view_mode = runner.view_mode

        # Create unified WorldInstance
        instance = WorldInstance(
            world_id=world_id,
            world_type=world_type,
            mode_id=runner.mode_id,
            name=name,
            runner=runner,
            created_at=datetime.now(),
            persistent=persistent,
            view_mode=view_mode,
            description=description,
        )

        # Store in unified worlds dict
        self._worlds[world_id] = instance

        # Set as default if first world
        if self._default_world_id is None:
            self._default_world_id = world_id

        logger.info(
            "Created %s world: %s (%s)",
            world_type,
            world_id[:8],
            name,
        )

        # Start broadcast task for newly created tank worlds
        if self._start_broadcast_callback:
            adapter = self.get_broadcast_adapter(world_id)
            if adapter:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        self._start_broadcast_callback(adapter, world_id),
                        name=f"broadcast_start_{world_id[:8]}",
                    )
                    logger.info("Scheduled broadcast task for world %s", world_id[:8])
                except RuntimeError:
                    # No running event loop - broadcast will be started when first client connects
                    logger.debug(
                        "No event loop available, broadcast task for %s will start on connection",
                        world_id[:8],
                    )

        return instance

    def _create_generic_world(
        self,
        world_id: str,
        world_type: str,
        mode_id: str,
        view_mode: str,
        name: str,
        config: dict[str, Any] | None,
        seed: int | None,
        persistent: bool,
        description: str,
    ) -> WorldInstance:
        """Create a non-tank world with WorldRunner."""
        # Create world and snapshot builder via backend registry
        world_backend, snapshot_builder = create_world(
            mode_id,
            seed=seed,
            config=config or {},
        )

        # Create WorldRunner
        runner = WorldRunner(
            world=world_backend,
            snapshot_builder=snapshot_builder,
            world_type=world_type,
            mode_id=mode_id,
            view_mode=view_mode,
        )

        # Ensure world is initialized
        runner.reset(seed=seed, config=config)

        # Create instance
        instance = WorldInstance(
            world_id=world_id,
            world_type=world_type,
            mode_id=mode_id,
            name=name,
            runner=runner,
            persistent=persistent,
            view_mode=view_mode,
            description=description,
        )

        # Store in unified worlds dict
        self._worlds[world_id] = instance

        # Set as default if first world
        if self._default_world_id is None:
            self._default_world_id = world_id

        logger.info(
            "Created %s world: %s (%s)",
            world_type,
            world_id[:8],
            name,
        )

        return instance

    def get_world(self, world_id: str) -> WorldInstance | None:
        """Get a world instance by ID.

        Args:
            world_id: The unique world identifier

        Returns:
            The WorldInstance if found, None otherwise
        """
        return self._worlds.get(world_id)

    def get_default_world(self) -> WorldInstance | None:
        """Get the default world instance.

        Returns:
            The default WorldInstance if one exists, None otherwise
        """
        if self._default_world_id is None:
            return None
        return self._worlds.get(self._default_world_id)

    def get_broadcast_adapter(self, world_id: str) -> WorldBroadcastAdapter | None:
        """Get or create the broadcast adapter for a world."""
        instance = self.get_world(world_id)
        if instance is None:
            return None

        if instance.broadcast_adapter is not None:
            return instance.broadcast_adapter

        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        step_on_access = not instance.is_tank()
        use_runner_state = instance.is_tank()

        adapter = WorldSnapshotAdapter(
            world_id=instance.world_id,
            runner=instance.runner,
            world_type=instance.world_type,
            mode_id=instance.mode_id,
            view_mode=instance.view_mode,
            step_on_access=step_on_access,
            use_runner_state=use_runner_state,
        )
        instance.broadcast_adapter = adapter
        return adapter

    def list_worlds(self, world_type: str | None = None) -> list[WorldStatus]:
        """List all active worlds.

        Args:
            world_type: Optional filter by world type

        Returns:
            List of WorldStatus for all matching worlds
        """
        statuses: list[WorldStatus] = []

        for world_id, instance in self._worlds.items():
            if world_type is not None and instance.world_type != world_type:
                continue

            # Get frame_count and paused from the runner
            runner = instance.runner
            frame_count = runner.frame_count
            paused = runner.paused

            statuses.append(
                WorldStatus(
                    world_id=world_id,
                    world_type=instance.world_type,
                    mode_id=instance.mode_id,
                    name=instance.name,
                    view_mode=instance.view_mode,
                    frame_count=frame_count,
                    paused=paused,
                    persistent=instance.persistent,
                    created_at=instance.created_at.isoformat(),
                    description=instance.description,
                )
            )

        return statuses

    def delete_world(self, world_id: str) -> bool:
        """Delete a world instance.

        Args:
            world_id: The world ID to delete

        Returns:
            True if deleted, False if not found
        """
        instance = self._worlds.pop(world_id, None)

        if instance is not None:
            # Stop the runner if it's a SimulationRunner
            if hasattr(instance.runner, "stop"):
                instance.runner.stop()

            # Update default world if needed
            if self._default_world_id == world_id:
                self._default_world_id = next(iter(self._worlds), None)

            # Cleanup connections
            if self.connection_manager:
                self.connection_manager.validate_connections(list(self._worlds.keys()))

            logger.info("Deleted world: %s (%s)", world_id[:8], instance.world_type)
            return True

        return False

    def step_world(self, world_id: str, actions: dict[str, Any] | None = None) -> bool:
        """Step a world by one frame.

        Works for all world types through the unified runner interface.

        Args:
            world_id: The world ID to step
            actions: Optional actions for agent-controlled worlds

        Returns:
            True if stepped, False if not found
        """
        instance = self.get_world(world_id)
        if instance is None:
            return False

        instance.runner.step(actions_by_agent=actions)
        return True

    @property
    def world_count(self) -> int:
        """Get total number of active worlds."""
        return len(self._worlds)

    def get_all_worlds(self) -> dict[str, WorldInstance]:
        """Get all world instances.

        Returns:
            Dictionary of world_id to WorldInstance
        """
        return dict(self._worlds)

    def start_all_worlds(self, start_paused: bool = False) -> None:
        """Start all world simulations.

        Args:
            start_paused: Whether to start worlds in paused state
        """
        for instance in self._worlds.values():
            if hasattr(instance.runner, "start"):
                if not instance.runner.running:
                    instance.runner.start(start_paused=start_paused)

    def stop_all_worlds(self) -> None:
        """Stop all world simulations."""
        for instance in self._worlds.values():
            if hasattr(instance.runner, "stop"):
                instance.runner.stop()

    # =========================================================================
    # Persistence support
    # =========================================================================

    def capture_world_state(self, world_id: str) -> dict[str, Any] | None:
        """Capture world state for persistence.

        Delegates to the world's persistence method if available.

        Args:
            world_id: The world ID to capture

        Returns:
            Captured state dict, or None if not supported/failed
        """
        instance = self.get_world(world_id)
        if instance is None:
            return None

        if not instance.persistent:
            return None

        # Tank worlds have their own capture method via SimulationRunner
        if instance.is_tank() and isinstance(instance.runner, SimulationRunner):
            # SimulationRunner doesn't have capture_state_for_save, that was on SimulationManager
            # For now, skip persistence (can be added later)
            return None

        # Other world types don't support persistence yet
        return None

    # =========================================================================
    # Client management (for WebSocket connections)
    # =========================================================================

    def add_client(self, world_id: str, websocket: WebSocket) -> bool:
        """Add a WebSocket client to a world.

        Args:
            world_id: The world ID
            websocket: The WebSocket connection

        Returns:
            True if added, False if world not found
        """
        instance = self.get_world(world_id)
        if instance is None:
            return False

        instance._connected_clients.add(websocket)
        return True

    def remove_client(self, world_id: str, websocket: WebSocket) -> bool:
        """Remove a WebSocket client from a world.

        Args:
            world_id: The world ID
            websocket: The WebSocket connection

        Returns:
            True if removed, False if not found
        """
        instance = self.get_world(world_id)
        if instance is None:
            return False

        instance._connected_clients.discard(websocket)
        return True

    def get_client_count(self, world_id: str) -> int:
        """Get the number of connected clients for a world.

        Args:
            world_id: The world ID

        Returns:
            Number of connected clients, 0 if world not found
        """
        instance = self.get_world(world_id)
        if instance is None:
            return 0
        return len(instance._connected_clients)

    # =========================================================================
    # Iterator support
    # =========================================================================

    def __iter__(self):
        """Iterate over world instances."""
        return iter(self._worlds.values())

    def __len__(self) -> int:
        """Get the number of worlds."""
        return len(self._worlds)

    def __contains__(self, world_id: str) -> bool:
        """Check if a world ID exists."""
        return world_id in self._worlds
