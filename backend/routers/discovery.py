"""Discovery service API endpoints."""

import ipaddress
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.discovery_service import DiscoveryService
from backend.models import ServerInfo

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def _require_discovery_api_key(request: Request) -> None:
    api_key = os.getenv("DISCOVERY_API_KEY")
    if not api_key:
        return
    provided = request.headers.get("X-Discovery-Key")
    if not provided or provided != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid discovery API key",
        )


def _validate_server_host(server_info: ServerInfo) -> None:
    allow_private = os.getenv("ALLOW_PRIVATE_SERVER_REGISTRATION", "false").lower() == "true"
    host = server_info.host.strip().lower()

    if host in {"localhost", "localhost.localdomain"} and not allow_private:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Localhost registrations are not allowed",
        )

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return

    if not allow_private and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private or special IP registrations are not allowed",
        )


def setup_router(discovery_service: DiscoveryService) -> APIRouter:
    """Setup the discovery router with required dependencies.

    Args:
        discovery_service: The discovery service instance

    Returns:
        Configured APIRouter
    """

    @router.post("/register")
    async def register_server(request: Request, server_info: ServerInfo):
        """Register a server with the discovery service.

        Args:
            server_info: Server information to register

        Returns:
            Success message and registered server info
        """
        _require_discovery_api_key(request)
        _validate_server_host(server_info)
        await discovery_service.register_server(server_info)
        return JSONResponse(
            {
                "status": "registered",
                "server_id": server_info.server_id,
                "message": f"Server {server_info.server_id} registered successfully",
            }
        )

    @router.post("/heartbeat/{server_id}")
    async def send_heartbeat(
        request: Request,
        server_id: str,
        server_info: Optional[ServerInfo] = None,
    ):
        """Record a heartbeat from a server.

        Args:
            server_id: Server ID sending the heartbeat
            server_info: Optional updated server information

        Returns:
            Success message or error if server not registered
        """
        _require_discovery_api_key(request)
        if server_info is not None:
            _validate_server_host(server_info)
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
                "servers": [s.model_dump() for s in servers],
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
