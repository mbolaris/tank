"""Discovery service API endpoints."""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.discovery_service import DiscoveryService
from backend.models import ServerInfo

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def setup_router(discovery_service: DiscoveryService) -> APIRouter:
    """Setup the discovery router with required dependencies.

    Args:
        discovery_service: The discovery service instance

    Returns:
        Configured APIRouter
    """

    @router.post("/register")
    async def register_server(server_info: ServerInfo):
        """Register a server with the discovery service.

        Args:
            server_info: Server information to register

        Returns:
            Success message and registered server info
        """
        await discovery_service.register_server(server_info)
        return JSONResponse(
            {
                "status": "registered",
                "server_id": server_info.server_id,
                "message": f"Server {server_info.server_id} registered successfully",
            }
        )

    @router.post("/heartbeat/{server_id}")
    async def send_heartbeat(server_id: str, server_info: Optional[ServerInfo] = None):
        """Record a heartbeat from a server.

        Args:
            server_id: Server ID sending the heartbeat
            server_info: Optional updated server information

        Returns:
            Success message or error if server not registered
        """
        success = await discovery_service.heartbeat(server_id, server_info)

        if not success:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"Server {server_id} not registered. Please register first.",
                },
                status_code=404,
            )

        return JSONResponse(
            {
                "status": "ok",
                "server_id": server_id,
                "message": "Heartbeat received",
            }
        )

    @router.get("/servers")
    async def list_discovery_servers(
        status: Optional[str] = None,
        include_local: bool = True,
    ):
        """List all servers registered in the discovery service.

        Args:
            status: Optional status filter ("online", "offline", "degraded")
            include_local: Whether to include local server

        Returns:
            List of registered servers
        """
        servers = await discovery_service.list_servers(
            status_filter=status,
            include_local=include_local,
        )

        return JSONResponse(
            {
                "servers": [s.dict() for s in servers],
                "count": len(servers),
            }
        )

    @router.delete("/unregister/{server_id}")
    async def unregister_server(server_id: str):
        """Unregister a server from the discovery service.

        Args:
            server_id: Server ID to unregister

        Returns:
            Success message or error if not found
        """
        success = await discovery_service.unregister_server(server_id)

        if not success:
            return JSONResponse(
                {"error": f"Server not found: {server_id}"},
                status_code=404,
            )

        return JSONResponse(
            {
                "status": "unregistered",
                "server_id": server_id,
                "message": f"Server {server_id} unregistered successfully",
            }
        )

    return router
