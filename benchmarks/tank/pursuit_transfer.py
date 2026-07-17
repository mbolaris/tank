"""Zero-shot pursuit-transfer benchmark for the shared Target Pursuit Module (v2).

Evaluates zero-shot transfer from food foraging to soccer-ball interception using
trajectory sets and evolutionary populations, comparing multiple groups and measuring
adaptation speed.
"""

from __future__ import annotations

import time
from typing import Any

from core.pursuit.transfer_gym import evaluate_pursuit_transfer

BENCHMARK_ID = "tank/pursuit_transfer"
EXPECTED_RUNTIME_SECONDS = 15

CONFIG: dict[str, Any] = {
    "module": "target_pursuit_module_v2",
    "study_version": "v2",
    "training": "population_evolution_moving_food_v2",
    "comparison_groups": "direct,default,random,food-trained,soccer-trained,constant-velocity-solver",
}


def run(seed: int) -> dict[str, Any]:
    """Measure food-to-soccer pursuit transfer and adaptation for one seed."""
    started = time.perf_counter()
    evaluation = evaluate_pursuit_transfer(seed)

    direct_score = evaluation.direct_score
    default_score = evaluation.default_score
    food_trained_score = evaluation.food_trained_score
    soccer_trained_score = evaluation.soccer_trained_score
    constant_velocity_solver_score = evaluation.constant_velocity_solver_score

    # Compute transfer benefit
    random_score = evaluation.group_summaries["random_search"].overall_score
    transfer_benefit = food_trained_score - random_score

    # Calculate adaptation acceleration
    adaptation_accel = (
        evaluation.adaptation_generations_random - evaluation.adaptation_generations_food
    )

    runtime = time.perf_counter() - started

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": transfer_benefit,
        "score_breakdown": {
            "direct_pursuit_fitness": direct_score,
            "default_module_fitness": default_score,
            "food_trained_fitness": food_trained_score,
            "constant_velocity_solver_fitness": constant_velocity_solver_score,
            "random_search_fitness": random_score,
            "soccer_trained_fitness": soccer_trained_score,
            "transfer_benefit": transfer_benefit,
        },
        "runtime_seconds": runtime,
        "metadata": {
            "transfer_benefit": transfer_benefit,
            "scenario_sets": {
                "train": "train_v2",
                "validation": "validation_v2",
                "held_out": "held_out_v2",
            },
            "groups": {
                name: summary.to_dict() for name, summary in evaluation.group_summaries.items()
            },
            "adaptation": {
                "gens_food_trained": evaluation.adaptation_generations_food,
                "gens_random_start": evaluation.adaptation_generations_random,
                "acceleration_generations": adaptation_accel,
                "threshold": evaluation.adaptation_threshold,
            },
        },
    }
