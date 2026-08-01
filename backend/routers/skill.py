"""Skill-ladder standings REST API router.

Exposes frozen-ruler skill summaries embedded in the champion registry and the
latest asynchronous Tank Skill Observatory results. All evaluation, scoring,
and caching logic lives in ``backend.skill_observatory`` and its
``_policies``/``_scoring`` companions; this router only validates input,
delegates, and wraps results as JSON. Observatory evaluations are performed
by ``SkillEvaluationService``; GET requests only read completed data.
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.skill_evaluation_service import SkillEvaluationService
from backend.skill_observatory import build_observatory_snapshot, evaluate_observatory_snapshot
from backend.skill_observatory_scoring import compute_foraging_gym_summary
from core.skill import load_ladder_summaries

logger = logging.getLogger(__name__)

# Repo-root-relative champions directory (backend/ -> repo root -> champions).
_CHAMPIONS_DIR = Path(__file__).resolve().parents[2] / "champions"

SCHEMA_VERSION = 1


def setup_router(
    champions_dir: Path | None = None,
    world_manager: Any | None = None,
    evaluation_service: SkillEvaluationService | None = None,
) -> APIRouter:
    """Create the skill-ladder standings router."""
    router = APIRouter(tags=["skill"])
    resolved_dir = champions_dir or _CHAMPIONS_DIR
    if evaluation_service is None:
        evaluation_service = SkillEvaluationService(world_manager)

    @router.get("/api/skill/ladders")
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

    @router.get("/api/skill/foraging-gym")
    def run_foraging_gym(seed: int = Query(default=42, ge=0, le=2_147_483_647)) -> JSONResponse:
        """Run the isolated foraging ruler for one deterministic seed.

        Unlike ``/ladders``, this evaluates the current source tree directly.
        It lets the UI inspect the foraging substrate before a benchmark result
        is promoted to the champion registry.
        """
        from benchmarks.tank.foraging_gym import run

        return JSONResponse(run(seed))

    @router.get("/api/skill/foraging-gym/summary")
    def get_foraging_gym_summary(
        world_id: str | None = Query(default=None),
    ) -> JSONResponse:
        """Return the aggregated foraging gym summary across versioned seeds."""
        return JSONResponse(compute_foraging_gym_summary())

    # The background worker (asyncio.to_thread) must never touch live
    # simulation state - build_observatory_snapshot captures everything it
    # needs synchronously first, on this coroutine's own thread, and
    # evaluate_observatory_snapshot then runs as a pure function of that
    # immutable snapshot. See backend.skill_observatory for both.
    evaluation_service.set_snapshot_builder(
        functools.partial(build_observatory_snapshot, world_manager)
    )
    evaluation_service.set_evaluator(evaluate_observatory_snapshot)

    @router.get("/api/skill/foraging-gym/observatory")
    def get_foraging_gym_observatory(world_id: str | None = Query(default=None)) -> JSONResponse:
        """Return the latest completed result without starting an evaluation."""
        if world_manager is None:
            return JSONResponse({"status": "no_data", "message": "World manager not available"})

        worlds = world_manager.list_worlds()
        if not worlds:
            return JSONResponse({"status": "no_data", "message": "No active worlds available"})

        resolved_world_id = world_id
        if not resolved_world_id or resolved_world_id == "default":
            resolved_world_id = worlds[0].world_id

        latest = evaluation_service.get_latest(resolved_world_id)
        if latest is None:
            latest = {
                "status": "no_data",
                "world_id": resolved_world_id,
                "message": "Skill evaluation is pending; showing the last completed result when ready.",
            }
        return JSONResponse(latest)

    @router.get("/api/skill/snapshots")
    @router.get("/api/world/{world_id}/skill/snapshots")
    def get_skill_snapshots(
        world_id: str | None = None,
        domain: str | None = Query(default=None),
        limit: int | None = Query(default=None, ge=1, le=100),
    ) -> JSONResponse:
        """Return recorded live skill snapshots for a world."""
        if world_manager is None:
            return JSONResponse({"status": "no_data", "message": "World manager not available"})

        worlds = world_manager.list_worlds()
        if not worlds:
            return JSONResponse({"status": "no_data", "message": "No active worlds available"})

        resolved_world_id = world_id
        if not resolved_world_id or resolved_world_id == "default":
            resolved_world_id = (
                getattr(world_manager, "default_world_id", None) or worlds[0].world_id
            )

        instance = world_manager.get_world(resolved_world_id)
        if instance is None:
            return JSONResponse(
                {
                    "schema_version": SCHEMA_VERSION,
                    "world_id": resolved_world_id,
                    "count": 0,
                    "tank_best": 0.0,
                    "latest_baseline_score_diff": None,
                    "snapshots": [],
                }
            )

        runner = getattr(instance, "runner", None)
        engine = getattr(runner, "engine", None) if runner else getattr(instance, "engine", None)
        store = getattr(engine, "skill_snapshot_store", None) if engine else None
        evaluator = getattr(engine, "soccer_ladder_evaluator", None) if engine else None

        if store is None:
            return JSONResponse(
                {
                    "schema_version": SCHEMA_VERSION,
                    "world_id": resolved_world_id,
                    "count": 0,
                    "tank_best": 0.0,
                    "latest_baseline_score_diff": None,
                    "snapshots": [],
                }
            )

        snapshots = store.get_snapshots(limit=limit, domain=domain)
        latest_diff = getattr(evaluator, "latest_baseline_score_diff", None) if evaluator else None

        return JSONResponse(
            {
                "schema_version": SCHEMA_VERSION,
                "world_id": resolved_world_id,
                "count": len(snapshots),
                "tank_best": store.tank_best,
                "latest_baseline_score_diff": latest_diff,
                "snapshots": [s.to_dict() for s in snapshots],
            }
        )

    return router
