"""Tank Skill Observatory: isolated evaluation snapshots and their evaluation.

Movement policies and raw genome evaluation live in
``backend.skill_observatory_policies``; fingerprinting, the per-genome score
cache, and the foraging-gym baseline live in ``backend.skill_observatory_scoring``.
This module owns the two-phase evaluation boundary itself: capturing a
point-in-time snapshot of live simulation state (``build_observatory_snapshot``,
must run on the caller's own thread) and scoring it (``evaluate_observatory_snapshot``,
safe to run on a background worker thread since it touches only the snapshot).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.skill_observatory_scoring import (
    FORAGING_GYM_SUMMARY_SEEDS,
    compute_foraging_gym_summary,
    evaluate_genome_with_cache,
    legacy_prediction_skill_of,
    module_fingerprint,
)
from core.entities.fish import Fish


@dataclass(frozen=True)
class FishSkillSnapshot:
    """Point-in-time, worker-thread-safe copy of one living fish.

    A living ``Fish``'s ``taxon_id``/``common_name`` can be reassigned by
    ``TaxonomySystem.update()`` on any simulation tick (species promotion
    swaps the record's id), so holding a live ``Fish`` reference across a
    multi-seed background evaluation can silently mix data from two points
    in time. This snapshot is built once, synchronously, before the worker
    thread starts.
    """

    fish_id: int
    taxon_id: str
    common_name: str
    generation: int
    parent_id: int | None
    genome: Any
    parent_pursuit_params: dict[str, float] | None


@dataclass(frozen=True)
class SpeciesSkillSnapshot:
    """Point-in-time copy of one species record's observatory-relevant state."""

    taxon_id: str
    common_name: str
    legacy_prediction_skill: float | None


@dataclass(frozen=True)
class WorldSkillSnapshot:
    """Isolated evaluation snapshot of everything an observatory evaluation needs.

    Built synchronously on the caller's thread under the simulation runner's
    lock from live simulation state, then handed to a worker thread (via
    ``asyncio.to_thread``) that must not touch the live world - the simulation
    keeps mutating fish, species records, and the genome code pool concurrently.
    """

    world_id: str
    frame: int
    living_fish: tuple[FishSkillSnapshot, ...]
    species_by_taxon_id: dict[str, SpeciesSkillSnapshot]
    simulation_config: Any
    genome_code_pool: Any


def build_observatory_snapshot(
    world_manager: Any, resolved_world_id: str
) -> WorldSkillSnapshot | dict[str, Any]:
    """Capture one isolated evaluation snapshot of a world's observatory state.

    Must run synchronously on the caller's thread under the simulation runner's
    lock (never inside the background worker) so every live read - fish,
    species records, world config, the genome code pool - happens at one
    consistent, atomic instant. A living fish's ``taxon_id`` can be reassigned
    by the taxonomy system on any tick, and species records are
    added/renamed/removed continuously, so passing a world_id string alone
    into a worker (and re-resolving these live) risks mixing state from different
    points in time across a multi-seed evaluation.
    """
    import copy

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

    with runner.lock:
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
        simulation_config_copied = (
            copy.deepcopy(simulation_config) if simulation_config is not None else None
        )
        genome_code_pool = getattr(runner.world, "genome_code_pool", None)
        frame = int(getattr(runner.world, "frame_count", getattr(runner, "frame_count", 0)))

    return WorldSkillSnapshot(
        world_id=resolved_world_id,
        frame=frame,
        living_fish=fish_snapshots,
        species_by_taxon_id=species_by_taxon_id,
        simulation_config=simulation_config_copied,
        # Created once at world startup and never mutated during a running
        # simulation (see core/code_pool/genome_code_pool.py); deep-copying
        # it would only clone the outer dict; every contained Callable stays
        # the same object regardless, so a reference is equally safe.
        genome_code_pool=genome_code_pool,
    )


def evaluate_observatory_snapshot(snapshot: WorldSkillSnapshot) -> dict[str, Any]:
    """Score one isolated evaluation snapshot against the production controller.

    Runs on a background worker thread (via ``asyncio.to_thread``) - must
    never touch live simulation state, only the ``snapshot`` it was given.
    """
    from core.behavior.pursuit_nodes import pursuit_module_parameters

    living_fish = snapshot.living_fish
    species_by_taxon_id = snapshot.species_by_taxon_id

    baseline = compute_foraging_gym_summary()
    config_hash = baseline["config_hash"]

    # Each living_fish entry's genome is already an isolated deep copy (see
    # build_observatory_snapshot), so no further copying is needed here.
    fish_evals = []
    for fish in living_fish:
        eval_res = evaluate_genome_with_cache(
            fish.genome,
            config_hash,
            FORAGING_GYM_SUMMARY_SEEDS,
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

    # Parent comparisons: four honestly-separate fields rather than one field
    # that silently mixes two different parameters. The living parent's
    # legacy trait and the parent-at-birth pursuit-module snapshot measure
    # genuinely different things and must never be compared as if they were
    # the same value.
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
    similar_fraction = same_module_count / len(species_fish_items) if species_fish_items else 1.0

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
        "engine_baseline": baseline["mean"],
        "wandering_mean": baseline["wandering_mean"],
        "perfect_mean": baseline["perfect_mean"],
    }
