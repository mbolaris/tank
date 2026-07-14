"""Skill-ladder standings REST API router.

Exposes frozen-ruler skill summaries embedded in the champion registry and the
latest asynchronous Tank Skill Observatory results. Observatory evaluations are
performed by ``SkillEvaluationService``; GET requests only read completed data.
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


_FORAGING_GYM_SUMMARY_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)

from typing import cast
from core.math_utils import Vector2
from core.foraging.gym import (
    _RandomWalkPolicy,
    _GymFish,
    _GymFood,
)
from core.movement_strategy import AlgorithmicMovement
from core.entities.fish import Fish
from backend.skill_evaluation_service import SkillEvaluationService
from backend.skill_observatory import (
    FishSkillSnapshot,
    SpeciesSkillSnapshot,
    WorldSkillSnapshot,
    evaluate_genome_with_cache,
    legacy_prediction_skill_of,
    module_fingerprint,
)


class _LegacyComposablePolicy:
    """Evaluates only the fish's inherited legacy ComposableBehavior."""

    def __init__(self, genome: Any, seed: int) -> None:
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        behavior_trait = getattr(genome.behavioral, "behavior", None)
        self._behavior = behavior_trait.value if behavior_trait is not None else None

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if self._behavior is None or not active_food:
            return self._wander.velocity(fish, active_food)

        fish_any: Any = fish
        fish_any.genome = self._genome

        vx, vy = self._behavior.execute(cast(Fish, fish_any))
        return Vector2(vx, vy)


class _SharedPursuitModulePolicy:
    """Evaluates the fish's inherited target_pursuit_module BehaviorGraph."""

    def __init__(self, genome: Any, seed: int) -> None:
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        module_trait = getattr(genome.behavioral, "target_pursuit_module", None)
        self._module = module_trait.value if module_trait is not None else None

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if self._module is None or not active_food:
            return self._wander.velocity(fish, active_food)

        from core.algorithms.composable.food_selection import select_food_target

        fish_any: Any = fish
        fish_any.genome = self._genome

        env_any: Any = fish.environment
        if not hasattr(env_any, "get_detection_modifier"):
            env_any.get_detection_modifier = lambda: 1.0

        food = select_food_target(cast("Fish", fish_any))
        if food is None:
            return self._wander.velocity(fish, active_food)

        from core.behavior.targeting import TargetObservation

        offset = food.pos - fish.pos
        target_obs = TargetObservation(
            target_vector=(float(offset.x), float(offset.y)),
            target_velocity=(0.0, 0.0),
            target_exists=True,
            threat_vector=(0.0, 0.0),
            self_velocity=(float(fish_any.vel.x), float(fish_any.vel.y)),
            self_speed=float(fish_any.speed),
            energy_ratio=float(fish_any.get_energy_ratio()),
        )

        output = self._module.compile_cached().evaluate(target_obs.to_values())
        if isinstance(output, tuple) and len(output) == 2:
            return Vector2(float(output[0]), float(output[1]))
        return self._wander.velocity(fish, active_food)


