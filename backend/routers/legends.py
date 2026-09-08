"""In-world legends REST API router (U8b/E6).

Read-only, like the story-event feed: legends are *promoted* by criteria that
read the simulation, never submitted by a client.

Endpoints (mounted under ``/api/world``):

    GET    /api/world/{world_id}/legends   list promoted legends
    DELETE /api/world/{world_id}/legends   clear the roster

``world_id`` accepts the literal ``"default"``.

These are in-world legends, not benchmark champions: the champion registry
(``champions/``) records reproducible best-known solutions and is served
elsewhere. Nothing here reads it.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.legends import LEGEND_KINDS
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the legends router."""
    router = APIRouter(prefix="/api/world", tags=["legends"])

    def _resolve_service(world_id: str):
        resolved = world_id
        if world_id == "default":
            resolved = world_manager.default_world_id or world_id
        instance = world_manager.get_world(resolved)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")
        service = getattr(instance.runner, "legends", None)
        if service is None:
            raise HTTPException(status_code=404, detail=f"World has no legend service: {world_id}")
        return service

    @router.get("/{world_id}/legends")
    async def get_legends(
        world_id: str,
        limit: int | None = Query(default=None, ge=0, le=200),
        since_id: int | None = Query(default=None, ge=0),
        kind: str | None = Query(default=None),
    ) -> JSONResponse:
        """List a world's legends (oldest first)."""
        if kind is not None and kind not in LEGEND_KINDS:
            raise HTTPException(status_code=400, detail=f"Unknown legend kind: {kind}")
        service = _resolve_service(world_id)
        legends = service.recent(limit=limit, since_id=since_id, kind=kind)
        return JSONResponse(
            {
                "schema_version": service.schema_version,
                "world_id": service.world_id,
                "kinds": list(LEGEND_KINDS),
                "count": len(legends),
                "legends": legends,
            }
        )

    @router.delete("/{world_id}/legends")
    async def clear_legends(world_id: str) -> JSONResponse:
        """Clear a world's legends, allowing re-promotion."""
        service = _resolve_service(world_id)
        return JSONResponse({"status": "ok", "cleared": service.clear()})

    return router
