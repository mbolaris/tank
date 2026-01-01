"""Central manager for active world instances across all types.

This module provides the WorldManager class which manages active world instances
for all world types (tank, petri, soccer). For tank worlds, it delegates to the
existing TankRegistry to preserve compatibility. For other world types, it
manages WorldRunner instances directly.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional

from backend.world_registry import create_world, get_all_world_metadata, get_world_metadata
from backend.world_runner import WorldRunner

if TYPE_CHECKING:
    from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)

# Type alias for broadcast callbacks
BroadcastCallback = Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class WorldInstance:
    """Represents an active world instance."""

    world_id: str
    world_type: str
    mode_id: str
    name: str
    runner: WorldRunner
    created_at: datetime = field(default_factory=datetime.now)
    persistent: bool = True
    view_mode: str = "side"
    description: str = ""


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

    def to_dict(self) -> Dict[str, Any]:
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

    This class unifies management of world instances across all world types.
    For tank worlds, it delegates to TankRegistry to preserve existing behavior.
    For other world types (petri, soccer), it manages WorldRunner instances directly.

    Attributes:
        tank_registry: The TankRegistry for tank-specific operations
        _worlds: Dictionary of non-tank world instances by world_id
    """

    def __init__(
        self,
        tank_registry: Optional["TankRegistry"] = None,
    ) -> None:
        """Initialize the world manager.

        Args:
            tank_registry: Optional existing TankRegistry for tank worlds
        """
        self._tank_registry = tank_registry
        self._worlds: Dict[str, WorldInstance] = {}
        self._start_broadcast_callback: Optional[BroadcastCallback] = None
        self._stop_broadcast_callback: Optional[BroadcastCallback] = None

    def set_tank_registry(self, tank_registry: "TankRegistry") -> None:
        """Set the tank registry for tank world operations."""
        self._tank_registry = tank_registry

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
        config: Optional[Dict[str, Any]] = None,
        persistent: bool = True,
        seed: Optional[int] = None,
        description: str = "",
    ) -> WorldInstance:
        """Create a new world instance.

        Args:
            world_type: The type of world to create (tank, petri, soccer)
            name: Human-readable name for the world
            config: Optional configuration for the world
            persistent: Whether the world should be persisted
            seed: Optional random seed for deterministic behavior
            description: Optional description of the world

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

        # For tank worlds, delegate to TankRegistry
        if world_type == "tank" and self._tank_registry is not None:
            return self._create_tank_world(name, config, seed, persistent, description)

        # For other world types, create directly
        return self._create_generic_world(
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
        name: str,
        config: Optional[Dict[str, Any]],
        seed: Optional[int],
        persistent: bool,
        description: str,
    ) -> WorldInstance:
        """Create a tank world through TankRegistry."""
        if self._tank_registry is None:
            raise RuntimeError("TankRegistry not available")

        # Create tank through registry
        manager = self._tank_registry.create_tank(
            name=name,
            description=description,
            seed=seed,
            persistent=persistent,
        )

        # Start the simulation
        manager.start(start_paused=False)

        # Create WorldInstance wrapper
        return WorldInstance(
            world_id=manager.tank_id,
            world_type="tank",
            mode_id="tank",
            name=name,
            runner=manager.runner,
            persistent=persistent,
            view_mode="side",
            description=description,
        )

    def _create_generic_world(
        self,
        world_type: str,
        mode_id: str,
        view_mode: str,
        name: str,
        config: Optional[Dict[str, Any]],
        seed: Optional[int],
        persistent: bool,
        description: str,
    ) -> WorldInstance:
        """Create a non-tank world directly."""
        world_id = str(uuid.uuid4())

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

        self._worlds[world_id] = instance
        logger.info(
            "Created %s world: %s (%s)",
            world_type,
            world_id[:8],
            name,
        )

        return instance

    def get_world(self, world_id: str) -> Optional[WorldInstance]:
        """Get a world instance by ID.

        Args:
            world_id: The unique world identifier

        Returns:
            The WorldInstance if found, None otherwise
        """
        # Check non-tank worlds first
        if world_id in self._worlds:
            return self._worlds[world_id]

        # Check tank registry
        if self._tank_registry is not None:
            tank_manager = self._tank_registry.get_tank(world_id)
            if tank_manager is not None:
                return WorldInstance(
                    world_id=world_id,
                    world_type="tank",
                    mode_id="tank",
                    name=tank_manager.name,
                    runner=tank_manager.runner,
                    persistent=tank_manager.persistent,
                    view_mode="side",
                    description=tank_manager.description,
                )

        return None

    def list_worlds(self, world_type: Optional[str] = None) -> List[WorldStatus]:
        """List all active worlds.

        Args:
            world_type: Optional filter by world type

        Returns:
            List of WorldStatus for all matching worlds
        """
        statuses: List[WorldStatus] = []

        # Include tank worlds from TankRegistry
        if self._tank_registry is not None and (world_type is None or world_type == "tank"):
            for tank_status in self._tank_registry.list_tanks():
                # tank_status has structure: {"tank": {...}, "running": ..., "frame": ..., ...}
                tank_info = tank_status.get("tank", {})
                statuses.append(
                    WorldStatus(
                        world_id=tank_info.get("tank_id", ""),
                        world_type="tank",
                        mode_id="tank",
                        name=tank_info.get("name", "Unknown"),
                        view_mode="side",
                        frame_count=tank_status.get("frame", 0),
                        paused=tank_status.get("paused", False),
                        persistent=tank_info.get("persistent", True),
                        created_at=tank_info.get("created_at", ""),
                        description=tank_info.get("description", ""),
                    )
                )

        # Include non-tank worlds
        for world_id, instance in self._worlds.items():
            if world_type is not None and instance.world_type != world_type:
                continue
            statuses.append(
                WorldStatus(
                    world_id=world_id,
                    world_type=instance.world_type,
                    mode_id=instance.mode_id,
                    name=instance.name,
                    view_mode=instance.view_mode,
                    frame_count=instance.runner.frame_count,
                    paused=instance.runner.paused,
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
        # Check non-tank worlds first
        if world_id in self._worlds:
            del self._worlds[world_id]
            logger.info("Deleted world: %s", world_id[:8])
            return True

        # Check tank registry
        if self._tank_registry is not None:
            if self._tank_registry.remove_tank(world_id, delete_persistent_data=True):
                logger.info("Deleted tank world: %s", world_id[:8])
                return True

        return False

    def step_world(self, world_id: str, actions: Optional[Dict[str, Any]] = None) -> bool:
        """Step a world by one frame.

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
        count = len(self._worlds)
        if self._tank_registry is not None:
            count += self._tank_registry.tank_count
        return count
