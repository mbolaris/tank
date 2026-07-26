"""Endpoints that operate on the world collection rather than one instance.

These routes use literal path segments ("/types", "/evolution-benchmark",
"/default/id") that share a path-segment count with ``instance``'s
``/{world_id}`` catch-all. FastAPI/Starlette matches routes in registration
order, so this module's router must be attached before ``instance``'s or a
request like ``GET /api/worlds/types`` would be swallowed by
``GET /{world_id}`` with ``world_id="types"``. See ``worlds/__init__.py``.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.routers.worlds.models import CreateWorldRequest, WorldTypeResponse
from backend.world_manager import WorldManager
from backend.world_registry import get_all_world_metadata
from core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def register(router: APIRouter, world_manager: WorldManager) -> None:
    """Attach collection-level endpoints to ``router``."""

    @router.get("/types", response_model=list[WorldTypeResponse])
    async def list_world_types():
        """List all available world types with their capabilities.

        Returns a list of registered world types including:
        - mode_id: The mode identifier (e.g., "tank", "petri")
        - world_type: The underlying world type
        - view_mode: Default view mode for rendering ("side", "topdown", etc.)
        - display_name: Human-readable name
        - supports_persistence: Whether the world can be saved/restored
        - supports_actions: Whether the world requires agent actions
        """
        metadata_list = get_all_world_metadata()
        return [
            WorldTypeResponse(
                mode_id=m.mode_id,
                world_type=m.world_type,
                view_mode=m.view_mode,
                display_name=m.display_name,
                supports_persistence=m.supports_persistence,
                supports_actions=m.supports_actions,
                supports_websocket=m.supports_websocket,
                supports_transfer=m.supports_transfer,
                has_fish=m.has_fish,
            )
            for m in metadata_list
        ]

    @router.post("")
    async def create_world(request: CreateWorldRequest):
        """Create a new world instance.

        Args:
            request: CreateWorldRequest with world_type, name, config, etc.

        Returns:
            WorldStatus for the created world
        """
        try:
            instance = world_manager.create_world(
                world_type=request.world_type,
                name=request.name,
                config=request.config,
                persistent=request.persistent,
                seed=request.seed,
                description=request.description,
                start_paused=request.start_paused,
            )
            return JSONResponse(
                {
                    "world_id": instance.world_id,
                    "world_type": instance.world_type,
                    "mode_id": instance.mode_id,
                    "name": instance.name,
                    "view_mode": instance.view_mode,
                    "persistent": instance.persistent,
                    "message": f"Created {instance.world_type} world: {instance.name}",
                },
                status_code=201,
            )
        except (ConfigurationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error creating world: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("")
    async def list_worlds(world_type: str | None = None):
        """List all active worlds.

        Args:
            world_type: Optional filter by world type

        Returns:
            List of world statuses
        """
        worlds = world_manager.list_worlds(world_type=world_type)
        return JSONResponse(
            {
                "worlds": [w.to_dict() for w in worlds],
                "count": len(worlds),
            }
        )

    @router.get("/evolution-benchmark")
    async def get_default_evolution_benchmark():
        """Get evolution benchmark data for the default world.

        Returns:
            Benchmark history, latest snapshot, and improvement metrics
        """
        worlds = world_manager.list_worlds()
        if not worlds:
            return JSONResponse(
                {"status": "not_available", "history": [], "improvement": {}, "latest": None}
            )

        # Use first world as default
        instance = world_manager.get_world(worlds[0].world_id)
        if instance is None:
            return JSONResponse(
                {"status": "not_available", "history": [], "improvement": {}, "latest": None}
            )

        data = instance.runner.get_evolution_benchmark_data()
        return JSONResponse(data)

    @router.get("/default/id")
    async def get_default_world_id():
        """Get the default world ID.

        Returns:
            The ID of the default world (first world in the list)
        """
        worlds = world_manager.list_worlds()
        if not worlds:
            raise HTTPException(status_code=404, detail="No worlds available")

        return JSONResponse({"world_id": worlds[0].world_id})
