"""Tank registry for managing multiple tank simulations.

This module provides the TankRegistry class which manages multiple
SimulationManager instances for Tank World Net. It supports creating,
listing, accessing, and removing tanks both locally and across remote servers.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.simulation_manager import SimulationManager

if TYPE_CHECKING:
    from backend.discovery_service import DiscoveryService
    from backend.server_client import ServerClient

logger = logging.getLogger(__name__)


@dataclass
class CreateTankRequest:
    """Request to create a new tank."""

    name: str
    description: str = ""
    seed: Optional[int] = None
    owner: Optional[str] = None
    is_public: bool = True
    allow_transfers: bool = True
    persistent: bool = True
    auto_save_interval: float = 300.0
    tank_id: Optional[str] = None  # Optional for restoring existing tanks


class TankRegistry:
    """Registry for managing multiple tank simulations.

    This class provides a centralized way to manage multiple SimulationManager
    instances. Each tank is identified by a unique tank_id and can be accessed,
    listed, or removed through this registry.

    The registry supports:
    - Creating new tanks with custom configurations
    - Listing all tanks (optionally filtered by public visibility)
    - Accessing individual tanks by ID
    - Removing tanks and cleaning up their resources
    - Getting a default tank for backwards compatibility
    """

    def __init__(
        self,
        create_default: bool = True,
        discovery_service: Optional["DiscoveryService"] = None,
        server_client: Optional["ServerClient"] = None,
        local_server_id: str = "local-server",
    ):
        """Initialize the tank registry.

        Args:
            create_default: If True, creates a default "Tank 1" on init
            discovery_service: Optional discovery service for distributed lookups
            server_client: Optional server client for remote queries
            local_server_id: ID of the local server for distributed lookups
        """
        self._tanks: Dict[str, SimulationManager] = {}
        self._default_tank_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._discovery_service = discovery_service
        self._server_client = server_client
        self._connection_manager = None
        self._local_server_id = local_server_id

        if create_default:
            default_tank = self.create_tank(
                name="Tank 1",
                description="A local fish tank simulation",
            )
            self._default_tank_id = default_tank.tank_id
            logger.info(
                "TankRegistry initialized with default tank: %s",
                self._default_tank_id,
            )
        else:
            logger.info("TankRegistry initialized (no default tank)")

    def set_distributed_services(
        self,
        discovery_service: "DiscoveryService",
        server_client: "ServerClient",
    ) -> None:
        """Set the discovery service and server client for distributed operations.

        Args:
            discovery_service: Discovery service instance
            server_client: Server client instance
        """
        self._discovery_service = discovery_service
        self._server_client = server_client
        logger.info("TankRegistry distributed services configured")

    def set_connection_manager(self, connection_manager: Any) -> None:
        """Set the connection manager for handling tank connections.

        Args:
            connection_manager: ConnectionManager instance
        """
        self._connection_manager = connection_manager
        logger.info("TankRegistry connection manager configured")

    @property
    def tank_count(self) -> int:
        """Get the number of tanks in the registry."""
        return len(self._tanks)

    @property
    def default_tank_id(self) -> Optional[str]:
        """Get the default tank ID."""
        return self._default_tank_id

    @property
    def default_tank(self) -> Optional[SimulationManager]:
        """Get the default tank manager."""
        if self._default_tank_id:
            return self._tanks.get(self._default_tank_id)
        return None

    def create_tank(
        self,
        name: str,
        description: str = "",
        seed: Optional[int] = None,
        owner: Optional[str] = None,
        is_public: bool = True,
        allow_transfers: bool = True,
        server_id: str = "local-server",
        persistent: bool = True,
        auto_save_interval: float = 300.0,
    ) -> SimulationManager:
        """Create a new tank and add it to the registry.

        Args:
            name: Human-readable name for the tank
            description: Description of the tank
            seed: Optional random seed for deterministic behavior
            owner: Optional owner identifier
            is_public: Whether the tank is publicly visible
            allow_transfers: Whether to allow entity transfers
            server_id: Which server this tank should run on (default: local-server)
            persistent: Whether this tank should auto-save and restore
            auto_save_interval: Auto-save interval in seconds (default: 5 minutes)

        Returns:
            The newly created SimulationManager
        """
        manager = SimulationManager(
            tank_name=name,
            tank_description=description,
            seed=seed,
            persistent=persistent,
            auto_save_interval=auto_save_interval,
        )

        # Update tank info with additional fields
        manager.tank_info.owner = owner
        manager.tank_info.is_public = is_public
        manager.tank_info.allow_transfers = allow_transfers
        manager.tank_info.server_id = server_id

        self._tanks[manager.tank_id] = manager

        logger.info(
            "Created tank: id=%s, name=%s, owner=%s, public=%s, server=%s, persistent=%s",
            manager.tank_id,
            name,
            owner,
            is_public,
            server_id,
            persistent,
        )

        return manager

    def get_tank(self, tank_id: str) -> Optional[SimulationManager]:
        """Get a tank by its ID.

        Args:
            tank_id: The unique tank identifier

        Returns:
            The SimulationManager if found, None otherwise
        """
        return self._tanks.get(tank_id)

    def get_tank_or_default(self, tank_id: Optional[str] = None) -> Optional[SimulationManager]:
        """Get a tank by ID, or return the default tank.

        Args:
            tank_id: Optional tank ID. If None or not found, returns default.

        Returns:
            The SimulationManager for the specified or default tank
        """
        if tank_id:
            tank = self._tanks.get(tank_id)
            if tank:
                return tank
        return self.default_tank

    def list_tanks(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """List all tanks in the registry.

        Args:
            include_private: If True, include non-public tanks

        Returns:
            List of tank status dictionaries
        """
        tanks = []
        for manager in self._tanks.values():
            if include_private or manager.tank_info.is_public:
                tanks.append(manager.get_status())
        return tanks

    def list_tank_ids(self) -> List[str]:
        """Get a list of all tank IDs.

        Returns:
            List of tank IDs
        """
        return list(self._tanks.keys())

    def remove_tank(self, tank_id: str, delete_persistent_data: bool = False) -> bool:
        """Remove a tank from the registry and clean up resources.

        Args:
            tank_id: The tank ID to remove
            delete_persistent_data: Whether to delete any persisted tank data

        Returns:
            True if the tank was removed, False if not found
        """
        manager = self._tanks.pop(tank_id, None)
        if manager is None:
            logger.warning("Attempted to remove non-existent tank: %s", tank_id)
            return False

        # Stop the simulation if running
        if manager.running:
            manager.stop()

        # Clear the default tank reference if needed
        if self._default_tank_id == tank_id:
            self._default_tank_id = None
            # Set a new default if other tanks exist
            if self._tanks:
                self._default_tank_id = next(iter(self._tanks.keys()))
                logger.info("New default tank: %s", self._default_tank_id)

        # Remove associated connections if connection manager is available
        if self._connection_manager:
            self._connection_manager.clear_connections_for_tank(tank_id)

        if delete_persistent_data:
            try:
                from backend.tank_persistence import delete_tank_data

                deleted = delete_tank_data(tank_id)
                if deleted:
                    logger.info("Deleted persisted data for tank: %s", tank_id)
            except Exception as e:
                logger.warning(
                    "Failed to delete persisted data for tank %s: %s", tank_id, e
                )

        logger.info("Removed tank: %s", tank_id)
        return True

    def start_all(self, start_paused: bool = False) -> None:
        """Start all tanks in the registry.

        Args:
            start_paused: Whether to start tanks in paused state
        """
        for manager in self._tanks.values():
            if not manager.running:
                manager.start(start_paused=start_paused)

    def stop_all(self) -> None:
        """Stop all tanks in the registry."""
        for manager in self._tanks.values():
            if manager.running:
                manager.stop()

    def __contains__(self, tank_id: str) -> bool:
        """Check if a tank ID exists in the registry."""
        return tank_id in self._tanks

    def __len__(self) -> int:
        """Get the number of tanks."""
        return len(self._tanks)

    def __iter__(self):
        """Iterate over tank managers."""
        return iter(self._tanks.values())

    def restore_tank_from_snapshot(
        self,
        snapshot_path: str,
        start_paused: bool = True,
    ) -> Optional[SimulationManager]:
        """Restore a tank from a snapshot file.

        Args:
            snapshot_path: Path to the snapshot file
            start_paused: Whether to start the tank in paused state

        Returns:
            The restored SimulationManager, or None if restoration failed
        """
        from backend.tank_persistence import load_tank_state, restore_tank_from_snapshot

        # Load snapshot data
        snapshot = load_tank_state(snapshot_path)
        if snapshot is None:
            logger.error(f"Failed to load snapshot: {snapshot_path}")
            return None

        # Extract metadata
        tank_id = snapshot["tank_id"]
        metadata = snapshot["metadata"]

        # Check if tank already exists
        if tank_id in self._tanks:
            logger.warning(f"Tank {tank_id[:8]} already exists, skipping restore")
            return self._tanks[tank_id]

        # Create new tank with same ID and metadata
        manager = SimulationManager(
            tank_name=metadata["name"],
            tank_description=metadata.get("description", ""),
            seed=metadata.get("seed"),
            persistent=True,  # Restored tanks are persistent by default
            auto_save_interval=300.0,
        )

        # Override the tank_id to match the snapshot
        manager.tank_info.tank_id = tank_id
        manager.tank_info.owner = metadata.get("owner")
        manager.tank_info.is_public = metadata.get("is_public", True)
        manager.tank_info.allow_transfers = metadata.get("allow_transfers", True)
        manager.tank_info.server_id = metadata.get("server_id", "local-server")

        # Keep runner identity consistent with restored tank metadata (important for per-tank persistence)
        try:
            manager.runner.set_tank_identity(tank_id=tank_id, tank_name=metadata.get("name"))
        except Exception:
            # Restoration should still succeed even if runner identity update fails
            logger.exception("Failed to update runner tank identity during restore for %s", tank_id[:8])

        # Restore state into the tank
        if not restore_tank_from_snapshot(snapshot, manager.world):
            logger.error(f"Failed to restore tank state from {snapshot_path}")
            return None

        # Add to registry
        self._tanks[tank_id] = manager

        logger.info(
            f"Restored tank {tank_id[:8]} from snapshot "
            f"(frame: {snapshot['frame']}, entities: {len(snapshot['entities'])})"
        )

        return manager

    # =========================================================================
    # Distributed Tank Queries
    # =========================================================================

    async def find_tank_server(self, tank_id: str) -> Optional[str]:
        """Find which server hosts a specific tank.

        Args:
            tank_id: Tank ID to search for

        Returns:
            Server ID if found, None otherwise
        """
        # Check local first
        if tank_id in self._tanks:
            return self._local_server_id

        # Check remote servers if distributed services available
        if self._discovery_service and self._server_client:
            try:
                servers = await self._discovery_service.get_online_servers()

                for server in servers:
                    if server.is_local:
                        continue

                    # Query remote server for this tank
                    tank_info = await self._server_client.get_tank(server, tank_id)
                    if tank_info is not None:
                        return server.server_id

            except Exception as e:
                logger.error(f"Error searching for tank {tank_id}: {e}")

        return None

    async def get_tank_distributed(
        self,
        tank_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get tank information from local or remote servers.

        Args:
            tank_id: Tank ID to look up

        Returns:
            Tank info dictionary if found, None otherwise
        """
        # Check local first
        manager = self._tanks.get(tank_id)
        if manager:
            return manager.get_status()

        # Check remote servers if distributed services available
        if self._discovery_service and self._server_client:
            try:
                servers = await self._discovery_service.get_online_servers()

                for server in servers:
                    if server.is_local:
                        continue

                    # Query remote server for this tank
                    tank_info = await self._server_client.get_tank(server, tank_id)
                    if tank_info is not None:
                        return tank_info

            except Exception as e:
                logger.error(f"Error fetching tank {tank_id}: {e}")

        return None

    async def list_tanks_distributed(
        self,
        include_private: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """List all tanks across all servers.

        Args:
            include_private: If True, include non-public tanks

        Returns:
            Dictionary mapping server_id to list of tank info dictionaries
        """
        result = {}

        # Add local tanks
        local_tanks = self.list_tanks(include_private=include_private)
        if local_tanks:
            result["local-server"] = local_tanks

        # Add remote tanks if distributed services available
        if self._discovery_service and self._server_client:
            try:
                servers = await self._discovery_service.get_online_servers()

                for server in servers:
                    if server.is_local:
                        continue

                    try:
                        remote_tanks = await self._server_client.list_tanks(server)
                        if remote_tanks:
                            # Filter private tanks if needed
                            if not include_private:
                                remote_tanks = [
                                    t for t in remote_tanks
                                    if t.get("is_public", True)
                                ]
                            result[server.server_id] = remote_tanks
                    except Exception as e:
                        logger.error(
                            f"Error fetching tanks from {server.server_id}: {e}"
                        )

            except Exception as e:
                logger.error(f"Error listing distributed tanks: {e}")

        return result
