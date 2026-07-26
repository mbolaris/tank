"""Read/delete endpoints addressed by a single ``world_id``.

``GET /{world_id}`` is a catch-all for any single path segment under the
worlds prefix, so this module's router must be attached *after*
``collection``'s (which owns the literal single-segment routes like
``/types``). See ``worlds/__init__.py``.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def register(router: APIRouter, world_manager: WorldManager) -> None:
    """Attach single-world read/delete endpoints to ``router``."""

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
        if await world_manager.delete_world_async(world_id):
            return JSONResponse({"message": f"World {world_id} deleted"})
        else:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")
