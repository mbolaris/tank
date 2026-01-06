"""Connection management API endpoints."""

import logging
import sys

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.connection_manager import ConnectionManager, TankConnection
from backend.connection_persistence import save_connections
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connections", tags=["connections"])


class ConnectionResponse(BaseModel):
    """Response model for a list of connections."""

    connections: List[Dict]


def setup_router(
    connection_manager: ConnectionManager,
    world_manager: WorldManager,
    local_server_id: Optional[str] = None,
) -> APIRouter:
    """Create and configure the connections router."""

    @router.get("")
    async def list_connections(
        world_id: Annotated[Optional[str], Query()] = None,
    ) -> JSONResponse:
        """List all migration connections, optionally filtered by source world."""
        if world_id:
            connections = connection_manager.get_connections_for_world(world_id)
        else:
            connections = connection_manager.list_connections()

        payload = [conn.to_dict() for conn in connections]
        return JSONResponse({"connections": payload, "count": len(payload)})

    @router.post("")
    async def create_connection(
        payload: Annotated[Dict[str, Any], Body(...)],
    ) -> JSONResponse:
        """Create or update a migration connection."""
        try:
            connection = TankConnection.from_dict(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not 0 <= connection.probability <= 100:
            raise HTTPException(
                status_code=400,
                detail="Probability must be between 0 and 100",
            )

        if connection.direction not in ("left", "right"):
            raise HTTPException(
                status_code=400,
                detail="Direction must be 'left' or 'right'",
            )

        def is_local(server_id: Optional[str]) -> bool:
            if server_id is None:
                return True
            if local_server_id is None:
                return True
            return server_id == local_server_id

        if is_local(connection.source_server_id):
            if world_manager.get_world(connection.source_world_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source world not found: {connection.source_world_id}",
                )

        if is_local(connection.destination_server_id):
            if world_manager.get_world(connection.destination_world_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Destination world not found: {connection.destination_world_id}",
                )

        existing = connection_manager.get_connection(connection.id)
        connection_manager.add_connection(connection)

        if not save_connections(connection_manager):
            logger.warning("Failed to persist connections after update")

        status_code = 200 if existing else 201
        return JSONResponse(connection.to_dict(), status_code=status_code)

    @router.delete("/{connection_id}")
    async def delete_connection(connection_id: str) -> JSONResponse:
        """Delete a migration connection."""
        removed = connection_manager.remove_connection(connection_id)
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Connection not found: {connection_id}",
            )

        if not save_connections(connection_manager):
            logger.warning("Failed to persist connections after delete")

        return JSONResponse({"message": f"Connection {connection_id} deleted"})

    return router
