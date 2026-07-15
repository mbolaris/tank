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
from core.behavior.target_memory_transfer_gym import MUTATION_RATE, MUTATION_STRENGTH

BENCHMARK_ID = "tank/target_memory_transfer"
EXPECTED_RUNTIME_SECONDS = 15

CONFIG: dict[str, Any] = {
    "module": "target_memory_v1",
    "study_version": "v1",
    "training": "population_evolution_moving_food_v1",
    "comparison_groups": "naive-greedy,default,random,food-trained,ball-trained",
}


def run(seed: int) -> dict[str, Any]:
    """Measure food-to-ball target-memory transfer and adaptation for one seed."""
    started = time.perf_counter()
    evaluation = evaluate_target_memory_transfer(seed)

    naive_greedy_score = evaluation.naive_greedy_score
    default_score = evaluation.default_score
    food_trained_score = evaluation.food_trained_score
    ball_trained_score = evaluation.ball_trained_score
    random_score = evaluation.group_summaries["random_search"].overall_score

    # Primary falsifiable claim (the board's "disjoint control"): does the
    # shared encoding's food-adapted params beat a founder-default baseline
    # that food selection never touched, on zero-shot ball commitment?
    transfer_benefit_vs_disjoint = food_trained_score - default_score
    transfer_benefit_vs_random = food_trained_score - random_score

    adaptation_accel = (
        evaluation.adaptation_generations_default - evaluation.adaptation_generations_food
    )

    runtime = time.perf_counter() - started

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": transfer_benefit_vs_disjoint,
        "score_breakdown": {
            "naive_greedy_fitness": naive_greedy_score,
            "default_params_fitness": default_score,
            "random_search_fitness": random_score,
            "food_trained_fitness": food_trained_score,
            "ball_trained_fitness": ball_trained_score,
            "transfer_benefit_vs_disjoint": transfer_benefit_vs_disjoint,
            "transfer_benefit_vs_random": transfer_benefit_vs_random,
        },
        "runtime_seconds": runtime,
        "metadata": {
            "transfer_benefit_vs_disjoint": transfer_benefit_vs_disjoint,
            "transfer_benefit_vs_random": transfer_benefit_vs_random,
            "scenario_sets": {
                "train": "train_v1",
                "validation": "validation_v1",
                "held_out": "held_out_v1",
                "ball_train": "ball_train_v1",
                "ball_validation": "ball_validation_v1",
            },
            "groups": {
                name: summary.to_dict() for name, summary in evaluation.group_summaries.items()
            },
            "adaptation": {
                "gens_food_trained": evaluation.adaptation_generations_food,
                "gens_disjoint_default_start": evaluation.adaptation_generations_default,
                "acceleration_generations": adaptation_accel,
                "threshold": evaluation.adaptation_threshold,
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
