"""Tank connection management endpoints."""

import logging
from typing import Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.connection_manager import ConnectionManager, TankConnection

logger = logging.getLogger(__name__)


def setup_connections_subrouter(
    router: APIRouter,
    connection_manager: ConnectionManager,
) -> None:
    """Attach connection management endpoints to the router.

    Endpoints:
        GET /api/connections - List connections
        POST /api/connections - Create connection
        DELETE /api/connections/{connection_id} - Delete connection
    """

    @router.get("/api/connections")
    async def list_connections(tank_id: Optional[str] = None):
        """List tank connections."""
        if tank_id:
            connections = connection_manager.get_connections_for_tank(tank_id)
        else:
            connections = connection_manager.list_connections()

        return JSONResponse({
            "connections": [c.to_dict() for c in connections],
            "count": len(connections),
        })

    @router.post("/api/connections")
    async def create_connection(connection_data: Dict):
        """Create or update a tank connection."""
        try:
            connection = TankConnection.from_dict(connection_data)
            connection_manager.add_connection(connection)

            # Save connections to disk
            try:
                from backend.connection_persistence import save_connections
                save_connections(connection_manager)
            except Exception as save_error:
                logger.warning(f"Failed to save connections after create: {save_error}")

            return JSONResponse(connection.to_dict())
        except Exception as e:
            logger.error(f"Error creating connection: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=400)

    @router.delete("/api/connections/{connection_id}")
    async def delete_connection(connection_id: str):
        """Delete a tank connection."""
        if connection_manager.remove_connection(connection_id):
            # Save connections to disk
            try:
                from backend.connection_persistence import save_connections
                save_connections(connection_manager)
            except Exception as save_error:
                logger.warning(f"Failed to save connections after delete: {save_error}")

            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Connection not found"}, status_code=404)
