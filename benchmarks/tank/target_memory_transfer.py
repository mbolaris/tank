"""Zero-shot target-memory transfer benchmark: food-to-ball target commitment.

Evaluates whether target_memory (core/behavior/target_memory.py), evolved
under food-only selection, transfers zero-shot to ball-domain target
commitment versus a disjoint/founder-default baseline that food selection
never touched - the substrate Board's frozen transfer assay
(see docs/EVOLVABILITY.md S3.1/S3.5).
"""

from __future__ import annotations

import time
from typing import Any

from core.behavior.target_memory_transfer_evolution import evaluate_target_memory_transfer
from core.behavior.target_memory_transfer_gym import (
    MIN_REFERENCE_EFFECT,
    MUTATION_RATE,
    MUTATION_STRENGTH,
)
from core.behavior.target_memory_transfer_scenarios import SCENARIO_SET_VERSION

BENCHMARK_ID = "tank/target_memory_transfer"
# Raised from 15: fixing the adaptation-phase held-out leakage (see
# TargetMemoryTransferEvaluation.adaptation_reference_established) means
# established-reference seeds now run real generations to reach their bar
# instead of terminating near-instantly against a manufactured threshold.
EXPECTED_RUNTIME_SECONDS = 25

CONFIG: dict[str, Any] = {
    "module": "target_memory_v1",
    # v1.2: food scenario sets gained moving/occluded families matched to the
    # ball families' latent capabilities (so food selection now exercises
    # motion_extrapolation_duration), the random-search control was replaced
    # by a structurally matched shuffled-fitness control, and per-episode
    # diagnostic metrics (switches, stale pursuit, reacquisition, distance)
    # were added to every group summary. v1.1 moved adaptation measurement
    # onto the ball-validation set; v1 measured it on the training set.
    "study_version": "v1.2",
    "training": "population_evolution_moving_food_v2",
    "comparison_groups": "naive-greedy,default,neutral-evolution,food-trained,ball-trained",
}


def _set_names() -> dict[str, str]:
    v = SCENARIO_SET_VERSION
    return {
        "train": f"train_{v}",
        "validation": f"validation_{v}",
        "held_out": f"held_out_{v}",
        "ball_train": f"ball_train_{v}",
        "ball_validation": f"ball_validation_{v}",
    }


def run(seed: int) -> dict[str, Any]:
    """Measure food-to-ball target-memory transfer and adaptation for one seed."""
    started = time.perf_counter()
    evaluation = evaluate_target_memory_transfer(seed)

    naive_greedy_score = evaluation.naive_greedy_score
    default_score = evaluation.default_score
    food_trained_score = evaluation.food_trained_score
    ball_trained_score = evaluation.ball_trained_score
    neutral_score = evaluation.group_summaries["neutral_evolution"].overall_score

    # Primary falsifiable claim (the board's "disjoint control"): does the
    # shared encoding's food-adapted params beat a founder-default baseline
    # that food selection never touched, on zero-shot ball commitment?
    transfer_benefit_vs_disjoint = food_trained_score - default_score
    # Secondary: does food *selection* specifically matter, versus the same
    # lineage machinery with selection decoupled (shuffled fitness)?
    transfer_benefit_vs_neutral = food_trained_score - neutral_score

    adaptation_accel: int | None = None
    if evaluation.adaptation_reference_established:
        assert evaluation.adaptation_generations_default is not None
        assert evaluation.adaptation_generations_food is not None
        adaptation_accel = (
            evaluation.adaptation_generations_default - evaluation.adaptation_generations_food
        )

    runtime = time.perf_counter() - started
    sets = _set_names()

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": transfer_benefit_vs_disjoint,
        "score_breakdown": {
            "naive_greedy_fitness": naive_greedy_score,
            "default_params_fitness": default_score,
            "neutral_evolution_fitness": neutral_score,
            "food_trained_fitness": food_trained_score,
            "ball_trained_fitness": ball_trained_score,
            "transfer_benefit_vs_disjoint": transfer_benefit_vs_disjoint,
            "transfer_benefit_vs_neutral": transfer_benefit_vs_neutral,
        },
        "runtime_seconds": runtime,
        "metadata": {
            "transfer_benefit_vs_disjoint": transfer_benefit_vs_disjoint,
            "transfer_benefit_vs_neutral": transfer_benefit_vs_neutral,
            "scenario_sets": sets,
            "groups": {
                name: summary.to_dict() for name, summary in evaluation.group_summaries.items()
            },
            "adaptation": {
                "reference_established": evaluation.adaptation_reference_established,
                "reference_gap": evaluation.adaptation_reference_gap,
                "gens_food_trained": evaluation.adaptation_generations_food,
                "gens_disjoint_default_start": evaluation.adaptation_generations_default,
                "acceleration_generations": adaptation_accel,
                "threshold": evaluation.adaptation_threshold,
            },
            # Machine-readable statement of what this run's numbers do and do
            # not support, so downstream consumers (validators, dashboards,
            # agents comparing runs) never have to infer validity from prose.
            "validity": {
                "adaptation_reference_established": (evaluation.adaptation_reference_established),
                "adaptation_fields_meaningful": evaluation.adaptation_reference_established,
                "min_reference_effect": MIN_REFERENCE_EFFECT,
                "adaptation_reference_measured_on": sets["ball_validation"],
                "adaptation_training_set": sets["ball_train"],
                "held_out_used_only_for_zero_shot_scoring": True,
                "adaptation_arms_rng": "paired_independent_streams_per_run",
                "neutral_control": (
                    "same evolutionary loop, budget, and operators as the "
                    "trained arms with fitness shuffled before selection; "
                    "final individual is a random draw from the drifted "
                    "population (weaker final-harvest than the trained arms' "
                    "validation pick, by design)"
                ),
                "multi_run_study_tool": "scripts/run_target_memory_transfer_study.py",
                "known_limitations": [
                    "this per-seed benchmark runs a deliberately small "
                    "CI-fast budget (16x15x2); transfer conclusions belong "
                    "to the multi-run study tool's aggregate report",
                    "diagnostic metrics (switches, stale pursuit, "
                    "reacquisition, distance) are observational and never "
                    "feed overall_score",
                ],
            },
            "mutation_schedule": {
                "mutation_rate": MUTATION_RATE,
                "mutation_strength": MUTATION_STRENGTH,
                "note": (
                    "Fixed constant shared by both training arms - the only "
                    "mutation-intensity lever wired for target_memory today; its "
                    "self-adapting per-trait meta-gene is inherited but not yet "
                    "consumed by inherit_behavior_graph (substrate board #8/#9)."
                ),
            },
        },
    }
