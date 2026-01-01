"""Central manager for active world instances across all types.

This module provides the WorldManager class which manages active world instances
for all world types (tank, petri, soccer) through a unified pipeline.

All world types now flow through the same creation/loop/broadcast path:
WorldManager → WorldInstance → Runner → Broadcast

Tank worlds use TankWorldAdapter which wraps SimulationManager to provide
the same interface as WorldRunner.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional, Union

from backend.world_registry import create_world, get_all_world_metadata, get_world_metadata
from backend.world_runner import WorldRunner

if TYPE_CHECKING:
    from backend.tank_registry import TankRegistry
    from backend.tank_world_adapter import TankWorldAdapter

logger = logging.getLogger(__name__)

# Type alias for broadcast callbacks
BroadcastCallback = Callable[..., Coroutine[Any, Any, Any]]

# Union type for all runner types (WorldRunner or TankWorldAdapter)
AnyRunner = Union["WorldRunner", "TankWorldAdapter"]


@dataclass
class WorldInstance:
    """Represents an active world instance.

    This is the unified container for all world types. The runner field
    can be either a WorldRunner (for petri/soccer) or a TankWorldAdapter
    (for tank). Both expose compatible interfaces.
    """

    world_id: str
    world_type: str
    mode_id: str
    name: str
    runner: AnyRunner
    created_at: datetime = field(default_factory=datetime.now)
    persistent: bool = True
    view_mode: str = "side"
    description: str = ""

    def is_tank(self) -> bool:
        """Check if this is a tank world."""
        return self.world_type == "tank"


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

    This class provides unified management of world instances across all world
    types (tank, petri, soccer). All worlds are stored in a single dictionary
    and accessed through the same interface.

    For tank worlds, a TankWorldAdapter wraps the existing SimulationManager
    to provide the same interface as WorldRunner, enabling tanks to run through
    the same pipeline as other world types.

    Attributes:
        _worlds: Dictionary of all world instances by world_id
        _tank_registry: Reference to TankRegistry for tank-specific operations
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

    @property
    def tank_registry(self) -> Optional["TankRegistry"]:
        """Get the tank registry for tank-specific operations."""
        return self._tank_registry

    def set_tank_registry(self, tank_registry: "TankRegistry") -> None:
        """Set the tank registry for tank world operations.

        Also registers any existing tanks from the registry as world instances.
        """
        self._tank_registry = tank_registry
        # Register existing tanks as world instances
        self._sync_tanks_from_registry()

    def _sync_tanks_from_registry(self) -> None:
        """Synchronize tank worlds from TankRegistry into _worlds dict.

        This ensures all tanks managed by TankRegistry are accessible through
        the unified WorldManager interface.
        """
        if self._tank_registry is None:
            return

        from backend.tank_world_adapter import TankWorldAdapter

        for manager in self._tank_registry:
            tank_id = manager.tank_id
            if tank_id not in self._worlds:
                adapter = TankWorldAdapter(manager)
                instance = WorldInstance(
                    world_id=tank_id,
                    world_type="tank",
                    mode_id="tank",
                    name=manager.tank_info.name,
                    runner=adapter,
                    created_at=manager.tank_info.created_at,
                    persistent=manager.tank_info.persistent,
                    view_mode="side",
                    description=manager.tank_info.description,
                )
                self._worlds[tank_id] = instance
                logger.debug("Synced tank world from registry: %s", tank_id[:8])

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

        All world types flow through this unified creation path. Tank worlds
        are created through TankRegistry and wrapped with TankWorldAdapter.
        Other worlds are created directly with WorldRunner.

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

        # Unified creation path - dispatch by world type
        if world_type == "tank":
            return self._create_tank_world(name, config, seed, persistent, description)

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
        """Create a tank world through TankRegistry with TankWorldAdapter.

        The tank is created through TankRegistry (preserving tank-specific
        functionality), then wrapped with TankWorldAdapter and stored in
        the unified _worlds dictionary.
        """
        if self._tank_registry is None:
            raise RuntimeError("TankRegistry not available for tank world creation")

        from backend.tank_world_adapter import TankWorldAdapter

        # Create tank through registry (handles SimulationManager creation)
        manager = self._tank_registry.create_tank(
            name=name,
            description=description,
            seed=seed,
            persistent=persistent,
        )

        # Start the simulation
        manager.start(start_paused=False)

        # Wrap with adapter for unified interface
        adapter = TankWorldAdapter(manager)

        # Create unified WorldInstance
        instance = WorldInstance(
            world_id=manager.tank_id,
            world_type="tank",
            mode_id="tank",
            name=name,
            runner=adapter,
            created_at=manager.tank_info.created_at,
            persistent=persistent,
            view_mode="side",
            description=description,
        )

        # Store in unified worlds dict
        self._worlds[manager.tank_id] = instance

        logger.info(
            "Created tank world: %s (%s)",
            manager.tank_id[:8],
            name,
        )

        return instance

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
        """Create a non-tank world with WorldRunner."""
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

        # Store in unified worlds dict
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

        All worlds (tank, petri, soccer) are retrieved from the unified
        _worlds dictionary.

        Args:
            world_id: The unique world identifier

        Returns:
            The WorldInstance if found, None otherwise
        """
        # First check if it's in our unified dict
        if world_id in self._worlds:
            return self._worlds[world_id]

        # For backward compatibility, check TankRegistry and sync if found
        if self._tank_registry is not None:
            tank_manager = self._tank_registry.get_tank(world_id)
            if tank_manager is not None:
                from backend.tank_world_adapter import TankWorldAdapter

                adapter = TankWorldAdapter(tank_manager)
                instance = WorldInstance(
                    world_id=world_id,
                    world_type="tank",
                    mode_id="tank",
                    name=tank_manager.tank_info.name,
                    runner=adapter,
                    created_at=tank_manager.tank_info.created_at,
                    persistent=tank_manager.tank_info.persistent,
                    view_mode="side",
                    description=tank_manager.tank_info.description,
                )
                # Cache in _worlds for future lookups
                self._worlds[world_id] = instance
                return instance

        return None

    def get_tank_adapter(self, world_id: str) -> Optional["TankWorldAdapter"]:
        """Get the TankWorldAdapter for a tank world.

        This is a convenience method for code that needs tank-specific
        functionality not exposed through the generic interface.

        Args:
            world_id: The tank world ID

        Returns:
            The TankWorldAdapter if found and world is a tank, None otherwise
        """
        instance = self.get_world(world_id)
        if instance is not None and instance.is_tank():
            from backend.tank_world_adapter import TankWorldAdapter
            if isinstance(instance.runner, TankWorldAdapter):
                return instance.runner
        return None

    def list_worlds(self, world_type: Optional[str] = None) -> List[WorldStatus]:
        """List all active worlds.

        Args:
            world_type: Optional filter by world type

        Returns:
            List of WorldStatus for all matching worlds
        """
        # Sync tanks from registry first to ensure we have all worlds
        self._sync_tanks_from_registry()

        statuses: List[WorldStatus] = []

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

        For tank worlds, also removes from TankRegistry and cleans up
        persistent data.

        Args:
            world_id: The world ID to delete

        Returns:
            True if deleted, False if not found
        """
        instance = self._worlds.pop(world_id, None)

        if instance is not None:
            # For tank worlds, also remove from TankRegistry
            if instance.is_tank() and self._tank_registry is not None:
                self._tank_registry.remove_tank(world_id, delete_persistent_data=True)

            logger.info("Deleted world: %s (%s)", world_id[:8], instance.world_type)
            return True

        # Backward compat: check if it's a tank not yet synced
        if self._tank_registry is not None:
            if self._tank_registry.remove_tank(world_id, delete_persistent_data=True):
                logger.info("Deleted tank world: %s", world_id[:8])
                return True

        return False

    def step_world(self, world_id: str, actions: Optional[Dict[str, Any]] = None) -> bool:
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
        # Sync to ensure we count all tanks
        self._sync_tanks_from_registry()
        return len(self._worlds)

    def get_all_worlds(self) -> Dict[str, WorldInstance]:
        """Get all world instances.

        Returns:
            Dictionary of world_id to WorldInstance
        """
        self._sync_tanks_from_registry()
        return dict(self._worlds)

    # =========================================================================
    # Persistence support
    # =========================================================================

    def capture_world_state(self, world_id: str) -> Optional[Dict[str, Any]]:
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

        # Tank worlds have their own capture method
        if instance.is_tank():
            from backend.tank_world_adapter import TankWorldAdapter
            if isinstance(instance.runner, TankWorldAdapter):
                return instance.runner.capture_state_for_save()

        # Other world types don't support persistence yet
        return None

    # =========================================================================
    # Tank-specific operations (for backward compatibility)
    # =========================================================================

    def get_tank_or_default(self, tank_id: Optional[str] = None) -> Optional["TankWorldAdapter"]:
        """Get a tank adapter by ID or return the default tank.

        This is for backward compatibility with code that expects to work
        with SimulationManager directly.

        Args:
            tank_id: Optional tank ID. If None, returns default tank.

        Returns:
            TankWorldAdapter for the specified or default tank
        """
        if self._tank_registry is None:
            return None

        manager = self._tank_registry.get_tank_or_default(tank_id)
        if manager is None:
            return None

        from backend.tank_world_adapter import TankWorldAdapter

        # Get or create the adapter
        instance = self.get_world(manager.tank_id)
        if instance is not None and isinstance(instance.runner, TankWorldAdapter):
            return instance.runner

        # Create adapter if not found
        return TankWorldAdapter(manager)
