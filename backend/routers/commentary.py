"""Agent commentary REST API router (the "Insights" feed).

This is the network surface for the Insights feature: any agent (or human) with
access to the simulation server can POST a short observation about a running
world, and the web UI polls these endpoints to render them as a live feed.

Endpoints (mounted under ``/api/world``):

    POST   /api/world/{world_id}/commentary   add a comment
    GET    /api/world/{world_id}/commentary   list recent comments
    DELETE /api/world/{world_id}/commentary   clear all comments

``world_id`` accepts the literal ``"default"`` to target the server's default
world, so an agent can comment without first discovering the world id. The write
path is purely additive telemetry (see ``SimulationRunner.add_commentary``); it
never mutates simulation state.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


class CommentaryRequest(BaseModel):
    """Body for posting a comment.

    Only ``text`` is required. ``tags`` is intentionally permissive (a list of
    strings or a single comma/space-separated string) and every field is
    sanitized by ``CommentaryStore.add`` so a slightly-malformed agent payload
    still lands as a usable comment instead of a 422.
    """

    text: str
    author: str | None = None
    tags: Any = None
    severity: str | None = None
    metrics: dict[str, Any] | None = None


def setup_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the commentary router."""
    router = APIRouter(prefix="/api/world", tags=["commentary"])

    def _resolve_world(world_id: str):
        """Resolve a world id (supporting "default"); raise 404 if unknown."""
        resolved = world_id
        if world_id == "default":
            resolved = world_manager.default_world_id or world_id
        instance = world_manager.get_world(resolved)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")
        return instance

    @router.post("/{world_id}/commentary")
    async def post_commentary(world_id: str, request: CommentaryRequest) -> JSONResponse:
        """Add an agent observation to a world's commentary feed."""
        instance = _resolve_world(world_id)
        try:
            comment = instance.runner.add_commentary(
                request.text,
                author=request.author,
                tags=request.tags,
                severity=request.severity,
                metrics=request.metrics,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return JSONResponse({"status": "ok", "comment": comment}, status_code=201)

    @router.get("/{world_id}/commentary")
    async def get_commentary(
        world_id: str,
        limit: int | None = Query(default=None, ge=0, le=500),
        since_id: int | None = Query(default=None, ge=0),
    ) -> JSONResponse:
        """List recent comments for a world (newest last).

        ``since_id`` returns only comments newer than that id (incremental
        polling); ``limit`` caps the result to the most recent N.
        """
        instance = _resolve_world(world_id)
        store = instance.runner.commentary
        comments = store.recent(limit=limit, since_id=since_id)
        return JSONResponse(
            {
                "schema_version": store.schema_version,
                "world_id": store.world_id,
                "count": len(comments),
                "comments": comments,
            }
        )

    @router.delete("/{world_id}/commentary")
    async def clear_commentary(world_id: str) -> JSONResponse:
        """Clear all comments for a world."""
        instance = _resolve_world(world_id)
        cleared = instance.runner.commentary.clear()
        return JSONResponse({"status": "ok", "cleared": cleared})

    return router
