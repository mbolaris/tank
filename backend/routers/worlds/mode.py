"""Endpoint for switching a world's active mode (e.g. tank <-> petri)."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.routers.worlds.models import UpdateWorldModeRequest
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def register(router: APIRouter, world_manager: WorldManager) -> None:
    """Attach the world-mode endpoint to ``router``."""

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
            raise HTTPException(status_code=400, detail=str(e)) from e
