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


from benchmarks.tank.foraging_gym import SUMMARY_SEEDS as _FORAGING_GYM_SUMMARY_SEEDS

_FORAGING_GYM_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}


def setup_router(
    champions_dir: Path | None = None,
    world_manager: Any | None = None,
) -> APIRouter:
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
    def run_foraging_gym(seed: int = Query(default=42, ge=0, le=2_147_483_647)) -> JSONResponse:
        """Run the isolated foraging ruler for one deterministic seed.

        Unlike ``/ladders``, this evaluates the current source tree directly.
        It lets the UI inspect the foraging substrate before a benchmark result
        is promoted to the champion registry.
        """
        from benchmarks.tank.foraging_gym import run

        return JSONResponse(run(seed))

    @router.get("/foraging-gym/summary")
    def get_foraging_gym_summary() -> JSONResponse:
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
            "benchmark_id": FORAGING_GYM_ID,
            "config_hash": config_hash,
            "mean": mean_score,
            "wandering_mean": wandering_mean,
            "perfect_mean": perfect_mean,
            "confidence_interval": [ci_lower, ci_upper],
            "range": [min(scores), max(scores)],
            "average_food": sum(food_collected_list) / n,
            "average_food_available": sum(
                res["metadata"]["oracle"]["food_collected"] for res in per_seed_results.values()
            )
            / n,
            "average_energy": sum(energy_collected_list) / n,
            "metadata": {
                "seeds": list(seeds),
                "per_seed": per_seed_results,
            },
        }

        _FORAGING_GYM_SUMMARY_CACHE[config_hash] = summary
        return JSONResponse(summary)

    @router.get("/foraging-gym/observatory")
    def get_foraging_gym_observatory(world_id: str | None = Query(default=None)) -> JSONResponse:
        """Evaluate the simulated fish in the foraging gym and return tank observatory standings."""
        import hashlib
        import json
        from core.genetics.genome import GENOME_SCHEMA_VERSION
        from core.genetics.genome_codec import genome_to_dict
        from core.foraging.gym import evaluate_custom_genome
        from core.entities.fish import Fish

        if world_manager is None:
            return JSONResponse(
                {"status": "no_data", "message": "World manager not available"},
                status_code=200,
            )

        worlds = world_manager.list_worlds()
        if not worlds:
            return JSONResponse(
                {"status": "no_data", "message": "No active worlds available"},
                status_code=200,
            )

        resolved_world_id = world_id
        if not resolved_world_id or resolved_world_id == "default":
            resolved_world_id = worlds[0].world_id

        instance = world_manager.get_world(resolved_world_id)
        if instance is None:
            return JSONResponse(
                {"status": "no_data", "message": f"World {resolved_world_id} not found"},
                status_code=200,
            )

        runner = instance.runner
        if not hasattr(runner, "world") or not runner.world:
            return JSONResponse(
                {"status": "no_data", "message": "World not initialized"},
                status_code=200,
            )

        living_fish = [e for e in runner.world.entities_list if isinstance(e, Fish)]
        if not living_fish:
            return JSONResponse(
                {"status": "no_data", "message": "No living fish in the tank"},
                status_code=200,
            )

        taxonomy = getattr(runner.world, "ecosystem", None) and getattr(
            runner.world.ecosystem, "taxonomy", None
        )
        if not taxonomy or not hasattr(taxonomy, "registry"):
            return JSONResponse(
                {"status": "no_data", "message": "Taxonomy system not available"},
                status_code=200,
            )

        species_registry = taxonomy.registry
        active_species = [
            rec for rec in species_registry.species.values() if len(rec.living_member_ids) > 0
        ]
        if not active_species:
            return JSONResponse(
                {"status": "no_data", "message": "No active species classification found"},
                status_code=200,
            )

        # Helpers for genome fingerprinting and caching
        def get_genome_fingerprint(genome: Any) -> str:
            payload = genome_to_dict(genome, schema_version=GENOME_SCHEMA_VERSION)
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]

        from benchmarks.tank.foraging_gym import CONFIG as FORAGING_GYM_CONFIG
        from benchmarks.tank.foraging_gym import BENCHMARK_ID as FORAGING_GYM_ID
        from core.solutions.config_hash import compute_config_hash

        summary_config = {
            **FORAGING_GYM_CONFIG,
            "summary_seeds": _FORAGING_GYM_SUMMARY_SEEDS,
        }
        config_hash = compute_config_hash(
            benchmark_id=FORAGING_GYM_ID,
            seed=0,
            benchmark_config=summary_config,
        )

        global _OBSERVATORY_EVALUATION_CACHE
        if "_OBSERVATORY_EVALUATION_CACHE" not in globals():
            globals()["_OBSERVATORY_EVALUATION_CACHE"] = {}
        cache: dict[tuple[str, str], dict[str, Any]] = globals()["_OBSERVATORY_EVALUATION_CACHE"]

        def evaluate_genome_cached(genome: Any) -> dict[str, Any]:
            fingerprint = get_genome_fingerprint(genome)
            cache_key = (fingerprint, config_hash)
            if cache_key in cache:
                return cache[cache_key]

            scores = []
            food_collected_list = []
            for s in _FORAGING_GYM_SUMMARY_SEEDS:
                res = evaluate_custom_genome(genome, s)
                scores.append(res.composable_ratio)
                food_collected_list.append(res.composable.food_collected)

            result = {
                "score": sum(scores) / len(scores),
                "average_food": sum(food_collected_list) / len(food_collected_list),
            }
            cache[cache_key] = result
            return result

        # Evaluate each living fish
        fish_evals = []
        for fish in living_fish:
            eval_res = evaluate_genome_cached(fish.genome)
            fish_evals.append(
                {
                    "fish": fish,
                    "score": eval_res["score"],
                    "average_food": eval_res["average_food"],
                }
            )

        # Calculate Tank Average
        tank_average = sum(item["score"] for item in fish_evals) / len(fish_evals)

        # Group fish evaluations by species
        species_scores: dict[str, list[float]] = {}
        for item in fish_evals:
            tid = item["fish"].taxon_id
            if tid not in species_scores:
                species_scores[tid] = []
            species_scores[tid].append(item["score"])

        # Calculate average score per species and find best species
        species_averages = {}
        for tid, scores in species_scores.items():
            species_averages[tid] = sum(scores) / len(scores)

        best_taxon_id = max(species_averages, key=lambda tid: species_averages[tid])
        best_species_score = species_averages[best_taxon_id]

        best_species_rec = species_registry.species.get(best_taxon_id)
        best_species_name = best_species_rec.common_name if best_species_rec else "Unknown Species"

        # Find best individual
        best_item = max(fish_evals, key=lambda item: item["score"])
        best_fish = best_item["fish"]
        best_score = best_item["score"]

        # Best individual details
        best_ind_species_rec = species_registry.species.get(best_fish.taxon_id)
        prediction_strength_after = float(best_fish.genome.behavioral.prediction_skill.value)
        prediction_strength_before = 0.5
        if best_ind_species_rec and "prediction_skill" in best_ind_species_rec.type_profile.traits:
            prediction_strength_before = best_ind_species_rec.type_profile.traits[
                "prediction_skill"
            ]

        # Percentage of its species population sharing the same genome fingerprint
        species_fish_items = [
            item for item in fish_evals if item["fish"].taxon_id == best_fish.taxon_id
        ]
        best_fingerprint = get_genome_fingerprint(best_fish.genome)
        same_fingerprint_count = sum(
            1
            for item in species_fish_items
            if get_genome_fingerprint(item["fish"].genome) == best_fingerprint
        )
        percentage = (
            (same_fingerprint_count / len(species_fish_items)) * 100.0
            if species_fish_items
            else 100.0
        )

        # Lineage improvement checks (and post commentary if meaningfully improved)
        global _SPECIES_SCORE_HISTORY
        if "_SPECIES_SCORE_HISTORY" not in globals():
            globals()["_SPECIES_SCORE_HISTORY"] = {}
        history = globals()["_SPECIES_SCORE_HISTORY"]

        for rec in active_species:
            if rec.taxon_id in species_averages:
                new_score = species_averages[rec.taxon_id]
                history_key = (resolved_world_id, rec.taxon_id)
                if history_key in history:
                    old_score = history[history_key]
                    diff = round(new_score * 100) - round(old_score * 100)
                    if diff >= 3:
                        # Log/Post commentary event
                        comment_text = (
                            f"A new pursuit strategy in the {rec.common_name} "
                            f"raised their foraging score from {round(old_score * 100)} to {round(new_score * 100)}."
                        )
                        try:
                            runner.add_commentary(
                                comment_text,
                                author="observatory",
                                tags=["evolution", "foraging", "observatory"],
                                severity="insight",
                                metrics={
                                    "taxon_id": rec.taxon_id,
                                    "previous_score": old_score,
                                    "new_score": new_score,
                                },
                            )
                        except Exception as e:
                            logger.error(f"Failed to add observatory commentary: {e}")
                # Update history
                history[history_key] = new_score

        # Get default/baseline controller scores from summary cache block
        # We run the baseline setup logic if not already done, or call it
        # Since it is fast/cached, we just run the cache block
        baseline_summary_config = {
            **FORAGING_GYM_CONFIG,
            "summary_seeds": _FORAGING_GYM_SUMMARY_SEEDS,
        }
        baseline_config_hash = compute_config_hash(
            benchmark_id=FORAGING_GYM_ID,
            seed=0,
            benchmark_config=baseline_summary_config,
        )

        # Retrieve baseline from summary cache
        if baseline_config_hash in _FORAGING_GYM_SUMMARY_CACHE:
            baseline_data = _FORAGING_GYM_SUMMARY_CACHE[baseline_config_hash]
            baseline_mean = baseline_data["mean"]
            wandering_mean = baseline_data["wandering_mean"]
            perfect_mean = baseline_data["perfect_mean"]
        else:
            # Fallback evaluation for baseline if not yet in cache
            from benchmarks.tank.foraging_gym import run as run_gym

            baseline_scores = []
            baseline_wandering_scores = []
            for s in _FORAGING_GYM_SUMMARY_SEEDS:
                res = run_gym(s)
                baseline_scores.append(res["score"])
                baseline_wandering_scores.append(res["score_breakdown"]["random_walk_energy_ratio"])
            baseline_mean = sum(baseline_scores) / len(baseline_scores)
            wandering_mean = sum(baseline_wandering_scores) / len(baseline_wandering_scores)
            perfect_mean = 1.0

        return JSONResponse(
            {
                "status": "success",
                "tank_average": tank_average,
                "best_species": {
                    "name": best_species_name,
                    "score": best_species_score,
                },
                "best_individual": {
                    "id": best_fish.fish_id,
                    "name": f"{best_fish.common_name} #{best_fish.fish_id}",
                    "score": best_score,
                    "food_collected": best_item["average_food"],
                    "food_available": 12.0,
                    "prediction_strength_before": prediction_strength_before,
                    "prediction_strength_after": prediction_strength_after,
                    "percentage_of_species": percentage,
                },
                "engine_baseline": baseline_mean,
                "wandering_mean": wandering_mean,
                "perfect_mean": perfect_mean,
            }
        )

    return router
