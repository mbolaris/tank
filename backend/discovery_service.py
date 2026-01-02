"""Server discovery and registry service for Tank World Net.

This module provides the DiscoveryService which maintains a registry of all
known servers in the Tank World Net distributed network. It handles:
- Server registration and deregistration
- Health checking via heartbeats
- Server status monitoring
- Persistent server registry storage
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from backend.models import ServerInfo

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Manages server discovery and registration for distributed Tank World Net.

    The DiscoveryService maintains a registry of all known servers, tracks their
    health status via heartbeats, and persists the registry to disk for recovery
    after restarts.

    Features:
    - Server registration (local and remote)
    - Heartbeat-based health checking
    - Automatic offline detection
    - Persistent storage of server registry
    - Query servers by ID or status
    """

    # Heartbeat settings
    HEARTBEAT_INTERVAL = 2.0  # Send heartbeat every 2 seconds (was 30.0)
    HEARTBEAT_TIMEOUT = 6.0  # Mark offline after 6 seconds without heartbeat (was 90.0)
    CLEANUP_INTERVAL = 5.0  # Check for stale servers every 5 seconds (was 60.0)
    PRUNE_TIMEOUT = 3600.0  # Remove servers offline for > 1 hour

    def __init__(self, data_dir: Path = Path("data")):
        """Initialize the discovery service.

        Args:
            data_dir: Directory for persistent storage
        """
        self._servers: Dict[str, ServerInfo] = {}
        self._last_heartbeat: Dict[str, float] = {}
        self._data_dir = data_dir
        self._registry_file = data_dir / "server_registry.json"
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

        # Create data directory if needed
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted registry
        self._load_registry()

        logger.info("DiscoveryService initialized with %d server(s)", len(self._servers))

    async def start(self) -> None:
        """Start the discovery service background tasks."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("DiscoveryService cleanup loop started")

    async def stop(self) -> None:
        """Stop the discovery service and cleanup tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("DiscoveryService cleanup loop stopped")

    async def register_server(self, server_info: ServerInfo) -> None:
        """Register a server in the discovery service.

        Args:
            server_info: Server information to register
        """
        async with self._lock:
            server_id = server_info.server_id

            # Check for existing servers with same host:port but different ID
            # This handles the case where a server restarts with a new ID
            to_remove = []
            for existing_id, existing_server in self._servers.items():
                if (
                    existing_id != server_id
                    and existing_server.host == server_info.host
                    and existing_server.port == server_info.port
                ):

                    logger.info(
                        "Found duplicate server %s at %s:%d. Removing in favor of new registration %s.",
                        existing_id,
                        existing_server.host,
                        existing_server.port,
                        server_id,
                    )
                    to_remove.append(existing_id)

            for stale_id in to_remove:
                del self._servers[stale_id]
                self._last_heartbeat.pop(stale_id, None)

            # Check if this is an update to existing server
            was_offline = False
            if server_id in self._servers:
                old_status = self._servers[server_id].status
                was_offline = old_status == "offline"

            # Update server info and heartbeat
            self._servers[server_id] = server_info
            self._last_heartbeat[server_id] = time.time()

            # Ensure status is online when registering
            if self._servers[server_id].status != "online":
                self._servers[server_id].status = "online"

            # Save to disk
            self._save_registry()

            if was_offline:
                logger.info("Server %s came back online", server_id)
            else:
                logger.info(
                    "Server registered: %s at %s:%d (%s)",
                    server_id,
                    server_info.host,
                    server_info.port,
                    server_info.hostname,
                )

    async def unregister_server(self, server_id: str) -> bool:
        """Unregister a server from the discovery service.

        Args:
            server_id: Server ID to unregister

        Returns:
            True if server was found and removed, False otherwise
        """
        async with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                self._last_heartbeat.pop(server_id, None)
                self._save_registry()
                logger.info("Server unregistered: %s", server_id)
                return True
            return False

    async def heartbeat(self, server_id: str, server_info: Optional[ServerInfo] = None) -> bool:
        """Record a heartbeat from a server.

        Args:
            server_id: Server ID sending the heartbeat
            server_info: Optional updated server info

        Returns:
            True if heartbeat was recorded, False if server not registered
        """
        async with self._lock:
            if server_id not in self._servers:
                logger.warning("Heartbeat from unregistered server: %s", server_id)
                return False

            # Update heartbeat timestamp
            self._last_heartbeat[server_id] = time.time()

            # Update server info if provided
            if server_info:
                self._servers[server_id] = server_info

                # Ensure status is online
                if self._servers[server_id].status == "offline":
                    self._servers[server_id].status = "online"
                    logger.info("Server %s status changed to online", server_id)

            return True

    async def get_server(self, server_id: str) -> Optional[ServerInfo]:
        """Get server info by ID.

        Args:
            server_id: Server ID to look up

        Returns:
            ServerInfo if found, None otherwise
        """
        async with self._lock:
            return self._servers.get(server_id)

    async def list_servers(
        self,
        status_filter: Optional[str] = None,
        include_local: bool = True,
    ) -> List[ServerInfo]:
        """List all registered servers.

        Args:
            status_filter: Optional status filter ("online", "offline", "degraded")
            include_local: Whether to include local server

        Returns:
            List of ServerInfo objects
        """
        async with self._lock:
            servers = list(self._servers.values())

            # Apply filters
            if status_filter:
                servers = [s for s in servers if s.status == status_filter]

            if not include_local:
                servers = [s for s in servers if not s.is_local]

            return servers

    async def get_online_servers(self) -> List[ServerInfo]:
        """Get all online servers.

        Returns:
            List of online ServerInfo objects
        """
        return await self.list_servers(status_filter="online")

    async def check_server_health(self, server_id: str) -> str:
        """Check the health status of a server based on heartbeat.

        Args:
            server_id: Server ID to check

        Returns:
            Status string: "online", "offline", or "degraded"
        """
        async with self._lock:
            if server_id not in self._servers:
                return "offline"

            last_heartbeat = self._last_heartbeat.get(server_id, 0)
            time_since_heartbeat = time.time() - last_heartbeat

            if time_since_heartbeat > self.HEARTBEAT_TIMEOUT:
                return "offline"
            elif time_since_heartbeat > self.HEARTBEAT_INTERVAL * 2:
                return "degraded"
            else:
                return "online"

    async def _cleanup_loop(self) -> None:
        """Background task to check for stale servers and update their status."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self._check_stale_servers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop: %s", e, exc_info=True)

    async def _check_stale_servers(self) -> None:
        """Check for servers that haven't sent heartbeats and mark them offline or prune them."""
        async with self._lock:
            current_time = time.time()
            changes = []
            to_prune = []

            for server_id, server_info in self._servers.items():
                last_heartbeat = self._last_heartbeat.get(server_id, 0)
                time_since_heartbeat = current_time - last_heartbeat

                # Determine new status
                if time_since_heartbeat > self.PRUNE_TIMEOUT:
                    to_prune.append(server_id)
                    continue
                elif time_since_heartbeat > self.HEARTBEAT_TIMEOUT:
                    new_status = "offline"
                elif time_since_heartbeat > self.HEARTBEAT_INTERVAL * 2:
                    new_status = "degraded"
                else:
                    new_status = "online"

                # Update if changed
                if server_info.status != new_status:
                    server_info.status = new_status
                    changes.append((server_id, new_status))

            # Prune very old servers
            for server_id in to_prune:
                del self._servers[server_id]
                self._last_heartbeat.pop(server_id, None)
                logger.info(
                    "Pruned stale server: %s (inactive for > %.0fs)", server_id, self.PRUNE_TIMEOUT
                )
                changes.append((server_id, "pruned"))

            # Log changes
            if changes:
                for server_id, new_status in changes:
                    if new_status != "pruned":
                        logger.info("Server %s status changed to %s", server_id, new_status)
                self._save_registry()

    def _load_registry(self) -> None:
        """Load server registry from disk."""
        if not self._registry_file.exists():
            logger.info("No existing server registry found")
            return

        try:
            with open(self._registry_file) as f:
                data = json.load(f)

            # Load servers
            for server_data in data.get("servers", []):
                server_info = ServerInfo(**server_data)
                self._servers[server_info.server_id] = server_info

                # Initialize heartbeat timestamp (will be updated on first heartbeat)
                self._last_heartbeat[server_info.server_id] = data.get("last_heartbeats", {}).get(
                    server_info.server_id, 0
                )

            logger.info("Loaded %d server(s) from registry", len(self._servers))

        except Exception as e:
            logger.error("Failed to load server registry: %s", e, exc_info=True)

    def _save_registry(self) -> None:
        """Save server registry to disk."""
        try:
            data = {
                "servers": [s.model_dump() for s in self._servers.values()],
                "last_heartbeats": self._last_heartbeat,
                "updated_at": time.time(),
            }

            # Write atomically using temp file
            temp_file = self._registry_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self._registry_file)
            logger.debug("Server registry saved to disk")

        except Exception as e:
            logger.error("Failed to save server registry: %s", e, exc_info=True)
