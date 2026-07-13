"""Skill-ladder standings REST API router.

Exposes the frozen-ruler skill summaries embedded in the champion registry so
the frontend can show, per domain, how good the evolved agents are in absolute
terms and how close they are to each ladder's ceiling. Stateless and
world-independent: it reads ``champions/**/*.json`` on request.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from core.skill import load_ladder_summaries

logger = logging.getLogger(__name__)

# Repo-root-relative champions directory (backend/ -> repo root -> champions).
_CHAMPIONS_DIR = Path(__file__).resolve().parents[2] / "champions"

SCHEMA_VERSION = 1


_FORAGING_GYM_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}
_FORAGING_GYM_SUMMARY_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)


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

    @router.get("/foraging-gym")
    async def run_foraging_gym(
        seed: int = Query(default=42, ge=0, le=2_147_483_647)
    ) -> JSONResponse:
        """Run the isolated foraging ruler for one deterministic seed.

        Unlike ``/ladders``, this evaluates the current source tree directly.
        It lets the UI inspect the foraging substrate before a benchmark result
        is promoted to the champion registry.
        """
        from benchmarks.tank.foraging_gym import run

        return JSONResponse(run(seed))

    @router.get("/foraging-gym/summary")
    async def get_foraging_gym_summary() -> JSONResponse:
        """Return the aggregated foraging gym summary across versioned seeds."""
        from benchmarks.tank.foraging_gym import CONFIG as FORAGING_GYM_CONFIG
        from benchmarks.tank.foraging_gym import BENCHMARK_ID as FORAGING_GYM_ID
        from core.solutions.config_hash import compute_config_hash

        # Include the fixed trial cohort in the hash so changing it invalidates
        # the cached aggregate rather than reusing stale summary data.
        summary_config = {
            **FORAGING_GYM_CONFIG,
            "summary_seeds": _FORAGING_GYM_SUMMARY_SEEDS,
        }
        config_hash = compute_config_hash(
            benchmark_id=FORAGING_GYM_ID,
            seed=0,
            benchmark_config=summary_config,
        )

        if config_hash in _FORAGING_GYM_SUMMARY_CACHE:
            return JSONResponse(_FORAGING_GYM_SUMMARY_CACHE[config_hash])

        # Run the versioned set of 8 seeds
        seeds = _FORAGING_GYM_SUMMARY_SEEDS
        from benchmarks.tank.foraging_gym import run as run_gym

        per_seed_results = {}
        scores = []
        wandering_scores = []
        food_collected_list = []
        energy_collected_list = []

        for s in seeds:
            res = run_gym(s)
            per_seed_results[str(s)] = res
            scores.append(res["score"])
            wandering_scores.append(res["score_breakdown"]["random_walk_energy_ratio"])
            composable_meta = res["metadata"]["composable"]
            food_collected_list.append(composable_meta["food_collected"])
            energy_collected_list.append(composable_meta["energy_collected"])

        import math

        n = len(scores)
        mean_score = sum(scores) / n
        wandering_mean = sum(wandering_scores) / n
        perfect_mean = 1.0  # Oracle is always 1.0

        # Calculate 95% confidence interval using t-distribution for n=8 (df=7, t=2.365)
        if n > 1:
            variance = sum((x - mean_score) ** 2 for x in scores) / (n - 1)
            std_dev = math.sqrt(variance)
            std_err = std_dev / math.sqrt(n)
            margin = 2.365 * std_err
            ci_lower = max(0.0, mean_score - margin)
            ci_upper = min(1.0, mean_score + margin)
        else:
            ci_lower = mean_score
            ci_upper = mean_score

        summary = {
            "subject": "engine_baseline",
            "config_hash": config_hash,
            "mean": mean_score,
            "wandering_mean": wandering_mean,
            "perfect_mean": perfect_mean,
            "confidence_interval": [ci_lower, ci_upper],
            "range": [min(scores), max(scores)],
            "average_food": sum(food_collected_list) / n,
            "average_energy": sum(energy_collected_list) / n,
            "metadata": {
                "seeds": list(seeds),
                "per_seed": per_seed_results,
            },
        }

        _FORAGING_GYM_SUMMARY_CACHE[config_hash] = summary
        return JSONResponse(summary)

    return router
