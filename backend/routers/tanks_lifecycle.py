"""Tank lifecycle operations (start, stop, pause, resume, fast_forward)."""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.routers.world_guards import get_tank_manager_or_error
from backend.tank_registry import TankRegistry
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_lifecycle_subrouter(
    router: APIRouter,
    tank_registry: TankRegistry,
    start_broadcast_callback,
    stop_broadcast_callback,
    world_manager: Optional[WorldManager] = None,
) -> None:
    """Attach lifecycle endpoints to the router.

    Endpoints:
        POST /api/tanks/{tank_id}/pause
        POST /api/tanks/{tank_id}/resume
        POST /api/tanks/{tank_id}/start
        POST /api/tanks/{tank_id}/stop
        POST /api/tanks/{tank_id}/fast_forward
    """

    @router.post("/{tank_id}/pause")
    async def pause_tank(tank_id: str, request: Request):
        """Pause a running tank simulation."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error
        if not manager.running:
            return JSONResponse({"error": "Tank is not running"}, status_code=400)

        manager.world.paused = True
        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/resume")
    async def resume_tank(tank_id: str, request: Request):
        """Resume a paused tank simulation."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error
        if not manager.running:
            return JSONResponse({"error": "Tank is not running"}, status_code=400)

        manager.world.paused = False

        # Ensure broadcast task exists for this tank
        await start_broadcast_callback(manager)

        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/start")
    async def start_tank(tank_id: str, request: Request):
        """Start a stopped tank simulation."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        if not manager.running:
            manager.start(start_paused=False)

        await start_broadcast_callback(manager)

        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/stop")
    async def stop_tank(tank_id: str, request: Request):
        """Stop a running tank simulation and its broadcast task."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        await stop_broadcast_callback(tank_id)

        if manager.running:
            manager.stop()

        manager.world.paused = True

        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/fast_forward")
    async def toggle_fast_forward(tank_id: str, request: Request, enabled: bool = True):
        """Toggle fast forward mode for a tank simulation."""
        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error
        if not manager.running:
            return JSONResponse({"error": "Tank is not running"}, status_code=400)

        manager.runner.fast_forward = enabled
        logger.info(f"Fast forward {'enabled' if enabled else 'disabled'} for tank {tank_id[:8]}")
        return JSONResponse(manager.get_status())
