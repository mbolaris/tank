"""Helper guards for world-typed endpoints."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.world_manager import WorldInstance, WorldManager


def get_world_instance_or_error(
    world_manager: WorldManager,
    world_id: str,
    *,
    request: Request | None = None,
) -> tuple[WorldInstance | None, JSONResponse | None]:
    """Resolve a world instance or return an error response.

    Args:
        world_manager: The WorldManager instance
        world_id: The world ID to look up
        request: Optional request for context extraction

    Returns:
        Tuple of (instance, error). One will be None.
    """
    # Try to get from provided world_manager
    instance = world_manager.get_world(world_id)
    if instance is not None:
        return instance, None

    # Try to get world_manager from request context if not passed
    if request is not None:
        context = getattr(getattr(request, "app", None), "state", None)
        if context is not None:
            ctx = getattr(context, "context", None)
            ctx_world_manager = getattr(ctx, "world_manager", None)
            if ctx_world_manager is not None:
                instance = ctx_world_manager.get_world(world_id)
                if instance is not None:
                    return instance, None

    return None, JSONResponse({"error": f"World not found: {world_id}"}, status_code=404)


def get_tank_world_or_error(
    world_manager: WorldManager,
    world_id: str,
    *,
    request: Request | None = None,
) -> tuple[WorldInstance | None, JSONResponse | None]:
    """Resolve a tank world instance or return an error response.

    Only returns tank worlds, returns 400 for other world types.

    Args:
        world_manager: The WorldManager instance
        world_id: The world ID to look up
        request: Optional request for context extraction

    Returns:
        Tuple of (instance, error). One will be None.
    """
    instance, error = get_world_instance_or_error(world_manager, world_id, request=request)

    if error is not None:
        return None, error

    if instance is not None and not instance.is_tank():
        return None, JSONResponse(
            {"error": f"Unsupported for world_type={instance.world_type}"},
            status_code=400,
        )

    return instance, None
