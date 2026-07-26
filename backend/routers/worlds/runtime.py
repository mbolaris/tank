"""Playback control endpoints: step, pause, resume, fast-forward."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def register(router: APIRouter, world_manager: WorldManager) -> None:
    """Attach playback-control endpoints to ``router``."""

    @router.post("/{world_id}/step")
    async def step_world(world_id: str, actions: dict[str, Any] | None = None):
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
