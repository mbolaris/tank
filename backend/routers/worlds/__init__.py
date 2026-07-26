"""World-agnostic API endpoints for managing worlds of any type.

This router provides endpoints for creating, listing, and managing
worlds of all types (tank, petri) through a unified API. The endpoint
implementations are split across sibling modules by concern (collection,
single-instance reads, playback control, telemetry, mode-switching); this
module only assembles them in the order route-matching requires.
"""

from fastapi import APIRouter

from backend.routers.worlds import collection, instance, mode, runtime, telemetry
from backend.world_manager import WorldManager


def setup_worlds_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the worlds router.

    Args:
        world_manager: The WorldManager instance for world operations

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/worlds", tags=["worlds"])

    # `collection` owns the literal single-path-segment routes ("/types",
    # "/evolution-benchmark", "" ). It must be registered before `instance`,
    # whose "/{world_id}" is a same-segment-count catch-all: Starlette matches
    # routes in registration order, so a literal route registered after the
    # catch-all would never be reached.
    collection.register(router, world_manager)
    instance.register(router, world_manager)
    runtime.register(router, world_manager)
    telemetry.register(router, world_manager)
    mode.register(router, world_manager)

    return router
