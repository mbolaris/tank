"""Story-event REST API router (the deterministic world-fact feed).

This is the read surface for the story-event service: the web UI (and any agent
studying a world) polls it to render what actually happened in the tank — a
population collapse, a generation milestone, one lineage taking over.

Endpoints (mounted under ``/api/world``):

    GET    /api/world/{world_id}/story-events   list recent events
    DELETE /api/world/{world_id}/story-events   clear the buffer

``world_id`` accepts the literal ``"default"`` to target the server's default
world, matching the commentary router. There is deliberately **no POST**: story
events are produced by detectors reading the simulation, not submitted by
clients. Agent-authored observations belong on the Board
(``/api/world/{world_id}/commentary``), and keeping the two surfaces separate is
what lets the UI show a visible distinction between a measured fact and an
opinion about it.

Poll incrementally with ``since_id``: ids are monotonic and are never reused,
even after old events scroll out of the bounded buffer.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.story_events import EVENT_TYPES
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_router(world_manager: WorldManager) -> APIRouter:
    """Create and configure the story-event router."""
    router = APIRouter(prefix="/api/world", tags=["story-events"])

    def _resolve_service(world_id: str):
        """Resolve a world id (supporting "default") to its story service."""
        resolved = world_id
        if world_id == "default":
            resolved = world_manager.default_world_id or world_id
        instance = world_manager.get_world(resolved)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")
        service = getattr(instance.runner, "story_events", None)
        if service is None:
            raise HTTPException(
                status_code=404, detail=f"World has no story-event service: {world_id}"
            )
        return service

    @router.get("/{world_id}/story-events")
    async def get_story_events(
        world_id: str,
        limit: int | None = Query(default=None, ge=0, le=500),
        since_id: int | None = Query(default=None, ge=0),
        event_type: str | None = Query(default=None),
    ) -> JSONResponse:
        """List recent story events for a world (oldest first).

        ``since_id`` returns only events newer than that id (incremental
        polling); ``limit`` caps the result to the most recent N; ``event_type``
        filters to a single type.
        """
        if event_type is not None and event_type not in EVENT_TYPES:
            raise HTTPException(status_code=400, detail=f"Unknown event_type: {event_type}")
        service = _resolve_service(world_id)
        events = service.recent(limit=limit, since_id=since_id, event_type=event_type)
        return JSONResponse(
            {
                "schema_version": service.schema_version,
                "world_id": service.world_id,
                "event_types": list(EVENT_TYPES),
                "last_observed_frame": service.last_observed_frame,
                "count": len(events),
                "events": events,
            }
        )

    @router.delete("/{world_id}/story-events")
    async def clear_story_events(world_id: str) -> JSONResponse:
        """Clear a world's story-event buffer. Ids stay monotonic afterwards."""
        service = _resolve_service(world_id)
        cleared = service.clear()
        return JSONResponse({"status": "ok", "cleared": cleared})

    return router
