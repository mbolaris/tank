"""HTTP client for server-to-server communication in Tank World Net.

This module provides the ServerClient class which handles all HTTP communication
between Tank World Net servers in a distributed deployment.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, cast

import httpx

from backend.models import ServerInfo

logger = logging.getLogger(__name__)


class ServerClient:
    """HTTP client for communicating with remote Tank World Net servers.

    The ServerClient provides a clean interface for making API calls to remote
    servers. It handles connection pooling, timeouts, retries, and error handling.

    Features:
    - Async HTTP client with connection pooling
    - Automatic retries with exponential backoff
    - Timeout handling
    - Error logging and recovery
    """

    # Client settings
    DEFAULT_TIMEOUT = 10.0  # Default request timeout in seconds
    MAX_RETRIES = 3  # Maximum number of retry attempts
    RETRY_DELAY = 1.0  # Initial retry delay (doubles each retry)

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize the server client.

        Args:
            timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retry attempts
        """
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                follow_redirects=True,
            )
            logger.debug("ServerClient HTTP client started")

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("ServerClient HTTP client closed")

    async def _request(
        self,
        method: str,
        url: str,
        retries: int = 0,
        **kwargs,
    ) -> Optional[httpx.Response]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Full URL to request
            retries: Current retry count
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response object if successful, None if all retries failed
        """
        if self._client is None:
            await self.start()
        client = self._client
        if client is None:
            logger.error("ServerClient HTTP client failed to start")
            return None

        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP %d error for %s %s: %s",
                e.response.status_code,
                method,
                url,
                e,
            )
            return None

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if retries < self._max_retries:
                delay = self.RETRY_DELAY * (2**retries)
                logger.warning(
                    "Request failed (%s), retrying in %.1fs... (attempt %d/%d)",
                    type(e).__name__,
                    delay,
                    retries + 1,
                    self._max_retries,
                )
                await asyncio.sleep(delay)
                return await self._request(method, url, retries=retries + 1, **kwargs)
            else:
                logger.error(
                    "Request failed after %d retries: %s %s - %s",
                    self._max_retries,
                    method,
                    url,
                    e,
                )
                return None

        except Exception as e:
            logger.error("Unexpected error in request to %s: %s", url, e, exc_info=True)
            return None

    def _build_url(self, server: ServerInfo, path: str) -> str:
        """Build a full URL from server info and path.

        Args:
            server: Server information
            path: API path (should start with /)

        Returns:
            Full URL string
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        return f"http://{server.host}:{server.port}{path}"

    async def get_server_info(self, server: ServerInfo) -> Optional[ServerInfo]:
        """Get server information from a remote server.

        Args:
            server: Server to query (uses host/port)

        Returns:
            ServerInfo if successful, None otherwise
        """
        url = self._build_url(server, "/api/servers/local")
        response = await self._request("GET", url)

        if response:
            try:
                data = response.json()
                return ServerInfo(**data)
            except Exception as e:
                logger.error("Failed to parse server info: %s", e)

        return None

    async def list_worlds(self, server: ServerInfo) -> Optional[List[Dict[str, Any]]]:
        """List all worlds on a remote server.

        Args:
            server: Server to query

        Returns:
            List of world info dictionaries if successful, None otherwise
        """
        url = self._build_url(server, "/api/worlds")
        response = await self._request("GET", url)

        if response:
            try:
                data = response.json()
                worlds: Any = data.get("worlds") if isinstance(data, dict) else data
                if isinstance(worlds, list) and all(isinstance(item, dict) for item in worlds):
                    return cast(List[Dict[str, Any]], worlds)
                logger.error("Unexpected world list response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse world list: %s", e)

        return None

    async def get_world(
        self,
        server: ServerInfo,
        world_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get world information from a remote server.

        Args:
            server: Server to query
            world_id: World ID to look up

        Returns:
            World info dictionary if successful, None otherwise
        """
        url = self._build_url(server, f"/api/worlds/{world_id}")
        response = await self._request("GET", url)

        if response:
            try:
                data = response.json()
                if isinstance(data, dict):
                    return cast(Dict[str, Any], data)
                logger.error("Unexpected world info response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse world info: %s", e)

        return None

    async def transfer_entity(
        self,
        server: ServerInfo,
        source_world_id: str,
        destination_world_id: str,
        entity_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Transfer an entity between worlds on a remote server.

        Args:
            server: Server hosting the worlds
            source_world_id: Source world ID
            destination_world_id: Destination world ID
            entity_id: Entity ID to transfer

        Returns:
            Transfer result dictionary if successful, None otherwise
        """
        url = self._build_url(
            server,
            f"/api/worlds/{source_world_id}/transfer",
        )

        params = {
            "entity_id": entity_id,
            "destination_world_id": destination_world_id,
        }

        response = await self._request("POST", url, params=params)

        if response:
            try:
                data = response.json()
                if isinstance(data, dict):
                    return cast(Dict[str, Any], data)
                logger.error("Unexpected transfer result response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse transfer result: %s", e)

        return None

    async def create_connection(
        self,
        server: ServerInfo,
        source_world_id: str,
        destination_world_id: str,
        probability: int = 50,
        direction: str = "right",
    ) -> Optional[Dict[str, Any]]:
        """Create a migration connection on a remote server.

        Args:
            server: Server to create connection on
            source_world_id: Source tank ID
            destination_world_id: Destination tank ID
            probability: Migration probability (0-100)
            direction: Migration direction ("left" or "right")

        Returns:
            Connection info if successful, None otherwise
        """
        url = self._build_url(server, "/api/connections")

        payload = {
            "source_world_id": source_world_id,
            "destination_world_id": destination_world_id,
            "probability": probability,
            "direction": direction,
        }

        response = await self._request("POST", url, json=payload)

        if response:
            try:
                data = response.json()
                if isinstance(data, dict):
                    return cast(Dict[str, Any], data)
                logger.error("Unexpected connection info response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse connection info: %s", e)

        return None

    async def get_connections(
        self,
        server: ServerInfo,
        world_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get migration connections from a remote server.

        Args:
            server: Server to query
            world_id: Optional tank ID to filter by source tank

        Returns:
            List of connection info dictionaries if successful, None otherwise
        """
        url = self._build_url(server, "/api/connections")

        params = {}
        if world_id:
            params["world_id"] = world_id

        response = await self._request("GET", url, params=params)

        if response:
            try:
                data = response.json()
                connections: Any = data.get("connections") if isinstance(data, dict) else data
                if isinstance(connections, list) and all(
                    isinstance(item, dict) for item in connections
                ):
                    return cast(List[Dict[str, Any]], connections)
                logger.error("Unexpected connections response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse connections: %s", e)

        return None

    async def ping(self, server: ServerInfo) -> bool:
        """Ping a server to check if it's reachable.

        Args:
            server: Server to ping

        Returns:
            True if server responds, False otherwise
        """
        url = self._build_url(server, "/api/health")
        response = await self._request("GET", url)
        return response is not None

    async def send_heartbeat(
        self,
        server: ServerInfo,
        local_server_info: ServerInfo,
    ) -> bool:
        """Send a heartbeat to a remote discovery service.

        Args:
            server: Discovery service server
            local_server_info: Information about this server

        Returns:
            True if heartbeat was successful, False otherwise
        """
        url = self._build_url(
            server,
            f"/api/discovery/heartbeat/{local_server_info.server_id}",
        )

        response = await self._request(
            "POST",
            url,
            json=local_server_info.model_dump(),
        )

        return response is not None

    async def register_server(
        self,
        server: ServerInfo,
        local_server_info: ServerInfo,
    ) -> bool:
        """Register this server with a remote discovery service.

        Args:
            server: Discovery service server
            local_server_info: Information about this server

        Returns:
            True if registration was successful, False otherwise
        """
        url = self._build_url(server, "/api/discovery/register")

        response = await self._request(
            "POST",
            url,
            json=local_server_info.model_dump(),
        )

        return response is not None

    async def remote_transfer_entity(
        self,
        server: ServerInfo,
        destination_world_id: str,
        entity_data: Dict[str, Any],
        source_server_id: str,
        source_world_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Transfer an entity to a remote server.

        This sends a serialized entity to a remote server for cross-server migration.

        Args:
            server: Destination server
            destination_world_id: Destination tank ID
            entity_data: Serialized entity data
            source_server_id: Source server ID (for logging)
            source_world_id: Source tank ID (for logging)

        Returns:
            Transfer result dictionary if successful, None otherwise
        """
        url = self._build_url(server, "/api/remote-transfer")

        payload = {
            "destination_world_id": destination_world_id,
            "entity_data": entity_data,
            "source_server_id": source_server_id,
            "source_world_id": source_world_id,
        }

        response = await self._request("POST", url, json=payload)

        if response:
            try:
                data = response.json()
                if isinstance(data, dict):
                    return cast(Dict[str, Any], data)
                logger.error("Unexpected remote transfer result response format: %s", type(data))
                return None
            except Exception as e:
                logger.error("Failed to parse remote transfer result: %s", e)

        return None
