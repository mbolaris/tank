"""World-agnostic API endpoints for managing worlds of any type.

This router provides endpoints for creating, listing, and managing
worlds of all types (tank, petri, soccer) through a unified API.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.world_manager import WorldManager
from backend.world_registry import get_all_world_metadata

logger = logging.getLogger(__name__)


class CreateWorldRequest(BaseModel):
    """Request body for creating a new world."""

    world_type: str
    name: str
    config: Optional[Dict[str, Any]] = None
    persistent: bool = True
    seed: Optional[int] = None
    description: str = ""


class WorldTypeResponse(BaseModel):
    """Response for a single world type."""

    mode_id: str
    world_type: str
    view_mode: str
    display_name: str
    supports_persistence: bool
    supports_actions: bool
    supports_websocket: bool
    supports_transfer: bool


def setup_worlds_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the worlds router.

    Args:
        world_manager: The WorldManager instance for world operations

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/worlds", tags=["worlds"])

    @router.get("/types", response_model=List[WorldTypeResponse])
    async def list_world_types():
        """List all available world types with their capabilities.

        Returns a list of registered world types including:
        - mode_id: The mode identifier (e.g., "tank", "petri", "soccer")
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
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating world: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("")
    async def list_worlds(world_type: Optional[str] = None):
        """List all active worlds.

        Args:
            world_type: Optional filter by world type

        Returns:
            List of world statuses
        """
        worlds = world_manager.list_worlds(world_type=world_type)
        return JSONResponse({
            "worlds": [w.to_dict() for w in worlds],
            "count": len(worlds),
        })

    @router.get("/{world_id}")
    async def get_world(world_id: str):
        """Get information about a specific world.

        Args:
            world_id: The unique world identifier

        Returns:
            World status or 404 if not found
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        return JSONResponse({
            "world_id": instance.world_id,
            "world_type": instance.world_type,
            "mode_id": instance.mode_id,
            "name": instance.name,
            "view_mode": instance.view_mode,
            "persistent": instance.persistent,
            "frame_count": instance.runner.frame_count,
            "paused": instance.runner.paused,
            "description": instance.description,
        })

    @router.delete("/{world_id}")
    async def delete_world(world_id: str):
        """Delete a world instance.

        Args:
            world_id: The world ID to delete

        Returns:
            Success message or 404 if not found
        """
        if world_manager.delete_world(world_id):
            return JSONResponse({"message": f"World {world_id} deleted"})
        else:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

    @router.post("/{world_id}/step")
    async def step_world(world_id: str, actions: Optional[Dict[str, Any]] = None):
        """Step a world by one frame.

        Args:
            world_id: The world ID to step
            actions: Optional actions for agent-controlled worlds

        Returns:
            Updated frame count or 404 if not found
        """
        if world_manager.step_world(world_id, actions):
            instance = world_manager.get_world(world_id)
            return JSONResponse({
                "world_id": world_id,
                "frame_count": instance.runner.frame_count if instance else 0,
            })
        else:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

    return router
