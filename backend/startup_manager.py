"""Backend startup and shutdown manager.

This module handles all server initialization and cleanup logic in a clean,
testable way. Previously this logic was scattered throughout the main.py
lifespan function, making it hard to maintain and test.
"""

import asyncio
import logging
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, Set

from backend.auto_save_service import AutoSaveService
from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.migration_scheduler import MigrationScheduler
from backend.models import ServerInfo
from backend.server_client import ServerClient
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


class StartupManager:
    """Manages server startup and shutdown lifecycle.

    This class encapsulates all initialization and cleanup logic for the
    backend server, providing a clean separation from the FastAPI application
    lifecycle. It handles:

    - World creation and restoration
    - Connection restoration
    - Service initialization (discovery, auto-save, migrations)
    - Broadcast task management
    - Graceful shutdown and cleanup

    Attributes:
        world_manager: Manager for all world instances
        connection_manager: Manager for inter-tank connections
        discovery_service: Service discovery for distributed servers
        server_client: Client for server-to-server communication
        server_id: Unique identifier for this server
        discovery_server_url: Optional URL of discovery hub server
    """

    def __init__(
        self,
        world_manager: WorldManager,
        connection_manager: ConnectionManager,
        discovery_service: DiscoveryService,
        server_client: ServerClient,
        server_id: str,
        discovery_server_url: Optional[str] = None,
        start_broadcast_callback: Optional[Callable[[Any, str], Any]] = None,
        stop_broadcast_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """Initialize the startup manager.

        Args:
            world_manager: World manager instance
            connection_manager: Connection manager instance
            discovery_service: Discovery service instance
            server_client: Server client instance
            server_id: Unique server identifier
            discovery_server_url: Optional discovery hub URL
            start_broadcast_callback: Callback to start broadcast for a world
            stop_broadcast_callback: Callback to stop broadcast for a world
        """
        self.world_manager = world_manager
        self.connection_manager = connection_manager
        self.discovery_service = discovery_service
        self.server_client = server_client
        self.server_id = server_id
        self.discovery_server_url = discovery_server_url
        self._start_broadcast_callback = start_broadcast_callback
        self._stop_broadcast_callback = stop_broadcast_callback

        # Services created during startup
        self.auto_save_service: Optional[AutoSaveService] = None
        self.migration_scheduler: Optional[MigrationScheduler] = None

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._broadcast_task_ids: Set[str] = set()  # Track which worlds have broadcast tasks

        # Parsed discovery hub info
        self._discovery_hub_info: Optional[ServerInfo] = None

        # Server metadata
        self._start_time = time.time()

    def get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self._start_time

    async def initialize(
        self,
        get_server_info_callback: Callable[[], ServerInfo],
    ) -> None:
        """Initialize all server components.

        This is the main startup method that orchestrates all initialization steps.

        Args:
            get_server_info_callback: Callback to get current server info

        Raises:
            Exception: If critical initialization steps fail
        """
        logger.info("=" * 60)
        logger.info("STARTUP: Beginning server initialization")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python: {sys.version}")
        logger.info("=" * 60)

        # Step 0: Pass broadcast callbacks to world_manager
        if self._start_broadcast_callback and self._stop_broadcast_callback:
            self.world_manager.set_broadcast_callbacks(
                self._start_broadcast_callback,
                self._stop_broadcast_callback,
            )

        # Step 1: Create default world if none exists
        await self._create_default_world()

        # Step 2: Restore connections
        await self._restore_connections()

        # Step 3: Start broadcast tasks for all worlds
        await self._start_broadcast_tasks()

        # Step 4: Start discovery service
        await self._start_discovery_service(get_server_info_callback)

        # Step 5: Start server client
        await self._start_server_client(get_server_info_callback)

        # Step 6: Start migration scheduler
        await self._start_migration_scheduler()

        # Step 7: Start auto-save service
        await self._start_auto_save_service()

        logger.info("STARTUP: Server initialization complete")

    async def shutdown(self) -> None:
        """Shutdown all server components gracefully.

        This method handles cleanup in reverse order of initialization.
        """
        logger.info("SHUTDOWN: Beginning graceful shutdown")

        # Step 0: Save all worlds before shutdown
        if self.auto_save_service:
            try:
                await self.auto_save_service.save_all_on_shutdown()
            except Exception as e:
                logger.error(f"Error saving worlds on shutdown: {e}", exc_info=True)

        # Step 1: Stop auto-save service
        await self._stop_auto_save_service()

        # Step 2: Stop broadcast tasks
        await self._stop_broadcast_tasks()

        # Step 3: Stop migration scheduler
        await self._stop_migration_scheduler()

        # Step 4: Stop all world simulations
        await self._stop_simulations()

        # Step 5: Stop heartbeat task
        await self._stop_heartbeat_task()

        # Step 6: Stop discovery service
        await self._stop_discovery_service()

        # Step 7: Stop server client
        await self._stop_server_client()

        logger.info("SHUTDOWN: Cleanup complete")
        logger.info("=" * 60)

    # =========================================================================
    # Startup Steps
    # =========================================================================

    async def _create_default_world(self) -> None:
        """Create a default tank world if no worlds exist, or restore from saved snapshots."""
        # First try to restore worlds from saved snapshots
        await self._restore_saved_worlds()

        if self.world_manager.world_count == 0:
            logger.info("No worlds in manager, creating default world...")
            self.world_manager.create_world(
                world_type="tank",
                name="World 1",
                description="Default fish tank simulation",
                persistent=True,
                start_paused=False,
            )
            logger.info(
                f"Created default world: {self.world_manager.default_world_id[:8] if self.world_manager.default_world_id else 'unknown'}"
            )

        logger.info(f"World manager has {self.world_manager.world_count} world(s)")

    async def _restore_saved_worlds(self) -> None:
        """Restore worlds from saved snapshots."""
        from backend.world_persistence import (find_all_world_snapshots,
                                               load_snapshot)

        try:
            world_snapshots = find_all_world_snapshots()
            if not world_snapshots:
                logger.info("No saved world snapshots found")
                return

            logger.info(f"Found {len(world_snapshots)} saved world(s) to restore")

            for world_id, snapshot_path in world_snapshots.items():
                try:
                    snapshot = load_snapshot(snapshot_path)
                    if snapshot:
                        # Create world and restore state
                        instance = self.world_manager.create_world(
                            world_type=snapshot.get("world_type", "tank"),
                            name=snapshot.get("tank_name", snapshot.get("name", "Restored World")),
                            description=snapshot.get("description", "Restored from snapshot"),
                            persistent=True,
                            start_paused=True,  # Start paused to allow clean restoration before loop runs
                            world_id=world_id,  # Preserve the original world ID
                        )
                        if instance:
                            # Restore entities and state into the world
                            from backend.world_persistence import \
                                restore_world_from_snapshot

                            success = restore_world_from_snapshot(snapshot, instance.runner.world)
                            if success:
                                logger.info(f"Restored world {world_id[:8]} from snapshot")
                            else:
                                logger.error(
                                    f"Failed to restore world {world_id[:8]} - initializing fresh world"
                                )
                                # Rename corrupt snapshot to prevent reload loop
                                try:
                                    corrupt_path = (
                                        Path(snapshot_path).parent
                                        / f"CORRUPT_{Path(snapshot_path).name}"
                                    )
                                    Path(snapshot_path).rename(corrupt_path)
                                    logger.warning(
                                        f"Renamed corrupt snapshot to {corrupt_path.name}"
                                    )
                                except Exception as rename_err:
                                    logger.error(f"Failed to rename corrupt snapshot: {rename_err}")

                                # Reset instance to fresh (factory defaults)
                                # This ensures we don't start with a half-broken state
                                instance.runner.world.reset(seed=instance.runner.world._seed)
                                logger.info(f"Reset world {world_id[:8]} to fresh state")
                except Exception as e:
                    logger.error(f"Failed to restore world {world_id[:8]}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error during world restoration: {e}", exc_info=True)

    async def _restore_connections(self) -> None:
        """Restore tank connections from saved file."""
        logger.info("Restoring connections...")
        try:
            from backend.connection_persistence import load_connections

            restored_connections = load_connections(self.connection_manager)
            logger.info(f"Restored {restored_connections} connection(s)")
        except Exception as e:
            logger.error(f"Error restoring connections: {e}", exc_info=True)
            logger.info("Continuing without restored connections")

    async def _start_broadcast_tasks(self) -> None:
        """Start broadcast tasks for all worlds."""
        logger.info("Starting broadcast tasks...")
        if not self._start_broadcast_callback:
            logger.warning("No broadcast callback configured, skipping broadcast tasks")
            return

        try:
            for instance in self.world_manager:
                # Use the shared broadcast adapter to ensure clients and broadcast task use the same instance
                adapter = self.world_manager.get_broadcast_adapter(instance.world_id)
                if adapter:
                    await self._start_broadcast_callback(adapter, instance.world_id)
                    self._broadcast_task_ids.add(instance.world_id)
                    logger.info(f"Broadcast task started for world {instance.world_id[:8]}")
                else:
                    logger.warning(
                        f"Could not create broadcast adapter for world {instance.world_id[:8]}"
                    )
        except Exception as e:
            logger.error(f"Failed to start broadcast tasks: {e}", exc_info=True)
            raise

    async def _start_discovery_service(
        self, get_server_info_callback: Callable[[], ServerInfo]
    ) -> None:
        """Start discovery service and heartbeat loop."""
        logger.info("Starting discovery service...")
        try:
            await self.discovery_service.start()
            logger.info("Discovery service started")

            # Register local server
            local_server_info = get_server_info_callback()
            await self.discovery_service.register_server(local_server_info)
            logger.info(f"Local server registered: {self.server_id}")

            # Parse discovery hub URL if provided
            if self.discovery_server_url:
                self._discovery_hub_info = self._parse_discovery_url(self.discovery_server_url)
                if self._discovery_hub_info:
                    logger.info(
                        f"Discovery hub configured: "
                        f"{self._discovery_hub_info.host}:{self._discovery_hub_info.port}"
                    )
                else:
                    logger.warning(
                        f"Failed to parse DISCOVERY_SERVER_URL: {self.discovery_server_url}"
                    )

            # Start heartbeat loop
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(get_server_info_callback)
            )
            self._heartbeat_task.add_done_callback(self._handle_task_exception)
            logger.info("Heartbeat task started")

        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}", exc_info=True)
            # Non-fatal - continue without discovery

    async def _start_server_client(
        self, get_server_info_callback: Callable[[], ServerInfo]
    ) -> None:
        """Start server client and register with discovery hub."""
        logger.info("Starting server client...")
        try:
            await self.server_client.start()
            logger.info("Server client started")
        except Exception as e:
            logger.error(f"Failed to start server client: {e}", exc_info=True)
            # Non-fatal - continue without server client

        # Register with remote discovery hub if configured
        if self._discovery_hub_info:
            logger.info("Registering with remote discovery hub...")
            try:
                local_server_info = get_server_info_callback()
                success = await self.server_client.register_server(
                    self._discovery_hub_info, local_server_info
                )
                if success:
                    logger.info(
                        f"Successfully registered with discovery hub at "
                        f"{self._discovery_hub_info.host}:{self._discovery_hub_info.port}"
                    )
                else:
                    logger.warning(
                        f"Failed to register with discovery hub at "
                        f"{self._discovery_hub_info.host}:{self._discovery_hub_info.port}"
                    )
            except Exception as e:
                logger.error(f"Error registering with discovery hub: {e}", exc_info=True)
                # Non-fatal - continue without hub registration

    async def _start_migration_scheduler(self) -> None:
        """Start migration scheduler for automated entity migrations."""
        logger.info("Starting migration scheduler...")
        try:
            self.migration_scheduler = MigrationScheduler(
                connection_manager=self.connection_manager,
                world_manager=self.world_manager,
                check_interval=2.0,
                discovery_service=self.discovery_service,
                server_client=self.server_client,
                local_server_id=self.server_id,
            )
            await self.migration_scheduler.start()
            logger.info("Migration scheduler started")
        except Exception as e:
            logger.error(f"Failed to start migration scheduler: {e}", exc_info=True)
            # Non-fatal - continue without automated migrations

    async def _start_auto_save_service(self) -> None:
        """Start auto-save service for periodic world persistence."""
        logger.info("Starting auto-save service...")
        try:
            self.auto_save_service = AutoSaveService(self.world_manager)
            await self.auto_save_service.start()
            logger.info("Auto-save service started")
        except Exception as e:
            logger.error(f"Failed to start auto-save service: {e}", exc_info=True)
            # Non-fatal - continue without auto-save

    # =========================================================================
    # Shutdown Steps
    # =========================================================================

    async def _stop_auto_save_service(self) -> None:
        """Stop auto-save service."""
        logger.info("Stopping auto-save service...")
        if self.auto_save_service:
            try:
                await self.auto_save_service.stop()
                logger.info("Auto-save service stopped")
            except Exception as e:
                logger.error(f"Error stopping auto-save service: {e}", exc_info=True)

    async def _stop_broadcast_tasks(self) -> None:
        """Stop all broadcast tasks."""
        logger.info("Stopping broadcast tasks...")
        if not self._stop_broadcast_callback:
            logger.warning("No broadcast stop callback configured")
            return

        for world_id in list(self._broadcast_task_ids):
            try:
                await self._stop_broadcast_callback(world_id)
                logger.info(f"Broadcast task stopped for world {world_id[:8]}")
            except Exception as e:
                logger.error(
                    f"Error stopping broadcast for world {world_id[:8]}: {e}",
                    exc_info=True,
                )
        self._broadcast_task_ids.clear()

    async def _stop_migration_scheduler(self) -> None:
        """Stop migration scheduler."""
        logger.info("Stopping migration scheduler...")
        if self.migration_scheduler:
            try:
                await self.migration_scheduler.stop()
                logger.info("Migration scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping migration scheduler: {e}", exc_info=True)

    async def _stop_simulations(self) -> None:
        """Stop all world simulations."""
        logger.info("Stopping all simulations...")
        try:
            self.world_manager.stop_all_worlds()
            logger.info("All simulations stopped!")
        except Exception as e:
            logger.error(f"Error stopping simulations: {e}", exc_info=True)

    async def _stop_heartbeat_task(self) -> None:
        """Stop heartbeat background task."""
        logger.info("Stopping heartbeat task...")
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("Heartbeat task stopped")

    async def _stop_discovery_service(self) -> None:
        """Stop discovery service."""
        logger.info("Stopping discovery service...")
        try:
            await self.discovery_service.stop()
            logger.info("Discovery service stopped")
        except Exception as e:
            logger.error(f"Error stopping discovery service: {e}", exc_info=True)

    async def _stop_server_client(self) -> None:
        """Stop server client."""
        logger.info("Stopping server client...")
        try:
            await self.server_client.close()
            logger.info("Server client stopped")
        except Exception as e:
            logger.error(f"Error stopping server client: {e}", exc_info=True)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_discovery_url(self, url: str) -> Optional[ServerInfo]:
        """Parse DISCOVERY_SERVER_URL into a ServerInfo object.

        Args:
            url: Discovery server URL (e.g., "http://192.168.1.10:8000")

        Returns:
            ServerInfo for the discovery server, or None if invalid
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)

            if not parsed.hostname:
                logger.error(f"Invalid DISCOVERY_SERVER_URL: {url} (no hostname)")
                return None

            port = parsed.port or 8000

            # Create a minimal ServerInfo for the discovery hub
            return ServerInfo(
                server_id="discovery-hub",
                hostname=parsed.hostname,
                host=parsed.hostname,
                port=port,
                status="online",
                world_count=0,
                version="unknown",
                is_local=False,
            )
        except Exception as e:
            logger.error(f"Failed to parse DISCOVERY_SERVER_URL: {url} - {e}")
            return None

    @staticmethod
    def _handle_task_exception(task: asyncio.Task) -> None:
        """Handle exceptions from background tasks."""
        try:
            exc = task.exception()
            if exc is not None:
                logger.error(
                    f"Unhandled exception in task {task.get_name()}: {exc}",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
        except asyncio.CancelledError:
            logger.debug(f"Task {task.get_name()} was cancelled")
        except Exception as e:
            logger.error(f"Error getting task exception: {e}", exc_info=True)

    async def _heartbeat_loop(self, get_server_info_callback: Callable[[], ServerInfo]) -> None:
        """Background task to send periodic heartbeats to discovery service."""
        while True:
            try:
                await asyncio.sleep(DiscoveryService.HEARTBEAT_INTERVAL)

                # Update local server info and send heartbeat
                server_info = get_server_info_callback()
                await self.discovery_service.heartbeat(self.server_id, server_info)
                logger.debug("Heartbeat sent to local discovery service")

                # Also send heartbeat to remote discovery hub if configured
                if self._discovery_hub_info:
                    try:
                        success = await self.server_client.send_heartbeat(
                            self._discovery_hub_info, server_info
                        )
                        if success:
                            logger.debug(
                                f"Heartbeat sent to remote discovery hub at "
                                f"{self._discovery_hub_info.host}:{self._discovery_hub_info.port}"
                            )
                        else:
                            logger.warning(
                                f"Failed to send heartbeat to discovery hub at "
                                f"{self._discovery_hub_info.host}:{self._discovery_hub_info.port}"
                            )
                    except Exception as e:
                        logger.warning(f"Error sending heartbeat to discovery hub: {e}")

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
