"""Tank CRUD operations (list, create, get, delete)."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.routers.world_guards import get_tank_manager_or_error
from backend.tank_registry import TankRegistry
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


class UpdateTankModeRequest(BaseModel):
    """Request model for updating tank world type."""

    world_type: str


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
        if world_manager is not None:
            known_ids = {
                t.get("tank", {}).get("tank_id")
                for t in tanks
                if isinstance(t, dict) and "tank" in t
            }
            for world in world_manager.list_worlds(world_type="tank"):
                if world.world_id in known_ids:
                    continue
                adapter = world_manager.get_tank_adapter(world.world_id)
                if adapter is not None:
                    tanks.append(adapter.get_status())
        return JSONResponse(
            {
                "tanks": tanks,
                "count": len(tanks),
                "default_tank_id": tank_registry.default_tank_id,
            }
        )

    @router.post("")
    async def create_tank(
        name: str,
        description: str = "",
        seed: Optional[int] = None,
        owner: Optional[str] = None,
        is_public: bool = True,
        allow_transfers: bool = True,
        server_id_param: str = "local-server",
        world_type: str = "tank",
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
                world_type=world_type,
            )

            # Inject connection manager and tank registry for migrations
            if hasattr(tank_registry, "_connection_manager"):
                manager.runner.connection_manager = tank_registry._connection_manager
            manager.runner.tank_registry = tank_registry
            manager.runner.tank_id = manager.tank_id
            manager.runner._update_environment_migration_context()

            # Start the simulation
            manager.start(start_paused=False)

            # Start broadcast task for the new tank
            await start_broadcast_callback(manager)

            logger.info(
                f"Created new tank via API: {manager.tank_id[:8]} ({name}) on server {server_id_param}"
            )

            return JSONResponse(manager.get_status(), status_code=201)
        except Exception as e:
            logger.error(f"Error creating tank: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @router.put("/{tank_id}/mode")
    async def update_tank_mode(
        tank_id: str,
        mode_request: UpdateTankModeRequest,
        request: Request,
    ):
        """Update the world type of a tank (switch simulation mode)."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        try:
            # Validate mode availability (basic check)
            # You might want to call get_registered_world_types() here but for now simple check
            # basic validation is implicitly done by SimulationRunner/WorldRegistry which raises ValueError
            
            manager.change_world_type(mode_request.world_type)

            # Persist immediately
            if auto_save_service:
                await auto_save_service.save_tank_now(tank_id)

            return JSONResponse(manager.get_status())
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except Exception as e:
            logger.error(f"Error changing tank mode: {e}", exc_info=True)
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
