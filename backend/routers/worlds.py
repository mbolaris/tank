"""World-agnostic API endpoints for managing worlds of any type.

This router provides endpoints for creating, listing, and managing
worlds of all types (tank, petri) through a unified API.
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
    start_paused: bool = False


class UpdateWorldModeRequest(BaseModel):
    """Request body for updating world mode."""

    world_type: str


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
    has_fish: bool


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

        return JSONResponse(
            {
                "world_id": instance.world_id,
                "world_type": instance.world_type,
                "mode_id": instance.mode_id,
                "name": instance.name,
                "view_mode": instance.view_mode,
                "persistent": instance.persistent,
                "frame_count": instance.runner.frame_count,
                "paused": instance.runner.paused,
                "description": instance.description,
            }
        )

    @router.get("/{world_id}/snapshot")
    async def get_world_snapshot(world_id: str):
        """Get the latest snapshot of a world.

        Args:
            world_id: The world ID

        Returns:
            The full simulation state snapshot
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        state = instance.runner.get_state(force_full=True)
        if state:
            return JSONResponse(state.to_dict())

        return JSONResponse({"error": "Snapshot not available"}, status_code=503)

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
            return JSONResponse(
                {
                    "world_id": world_id,
                    "frame_count": instance.runner.frame_count if instance else 0,
                }
            )
        else:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

    @router.post("/{world_id}/pause")
    async def pause_world(world_id: str):
        """Pause a running world.

        Args:
            world_id: The world ID to pause

        Returns:
            Updated paused state or 404 if not found
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        instance.runner.paused = True
        return JSONResponse(
            {
                "world_id": world_id,
                "paused": True,
                "message": f"World {world_id[:8]} paused",
            }
        )

    @router.post("/{world_id}/resume")
    async def resume_world(world_id: str):
        """Resume a paused world.

        Args:
            world_id: The world ID to resume

        Returns:
            Updated paused state or 404 if not found
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        instance.runner.paused = False
        return JSONResponse(
            {
                "world_id": world_id,
                "paused": False,
                "message": f"World {world_id[:8]} resumed",
            }
        )

    @router.post("/{world_id}/fast_forward")
    async def set_fast_forward(world_id: str, enabled: bool):
        """Set fast forward mode.

        Args:
            world_id: The world ID
            enabled: Whether to enable fast forward

        Returns:
            Updated state
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        instance.runner.fast_forward = enabled
        return JSONResponse(
            {
                "world_id": world_id,
                "fast_forward": enabled,
                "message": f"World {world_id[:8]} fast forward {'enabled' if enabled else 'disabled'}",
            }
        )

    @router.get("/{world_id}/evolution-benchmark")
    async def get_evolution_benchmark(world_id: str):
        """Get evolution benchmark data for a world.

        Args:
            world_id: The world ID

        Returns:
            Benchmark history, latest snapshot, and improvement metrics
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        data = instance.runner.get_evolution_benchmark_data()
        return JSONResponse(data)

    @router.get("/{world_id}/lineage")
    async def get_world_lineage(world_id: str):
        """Get lineage data for phylogenetic tree visualization.

        Args:
            world_id: The world ID

        Returns:
            List of lineage records with parent-child relationships
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        # Access the lineage data through the runner's world ecosystem
        try:
            runner = instance.runner
            # SimulationRunner has self.world with ecosystem
            if hasattr(runner, "world") and hasattr(runner.world, "ecosystem"):
                ecosystem = runner.world.ecosystem
                if hasattr(ecosystem, "get_lineage_data"):
                    # Get alive fish IDs for enrichment
                    alive_fish_ids = None
                    if hasattr(runner.world, "entities_list"):
                        # Use snapshot_type for generic entity classification
                        alive_fish_ids = {
                            e.fish_id
                            for e in runner.world.entities_list
                            if getattr(e, "snapshot_type", None) == "fish"
                        }
                    lineage_data = ecosystem.get_lineage_data(alive_fish_ids)
                    return JSONResponse(lineage_data)

            # Fallback: lineage not available for this world type
            return JSONResponse([])
        except Exception as e:
            logger.error(f"Error getting lineage data: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error getting lineage data: {e}")

    @router.put("/{world_id}/mode")
    async def update_world_mode(world_id: str, request: UpdateWorldModeRequest):
        """Update the world mode (e.g., switch between tank and petri).

        Args:
            world_id: The world ID to update
            request: The update request containing the new world type

        Returns:
            Updated world info
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        try:
            # Use the runner's switch_world_type method (part of RunnerProtocol)
            # WorldRunner raises ValueError if switching not supported
            instance.runner.switch_world_type(request.world_type)

            # Update instance metadata to match
            instance.world_type = request.world_type
            instance.mode_id = instance.runner.mode_id
            instance.view_mode = instance.runner.view_mode

            return JSONResponse(
                {
                    "world_id": world_id,
                    "world_type": request.world_type,
                    "mode_id": instance.mode_id,
                    "view_mode": instance.view_mode,
                    "message": f"World type changed to {request.world_type}",
                }
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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

    return router
