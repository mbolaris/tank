"""Skill-ladder standings REST API router.

Exposes the frozen-ruler skill summaries embedded in the champion registry so
the frontend can show, per domain, how good the evolved agents are in absolute
terms and how close they are to each ladder's ceiling. Stateless and
world-independent: it reads ``champions/**/*.json`` on request.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.skill import load_ladder_summaries

logger = logging.getLogger(__name__)

# Repo-root-relative champions directory (backend/ -> repo root -> champions).
_CHAMPIONS_DIR = Path(__file__).resolve().parents[2] / "champions"

SCHEMA_VERSION = 1


def setup_router(champions_dir: Path | None = None) -> APIRouter:
    """Create the skill-ladder standings router."""
    router = APIRouter(prefix="/api/skill", tags=["skill"])
    resolved_dir = champions_dir or _CHAMPIONS_DIR

    @router.get("/ladders")
    async def get_skill_ladders() -> JSONResponse:
        """Return skill-ladder summaries for every domain that emits one."""
        try:
            summaries = load_ladder_summaries(resolved_dir)
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read champion registry: %s", exc)
            summaries = []
        return JSONResponse(
            {
                "schema_version": SCHEMA_VERSION,
                "ladders": [s.to_dict() for s in summaries],
            }
        )

    return router
