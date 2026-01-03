"""Helper guards for world-typed endpoints."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.tank_registry import TankRegistry
from backend.world_manager import WorldManager


def get_tank_manager_or_error(
    tank_registry: TankRegistry,
    tank_id: str,
    *,
    request: Request | None = None,
    world_manager: WorldManager | None = None,
) -> tuple[object | None, JSONResponse | None]:
    """Resolve a tank manager or return an error response.

    If the ID belongs to a non-tank world, return a 400 with a clean error.
    """
    manager = tank_registry.get_tank(tank_id)
    if manager is not None:
        return manager, None

    if request is not None:
        context = getattr(getattr(request, "app", None), "state", None)
        if context is not None:
            ctx = getattr(context, "context", None)
            world_manager = getattr(ctx, "world_manager", world_manager)

    if world_manager is not None:
        instance = world_manager.get_world(tank_id)
        if instance is not None and not instance.is_tank():
            return None, JSONResponse(
                {"error": f"Unsupported for world_type={instance.world_type}"},
                status_code=400,
            )

    return None, JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)
