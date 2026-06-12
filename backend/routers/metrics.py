"""Metrics history REST API router."""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the metrics history router."""
    router = APIRouter(prefix="/api/world", tags=["metrics"])

    @router.get("/{world_id}/metrics/history")
    async def get_metrics_history(world_id: str) -> JSONResponse:
        """Get metrics history for a specific world."""
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        runner = instance.runner
        metrics_history = getattr(runner, "metrics_history", None)
        if metrics_history is None:
            return JSONResponse(
                {
                    "schema_version": 1,
                    "world_id": world_id,
                    "sample_interval_frames": 500,
                    "max_samples": 2000,
                    "samples": [],
                }
            )

        return JSONResponse(metrics_history.to_payload())

    return router
