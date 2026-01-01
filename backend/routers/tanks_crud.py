"""Tank CRUD operations (list, create, get, delete)."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.routers.world_guards import get_tank_manager_or_error
from backend.tank_registry import TankRegistry
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_crud_subrouter(
    router: APIRouter,
    tank_registry: TankRegistry,
    server_id: str,
    start_broadcast_callback,
    stop_broadcast_callback,
    auto_save_service: Optional[Any] = None,
    world_manager: Optional[WorldManager] = None,
) -> None:
    """Attach CRUD endpoints to the router.

    Endpoints:
        GET /api/tanks - List all tanks
        POST /api/tanks - Create a new tank
        GET /api/tanks/{tank_id} - Get a specific tank
        DELETE /api/tanks/{tank_id} - Delete a tank
    """

    @router.get("")
    async def list_tanks(include_private: bool = False):
        """List all tanks in the registry."""
        tanks = tank_registry.list_tanks(include_private=include_private)
        return JSONResponse({
            "tanks": tanks,
            "count": len(tanks),
            "default_tank_id": tank_registry.default_tank_id,
        })

    @router.post("")
    async def create_tank(
        name: str,
        description: str = "",
        seed: Optional[int] = None,
        owner: Optional[str] = None,
        is_public: bool = True,
        allow_transfers: bool = True,
        server_id_param: str = "local-server",
    ):
        """Create a new tank simulation."""
        try:
            if server_id_param != server_id:
                return JSONResponse(
                    {
                        "error": f"Invalid server_id: {server_id_param}. "
                        f"Only '{server_id}' is supported in this version."
                    },
                    status_code=400,
                )

            manager = tank_registry.create_tank(
                name=name,
                description=description,
                seed=seed,
                owner=owner,
                is_public=is_public,
                allow_transfers=allow_transfers,
                server_id=server_id_param,
            )

            # Inject connection manager and tank registry for migrations
            if hasattr(tank_registry, '_connection_manager'):
                manager.runner.connection_manager = tank_registry._connection_manager
            manager.runner.tank_registry = tank_registry
            manager.runner.tank_id = manager.tank_id
            manager.runner._update_environment_migration_context()

            # Start the simulation
            manager.start(start_paused=False)

            # Start broadcast task for the new tank
            await start_broadcast_callback(manager)

            logger.info(f"Created new tank via API: {manager.tank_id[:8]} ({name}) on server {server_id_param}")

            return JSONResponse(manager.get_status(), status_code=201)
        except Exception as e:
            logger.error(f"Error creating tank: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @router.get("/{tank_id}")
    async def get_tank(tank_id: str, request: Request):
        """Get information about a specific tank."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error
        return JSONResponse(manager.get_status())

    @router.delete("/{tank_id}")
    async def delete_tank(tank_id: str, request: Request):
        """Delete a tank from the registry."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        # Stop auto-save first
        if auto_save_service:
            await auto_save_service.stop_tank_autosave(tank_id)

        # Stop broadcast first
        await stop_broadcast_callback(tank_id)

        # Remove from registry
        if tank_registry.remove_tank(manager.tank_id, delete_persistent_data=True):
            logger.info(f"Deleted tank via API: {manager.tank_id[:8]}")
            return JSONResponse({"message": f"Tank {manager.tank_id} deleted"})

        return JSONResponse(
            {"error": f"Tank not found: {tank_id}"},
            status_code=404,
        )
