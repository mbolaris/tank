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
from typing import Any, Callable, Optional, Set

from backend.auto_save_service import AutoSaveService
from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.migration_scheduler import MigrationScheduler
from backend.models import ServerInfo
from backend.server_client import ServerClient
from backend.simulation_manager import SimulationManager
from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


class StartupManager:
    """Manages server startup and shutdown lifecycle.

    This class encapsulates all initialization and cleanup logic for the
    backend server, providing a clean separation from the FastAPI application
    lifecycle. It handles:

    - Tank restoration from snapshots
    - Connection restoration
    - Service initialization (discovery, auto-save, migrations)
    - Broadcast task management
    - Graceful shutdown and cleanup

    Attributes:
        tank_registry: Registry of all tank simulations
        connection_manager: Manager for inter-tank connections
        discovery_service: Service discovery for distributed servers
        server_client: Client for server-to-server communication
        server_id: Unique identifier for this server
        discovery_server_url: Optional URL of discovery hub server
    """

    def __init__(
        self,
        tank_registry: TankRegistry,
        connection_manager: ConnectionManager,
        discovery_service: DiscoveryService,
        server_client: ServerClient,
        server_id: str,
        discovery_server_url: Optional[str] = None,
        start_broadcast_callback: Optional[Callable[[SimulationManager], Any]] = None,
        stop_broadcast_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """Initialize the startup manager.

        Args:
            tank_registry: Tank registry instance
            connection_manager: Connection manager instance
            discovery_service: Discovery service instance
            server_client: Server client instance
            server_id: Unique server identifier
            discovery_server_url: Optional discovery hub URL
            start_broadcast_callback: Callback to start broadcast for a tank
            stop_broadcast_callback: Callback to stop broadcast for a tank
        """
        self.tank_registry = tank_registry
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
        self._broadcast_task_ids: Set[str] = set()  # Track which tanks have broadcast tasks

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

        # Step 1: Restore tanks from snapshots
        await self._restore_tanks()

        # Step 2: Restore connections
        await self._restore_connections()

        # Step 3: Start tank simulations
        await self._start_simulations()

        # Step 4: Start broadcast tasks
        await self._start_broadcast_tasks()

        # Step 5: Start discovery service
        await self._start_discovery_service(get_server_info_callback)

        # Step 6: Start server client
        await self._start_server_client(get_server_info_callback)

        # Step 7: Configure distributed services
        await self._configure_distributed_services()

        # Step 8: Start migration scheduler
        await self._start_migration_scheduler()

        # Step 9: Start auto-save service
        await self._start_auto_save_service()

        logger.info("STARTUP: Server initialization complete")

    async def shutdown(self) -> None:
        """Shutdown all server components gracefully.

        This method handles cleanup in reverse order of initialization.
        """
        logger.info("SHUTDOWN: Beginning graceful shutdown")

        # Step 1: Save all persistent tanks
        await self._save_all_tanks()

        # Step 2: Save connections
        await self._save_connections()

        # Step 3: Stop auto-save service
        await self._stop_auto_save_service()

        # Step 4: Stop broadcast tasks
        await self._stop_broadcast_tasks()

        # Step 5: Stop migration scheduler
        await self._stop_migration_scheduler()

        # Step 6: Stop all simulations
        await self._stop_simulations()

        # Step 7: Stop heartbeat task
        await self._stop_heartbeat_task()

        # Step 8: Stop discovery service
        await self._stop_discovery_service()

        # Step 9: Stop server client
        await self._stop_server_client()

        logger.info("SHUTDOWN: Cleanup complete")
        logger.info("=" * 60)

    # =========================================================================
    # Startup Steps
    # =========================================================================

    async def _restore_tanks(self) -> None:
        """Restore tanks from saved snapshots."""
        logger.info("Checking for saved tank snapshots...")
        try:
            from backend.tank_persistence import find_all_tank_snapshots

            tank_snapshots = find_all_tank_snapshots()
            if tank_snapshots:
                logger.info(f"Found {len(tank_snapshots)} tank(s) with saved snapshots")
                for tank_id, snapshot_path in tank_snapshots.items():
                    logger.info(f"Restoring tank {tank_id[:8]} from {snapshot_path}")
                    restored_manager = self.tank_registry.restore_tank_from_snapshot(
                        snapshot_path,
                        start_paused=False,
                    )
                    if restored_manager:
                        logger.info(f"Successfully restored tank {tank_id[:8]}")
                        # Set as default if it's the first tank
                        if self.tank_registry._default_tank_id is None:
                            self.tank_registry._default_tank_id = tank_id
                    else:
                        logger.error(f"Failed to restore tank {tank_id[:8]}")
            else:
                logger.info("No saved snapshots found, will create default tank")
        except Exception as e:
            logger.error(f"Error restoring tanks from snapshots: {e}", exc_info=True)
            logger.info("Will create default tank instead")

        # Create default tank if no tanks were restored
        if self.tank_registry.tank_count == 0:
            logger.info("No tanks in registry, creating default tank...")
            default_manager = self.tank_registry.create_tank(
                name="Tank 1",
                description="A local fish tank simulation",
                persistent=True,
            )
            self.tank_registry._default_tank_id = default_manager.tank_id
            logger.info(f"Created default tank: {default_manager.tank_id[:8]}")

            # Create initial snapshot immediately
            try:
                from backend.tank_persistence import save_tank_state

                snapshot_path = save_tank_state(default_manager.tank_id, default_manager)
                if snapshot_path:
                    logger.info(f"Created initial snapshot: {snapshot_path}")
                else:
                    logger.warning("Failed to create initial snapshot")
            except Exception as e:
                logger.error(f"Error creating initial snapshot: {e}", exc_info=True)

        logger.info(f"Tank registry has {self.tank_registry.tank_count} tank(s)")

    async def _restore_connections(self) -> None:
        """Restore tank connections from saved file."""
        logger.info("Restoring tank connections...")
        try:
            from backend.connection_persistence import load_connections

            restored_connections = load_connections(self.connection_manager)
            logger.info(f"Restored {restored_connections} connection(s)")
        except Exception as e:
            logger.error(f"Error restoring connections: {e}", exc_info=True)
            logger.info("Continuing without restored connections")

    async def _start_simulations(self) -> None:
        """Start all tank simulations."""
        logger.info("Starting all tank simulations...")
        try:
            for manager in self.tank_registry:
                # Inject connection manager and tank registry for migrations
                manager.runner.connection_manager = self.connection_manager
                manager.runner.tank_registry = self.tank_registry
                manager.runner.tank_id = manager.tank_id
                manager.runner._update_environment_migration_context()

                manager.start(start_paused=False)
                logger.info(f"Tank {manager.tank_id[:8]} started")
        except Exception as e:
            logger.error(f"Failed to start simulations: {e}", exc_info=True)
            raise

    async def _start_broadcast_tasks(self) -> None:
        """Start broadcast tasks for all tanks."""
        logger.info("Starting broadcast tasks...")
        if not self._start_broadcast_callback:
            logger.warning("No broadcast callback configured, skipping broadcast tasks")
            return

        try:
            for manager in self.tank_registry:
                await self._start_broadcast_callback(manager)
                self._broadcast_task_ids.add(manager.tank_id)
                logger.info(f"Broadcast task started for tank {manager.tank_id[:8]}")
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

    async def _configure_distributed_services(self) -> None:
        """Configure tank registry for distributed operations."""
        logger.info("Configuring TankRegistry for distributed operations...")
        try:
            self.tank_registry.set_distributed_services(self.discovery_service, self.server_client)
            self.tank_registry.set_connection_manager(self.connection_manager)
            logger.info(
                "TankRegistry configured for distributed operations and connection management"
            )

            # Clean up invalid connections on startup
            valid_tank_ids = self.tank_registry.list_tank_ids()
            removed_count = self.connection_manager.validate_connections(
                valid_tank_ids, local_server_id=self.server_id
            )
            if removed_count > 0:
                logger.info(f"Startup cleanup: Removed {removed_count} invalid connections")

        except Exception as e:
            logger.error(f"Failed to configure TankRegistry: {e}", exc_info=True)
            # Non-fatal - continue without distributed tank queries

    async def _start_migration_scheduler(self) -> None:
        """Start migration scheduler for automated entity migrations."""
        logger.info("Starting migration scheduler...")
        try:
            self.migration_scheduler = MigrationScheduler(
                connection_manager=self.connection_manager,
                tank_registry=self.tank_registry,
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
        """Start auto-save service for periodic tank persistence."""
        logger.info("Starting auto-save service...")
        try:
            self.auto_save_service = AutoSaveService(self.tank_registry)
            await self.auto_save_service.start()
            logger.info("Auto-save service started")
        except Exception as e:
            logger.error(f"Failed to start auto-save service: {e}", exc_info=True)
            # Non-fatal - continue without auto-save

    # =========================================================================
    # Shutdown Steps
    # =========================================================================

    async def _save_all_tanks(self) -> None:
        """Save all persistent tanks before shutdown."""
        logger.info("Saving all persistent tanks...")
        if self.auto_save_service:
            try:
                saved_count = await self.auto_save_service.save_all_now()
                logger.info(f"Saved {saved_count} persistent tank(s) before shutdown")
            except Exception as e:
                logger.error(f"Error saving tanks on shutdown: {e}", exc_info=True)

    async def _save_connections(self) -> None:
        """Save all connections before shutdown."""
        logger.info("Saving tank connections...")
        try:
            from backend.connection_persistence import save_connections

            if save_connections(self.connection_manager):
                logger.info("Tank connections saved successfully")
            else:
                logger.warning("Failed to save tank connections")
        except Exception as e:
            logger.error(f"Error saving connections on shutdown: {e}", exc_info=True)

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

        for tank_id in list(self._broadcast_task_ids):
            try:
                await self._stop_broadcast_callback(tank_id)
                logger.info(f"Broadcast task stopped for tank {tank_id[:8]}")
            except Exception as e:
                logger.error(
                    f"Error stopping broadcast for tank {tank_id[:8]}: {e}",
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
        """Stop all tank simulations."""
        logger.info("Stopping all simulations...")
        try:
            self.tank_registry.stop_all()
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
                tank_count=0,
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
