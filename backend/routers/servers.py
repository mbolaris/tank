"""Server management API endpoints."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.discovery_service import DiscoveryService
from backend.models import ServerWithTanks
from backend.server_client import ServerClient
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/servers", tags=["servers"])


def setup_router(
    world_manager: WorldManager,
    discovery_service: DiscoveryService,
    server_client: ServerClient,
    get_server_info_callback,
) -> APIRouter:
    """Setup the servers router with required dependencies.

    Args:
        world_manager: The world manager instance
        discovery_service: The discovery service instance
        server_client: The server client instance
        get_server_info_callback: Callback to get current server info

    Returns:
        Configured APIRouter
    """

    @router.get("/local")
    async def get_local_server():
        """Get information about the local server.

        Returns:
            ServerInfo for the local server
        """
        server_info = get_server_info_callback()
        return JSONResponse(server_info.model_dump())

    @router.get("")
    async def list_servers():
        """List all servers in the Tank World Network.

        Returns all servers registered in the discovery service, including the local
        server. For each server, includes the list of worlds running on it.

        Returns:
            List of ServerWithTanks objects containing server info and their worlds
        """
        # Get all servers from discovery service
        all_servers = await discovery_service.list_servers()

        # Build response with worlds for each server
        servers_with_tanks = []

        for server in all_servers:
            if server.is_local:
                # For local server, get worlds directly
                worlds = world_manager.list_worlds()
                # Convert WorldStatus to dict for compatibility
                tanks = [w.to_dict() for w in worlds]
            else:
                # For remote servers, fetch tanks via API
                try:
                    remote_tanks = await server_client.list_tanks(server)
                    tanks = remote_tanks if remote_tanks is not None else []
                except Exception as e:
                    logger.error(f"Failed to fetch worlds from {server.server_id}: {e}")
                    tanks = []

            servers_with_tanks.append(
                ServerWithTanks(
                    server=server,
                    tanks=tanks,
                ).model_dump()
            )

        return JSONResponse({"servers": servers_with_tanks})

    @router.get("/{server_id}")
    async def get_server(server_id: str):
        """Get information about a specific server.

        Args:
            server_id: The server identifier

        Returns:
            ServerWithTanks object or 404 if not found
        """
        # Look up server in discovery service
        server_info = await discovery_service.get_server(server_id)

        if server_info is None:
            return JSONResponse(
                {"error": f"Server not found: {server_id}"},
                status_code=404,
            )

        # Get worlds for the server
        if server_info.is_local:
            # Local server - get worlds directly
            worlds = world_manager.list_worlds()
            tanks = [w.to_dict() for w in worlds]
        else:
            # Remote server - fetch via API
            try:
                remote_tanks = await server_client.list_tanks(server_info)
                tanks = remote_tanks if remote_tanks is not None else []
            except Exception as e:
                logger.error(f"Failed to fetch worlds from {server_id}: {e}")
                tanks = []

        return JSONResponse(
            ServerWithTanks(
                server=server_info,
                tanks=tanks,
            ).model_dump()
        )

    return router
