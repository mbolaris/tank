"""HTTP client for server-to-server communication in Tank World Net.

This module provides the ServerClient class which handles all HTTP communication
between Tank World Net servers in a distributed deployment.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

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
    MAX_RETRIES = 3         # Maximum number of retry attempts
    RETRY_DELAY = 1.0       # Initial retry delay (doubles each retry)

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

        try:
            response = await self._client.request(method, url, **kwargs)
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
                delay = self.RETRY_DELAY * (2 ** retries)
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

    async def list_tanks(self, server: ServerInfo) -> Optional[List[Dict[str, Any]]]:
        """List all tanks on a remote server.

        Args:
            server: Server to query

        Returns:
            List of tank info dictionaries if successful, None otherwise
        """
        url = self._build_url(server, "/api/tanks")
        response = await self._request("GET", url)

        if response:
            try:
                data = response.json()
                # Extract tanks array from response wrapper
                if isinstance(data, dict) and "tanks" in data:
                    return data["tanks"]
                # If response is already a list, return it
                elif isinstance(data, list):
                    return data
                else:
                    logger.error("Unexpected tank list response format: %s", type(data))
                    return None
            except Exception as e:
                logger.error("Failed to parse tank list: %s", e)

        return None

    async def get_tank(
        self,
        server: ServerInfo,
        tank_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get tank information from a remote server.

        Args:
            server: Server to query
            tank_id: Tank ID to look up

        Returns:
            Tank info dictionary if successful, None otherwise
        """
        url = self._build_url(server, f"/api/tanks/{tank_id}")
        response = await self._request("GET", url)

        if response:
            try:
                return response.json()
            except Exception as e:
                logger.error("Failed to parse tank info: %s", e)

        return None

    async def transfer_entity(
        self,
        server: ServerInfo,
        source_tank_id: str,
        destination_tank_id: str,
        entity_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Transfer an entity between tanks on a remote server.

        Args:
            server: Server hosting the tanks
            source_tank_id: Source tank ID
            destination_tank_id: Destination tank ID
            entity_id: Entity ID to transfer

        Returns:
            Transfer result dictionary if successful, None otherwise
        """
        url = self._build_url(
            server,
            f"/api/tanks/{source_tank_id}/transfer",
        )

        params = {
            "entity_id": entity_id,
            "destination_tank_id": destination_tank_id,
        }

        response = await self._request("POST", url, params=params)

        if response:
            try:
                return response.json()
            except Exception as e:
                logger.error("Failed to parse transfer result: %s", e)

        return None

    async def create_connection(
        self,
        server: ServerInfo,
        source_tank_id: str,
        destination_tank_id: str,
        probability: int = 50,
        direction: str = "right",
    ) -> Optional[Dict[str, Any]]:
        """Create a migration connection on a remote server.

        Args:
            server: Server to create connection on
            source_tank_id: Source tank ID
            destination_tank_id: Destination tank ID
            probability: Migration probability (0-100)
            direction: Migration direction ("left" or "right")

        Returns:
            Connection info if successful, None otherwise
        """
        url = self._build_url(server, "/api/connections")

        payload = {
            "source_tank_id": source_tank_id,
            "destination_tank_id": destination_tank_id,
            "probability": probability,
            "direction": direction,
        }

        response = await self._request("POST", url, json=payload)

        if response:
            try:
                return response.json()
            except Exception as e:
                logger.error("Failed to parse connection info: %s", e)

        return None

    async def get_connections(
        self,
        server: ServerInfo,
        tank_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get migration connections from a remote server.

        Args:
            server: Server to query
            tank_id: Optional tank ID to filter by source tank

        Returns:
            List of connection info dictionaries if successful, None otherwise
        """
        url = self._build_url(server, "/api/connections")

        params = {}
        if tank_id:
            params["tank_id"] = tank_id

        response = await self._request("GET", url, params=params)

        if response:
            try:
                return response.json()
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
            json=local_server_info.dict(),
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
            json=local_server_info.dict(),
        )

        return response is not None

    async def remote_transfer_entity(
        self,
        server: ServerInfo,
        destination_tank_id: str,
        entity_data: Dict[str, Any],
        source_server_id: str,
        source_tank_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Transfer an entity to a remote server.

        This sends a serialized entity to a remote server for cross-server migration.

        Args:
            server: Destination server
            destination_tank_id: Destination tank ID
            entity_data: Serialized entity data
            source_server_id: Source server ID (for logging)
            source_tank_id: Source tank ID (for logging)

        Returns:
            Transfer result dictionary if successful, None otherwise
        """
        url = self._build_url(server, "/api/remote-transfer")

        payload = {
            "destination_tank_id": destination_tank_id,
            "entity_data": entity_data,
            "source_server_id": source_server_id,
            "source_tank_id": source_tank_id,
        }

        response = await self._request("POST", url, json=payload)

        if response:
            try:
                return response.json()
            except Exception as e:
                logger.error("Failed to parse remote transfer result: %s", e)

        return None