class _FullProductionPolicy:
    """Evaluates the full production movement controller with arbiter considerations."""

    def __init__(
        self, genome: Any, seed: int, simulation_config: Any, genome_code_pool: Any
    ) -> None:
        self._strategy = AlgorithmicMovement()
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        self._simulation_config = simulation_config
        self._genome_code_pool = genome_code_pool

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        import math

        fish_any: Any = fish

        # Dynamically attach attributes to the gym fish
        if not hasattr(fish_any, "vel"):
            fish_any.vel = Vector2(0.0, 0.0)
        if not hasattr(fish_any, "age"):
            fish_any.age = 0
        if not hasattr(fish_any, "fish_id"):
            fish_any.fish_id = 1
        if not hasattr(fish_any, "poker_cooldown"):
            fish_any.poker_cooldown = 0
        if not hasattr(fish_any, "can_play_poker"):
            fish_any.can_play_poker = False
        if not hasattr(fish_any, "is_dead"):
            fish_any.is_dead = lambda: False
        if not hasattr(fish_any, "movement_policy"):
            fish_any.movement_policy = None

        # Dynamically attach attributes to the gym environment
        env_any: Any = fish.environment
        if not hasattr(env_any, "simulation_config"):
            env_any.simulation_config = self._simulation_config
        if not hasattr(env_any, "genome_code_pool"):
            env_any.genome_code_pool = self._genome_code_pool
        if not hasattr(env_any, "nearby_evolving_agents"):
            env_any.nearby_evolving_agents = lambda *args, **kwargs: []
        if not hasattr(env_any, "get_detection_modifier"):
            env_any.get_detection_modifier = lambda: 1.0

        fish_any.age += 1
        fish_any.genome = self._genome

        # Run arbiter considerations
        from core.movement_strategy import (
            ALGORITHMIC_MOVEMENT_SMOOTHING,
            ALGORITHMIC_MAX_SPEED_MULTIPLIER,
        )

        ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ = (
            ALGORITHMIC_MAX_SPEED_MULTIPLIER * ALGORITHMIC_MAX_SPEED_MULTIPLIER
        )

        arbitration = self._strategy._arbiter.arbitrate(self._strategy, cast("Fish", fish_any))
        selected = arbitration.selected
        desired = selected.velocity if selected is not None else None

        if desired is None:
            return self._wander.velocity(fish, active_food)

        desired_vx = max(-5.0, min(5.0, float(desired[0])))
        desired_vy = max(-5.0, min(5.0, float(desired[1])))

        speed = fish_any.speed
        target_vx = desired_vx * speed
        target_vy = desired_vy * speed

        # Interpolate velocity
        vel = fish_any.vel
        vel.x += (target_vx - vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        vel.y += (target_vy - vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        vel_x = vel.x
        vel_y = vel.y
        vel_length_sq = vel_x * vel_x + vel_y * vel_y

        if vel_length_sq < 0.01:
            rng = env_any.rng
            angle = rng.random() * 6.283185307
            nudge_speed = speed * 0.3
            vel.x = nudge_speed * math.cos(angle)
            vel.y = nudge_speed * math.sin(angle)
            vel_length_sq = vel.x * vel.x + vel.y * vel.y

        if vel_length_sq > 0:
            max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ
            if vel_length_sq > max_speed_sq:
                max_speed = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER
                scale = max_speed / math.sqrt(vel_length_sq)
                vel.x = vel_x * scale
                vel.y = vel_y * scale

        return Vector2(float(vel.x), float(vel.y))


_FORAGING_GYM_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}


def setup_router(
    champions_dir: Path | None = None,
    world_manager: Any | None = None,
    evaluation_service: SkillEvaluationService | None = None,
) -> APIRouter:
    """Create the skill-ladder standings router."""
    router = APIRouter(prefix="/api/skill", tags=["skill"])
    resolved_dir = champions_dir or _CHAMPIONS_DIR
    if evaluation_service is None:
        evaluation_service = SkillEvaluationService(world_manager)

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
    def get_foraging_gym_summary(
        world_id: str | None = Query(default=None),
    ) -> JSONResponse:
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

    def build_observatory_snapshot(resolved_world_id: str) -> WorldSkillSnapshot | dict[str, Any]:
        """Capture one immutable, worker-safe snapshot of a world's observatory state.

        Runs synchronously on the caller's thread (never inside the background
        worker) so every live read - fish, species records, world config, the
        genome code pool - happens at one consistent instant. A living fish's
        ``taxon_id`` can be reassigned by the taxonomy system on any tick, and
        species records are added/renamed/removed continuously, so passing a
        world_id string alone into a worker (and re-resolving these live) risks
        mixing state from different points in time across a multi-seed
        evaluation.
        """
        import copy
        from core.entities.fish import Fish

        if world_manager is None:
            return {"status": "no_data", "message": "World manager not available"}

        worlds = world_manager.list_worlds()
        if not worlds:
            return {"status": "no_data", "message": "No active worlds available"}

        instance = world_manager.get_world(resolved_world_id)
        if instance is None:
            return {"status": "no_data", "message": f"World {resolved_world_id} not found"}

        runner = instance.runner
        if not hasattr(runner, "world") or not runner.world:
            return {"status": "no_data", "message": "World not initialized"}

        living_fish = [e for e in runner.world.entities_list if isinstance(e, Fish)]
        if not living_fish:
            return {"status": "no_data", "message": "No living fish in the tank"}

        taxonomy = getattr(runner.world, "ecosystem", None) and getattr(
            runner.world.ecosystem, "taxonomy", None
        )
        if not taxonomy or not hasattr(taxonomy, "registry"):
            return {"status": "no_data", "message": "Taxonomy system not available"}

        species_registry = taxonomy.registry
        species_by_taxon_id: dict[str, SpeciesSkillSnapshot] = {}
        for taxon_id in {fish.taxon_id for fish in living_fish}:
            rec = species_registry.species.get(taxon_id)
            if rec is None or not rec.living_member_ids:
                continue
            legacy_val = rec.type_profile.traits.get("prediction_skill")
            species_by_taxon_id[taxon_id] = SpeciesSkillSnapshot(
                taxon_id=taxon_id,
                common_name=rec.common_name,
                legacy_prediction_skill=(
                    float(legacy_val) if isinstance(legacy_val, (int, float)) else None
                ),
            )
        if not species_by_taxon_id:
            return {"status": "no_data", "message": "No active species classification found"}

        fish_snapshots = tuple(
            FishSkillSnapshot(
                fish_id=fish.fish_id,
                taxon_id=fish.taxon_id,
                common_name=getattr(fish, "common_name", "") or "",
                generation=int(getattr(fish, "generation", 0)),
                parent_id=getattr(fish, "parent_id", None),
                genome=copy.deepcopy(fish.genome),
                parent_pursuit_params=copy.deepcopy(getattr(fish, "parent_pursuit_params", None)),
            )
            for fish in living_fish
        )

        simulation_config = getattr(runner.world, "simulation_config", None)
        frame = int(getattr(runner.world, "frame_count", getattr(runner, "frame_count", 0)))

        return WorldSkillSnapshot(
            world_id=resolved_world_id,
            frame=frame,
            living_fish=fish_snapshots,
            species_by_taxon_id=species_by_taxon_id,
            simulation_config=(
                copy.deepcopy(simulation_config) if simulation_config is not None else None
            ),
            # Created once at world startup and never mutated during a running
            # simulation (see core/code_pool/genome_code_pool.py); deep-copying
            # it would only clone the outer dict; every contained Callable
            # stays the same object regardless, so a reference is equally safe.
            genome_code_pool=getattr(runner.world, "genome_code_pool", None),
        )

    def evaluate_observatory_snapshot(snapshot: WorldSkillSnapshot) -> dict[str, Any]:
        """Score one immutable world snapshot.

        Runs on a background worker thread (via ``asyncio.to_thread``) - must
        never touch live simulation state, only the ``snapshot`` it was given.
        """
        from core.behavior.pursuit_nodes import pursuit_module_parameters

        living_fish = snapshot.living_fish
        species_by_taxon_id = snapshot.species_by_taxon_id

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

        # Each living_fish entry's genome is already an isolated deep copy (see
        # build_observatory_snapshot), so no further copying is needed here.
        fish_evals = []
        for fish in living_fish:
            eval_res = evaluate_genome_with_cache(
                fish.genome,
                config_hash,
                _FORAGING_GYM_SUMMARY_SEEDS,
                snapshot.simulation_config,
                snapshot.genome_code_pool,
            )
            fish_evals.append(
                {
                    "fish": fish,
                    "score": eval_res["score"],
                    "average_food": eval_res["average_food"],
                    "uncertainty": eval_res["uncertainty"],
                    "sample_size": eval_res["sample_size"],
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

        best_species_snapshot = species_by_taxon_id.get(best_taxon_id)
        best_species_name = (
            best_species_snapshot.common_name if best_species_snapshot else "Unknown Species"
        )

        # Find best individual
        best_item = max(fish_evals, key=lambda item: item["score"])
        best_fish = best_item["fish"]
        best_score = best_item["score"]

        # Legacy prediction_skill: the individual's own current value, and the
        # species founder/type-profile value used as a fallback baseline when
        # there is no living parent to compare against.
        legacy_prediction_skill = legacy_prediction_skill_of(best_fish.genome)
        if legacy_prediction_skill is None:
            legacy_prediction_skill = 0.5

        best_ind_species_snapshot = species_by_taxon_id.get(best_fish.taxon_id)
        species_founder_legacy_prediction_skill = (
            best_ind_species_snapshot.legacy_prediction_skill
            if best_ind_species_snapshot is not None
            and best_ind_species_snapshot.legacy_prediction_skill is not None
            else 0.5
        )

        # Species median legacy prediction skill
        species_fish = [f for f in living_fish if f.taxon_id == best_fish.taxon_id]
        species_values = [
            v for v in (legacy_prediction_skill_of(f.genome) for f in species_fish) if v is not None
        ]
        if species_values:
            sorted_vals = sorted(species_values)
            n_vals = len(sorted_vals)
            if n_vals % 2 == 1:
                species_median = sorted_vals[n_vals // 2]
            else:
                species_median = (sorted_vals[n_vals // 2 - 1] + sorted_vals[n_vals // 2]) / 2.0
        else:
            species_median = 0.5

        # Parent comparisons: four honestly-separate fields rather than one
        # field that silently mixes two different parameters. The living
        # parent's legacy trait and the parent-at-birth pursuit-module
        # snapshot measure genuinely different things and must never be
        # compared as if they were the same value.
        parent_legacy_prediction_skill = None
        parent_id = best_fish.parent_id
        if parent_id is not None:
            parent_fish = next((f for f in living_fish if f.fish_id == parent_id), None)
            if parent_fish is not None:
                parent_legacy_prediction_skill = legacy_prediction_skill_of(parent_fish.genome)

        pursuit_prediction_strength = None
        behavioral = getattr(best_fish.genome, "behavioral", None)
        pursuit_module_trait = (
            getattr(behavioral, "target_pursuit_module", None) if behavioral is not None else None
        )
        pursuit_module = pursuit_module_trait.value if pursuit_module_trait is not None else None
        if pursuit_module is not None:
            pursuit_prediction_strength = pursuit_module_parameters(pursuit_module).get(
                "prediction_strength"
            )

        parent_pursuit_prediction_strength = None
        if isinstance(best_fish.parent_pursuit_params, dict):
            parent_pursuit_prediction_strength = best_fish.parent_pursuit_params.get(
                "prediction_strength"
            )

        # Percentage/Fraction of its species population sharing the same module fingerprint
        species_fish_items = [
            item for item in fish_evals if item["fish"].taxon_id == best_fish.taxon_id
        ]
        best_module_fp = module_fingerprint(best_fish.genome)
        same_module_count = sum(
            1
            for item in species_fish_items
            if module_fingerprint(item["fish"].genome) == best_module_fp
        )
        percentage = (
            (same_module_count / len(species_fish_items)) * 100.0 if species_fish_items else 100.0
        )
        similar_fraction = (
            same_module_count / len(species_fish_items) if species_fish_items else 1.0
        )

        # Get default/baseline controller scores from summary cache block
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

        generation = max(fish.generation for fish in living_fish)
        return {
            "status": "success",
            "world_id": snapshot.world_id,
            "evaluated_at_frame": snapshot.frame,
            "evaluated_at_generation": generation,
            "benchmark_hash": config_hash,
            "subject": "Full production movement controller",
            "tank_average": tank_average,
            "best_species": {
                "name": best_species_name,
                "score": best_species_score,
            },
            "best_individual": {
                "id": best_fish.fish_id,
                "name": (
                    f"{best_fish.common_name} #{best_fish.fish_id}"
                    if best_fish.common_name
                    else f"Fish #{best_fish.fish_id}"
                ),
                "score": best_score,
                "food_collected": best_item["average_food"],
                "food_available": 12.0,
                "legacy_prediction_skill": legacy_prediction_skill,
                "species_founder_legacy_prediction_skill": species_founder_legacy_prediction_skill,
                "parent_legacy_prediction_skill": parent_legacy_prediction_skill,
                "pursuit_prediction_strength": pursuit_prediction_strength,
                "parent_pursuit_prediction_strength": parent_pursuit_prediction_strength,
                "percentage_of_species": percentage,
                "species_median": species_median,
                "module_fingerprint": best_module_fp,
                "similar_fraction": similar_fraction,
                "score_uncertainty": best_item["uncertainty"],
                "sample_size": best_item["sample_size"],
            },
            "engine_baseline": baseline_mean,
            "wandering_mean": wandering_mean,
            "perfect_mean": perfect_mean,
        }

    evaluation_service.set_snapshot_builder(build_observatory_snapshot)
    evaluation_service.set_evaluator(evaluate_observatory_snapshot)

    @router.get("/foraging-gym/observatory")
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

    return router
