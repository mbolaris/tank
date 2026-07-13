"""Frozen-ruler foraging benchmark with an attainable oracle ceiling.

This benchmark isolates food seeking from ecosystem confounders.  A single
neutral-default composable fish pursues a deterministic, seeded food script;
there is no reproduction, poker, ball, predator, or population feedback.  The
score is gross food energy collected divided by the full-information oracle's
attainable energy total, so it is always in the closed interval [0, 1].
"""

from __future__ import annotations

import time
from typing import Any

from core.foraging.gym import evaluate_foraging_gym
from core.skill import RungResult, SkillLadderSummary, interpolated_index

BENCHMARK_ID = "tank/foraging_gym"
EXPECTED_RUNTIME_SECONDS = 2

CONFIG: dict[str, Any] = {
    "policy": "composable_neutral_default",
    "schedule": "frozen_lcg_lane_v1",
    "floor": "random_walk_v1",
    "ceiling": "full_information_greedy_v1",
}

# The standardized trial seeds used to generate the summary aggregate result.
# Changing this tuple updates the versioned cohort and invalidates the cache.
SUMMARY_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)


def run(seed: int) -> dict[str, Any]:
    """Measure neutral composable food-seeking skill for one fixed seed."""
    started = time.perf_counter()
    evaluation = evaluate_foraging_gym(seed)
    oracle_energy = evaluation.oracle_energy
    composable = evaluation.composable
    random_walk = evaluation.random_walk
    oracle = evaluation.oracle

    oracle_ratio = oracle.energy_collected / oracle_energy if oracle_energy else 0.0
    composable_ratio = evaluation.composable_ratio
    random_ratio = evaluation.random_walk_ratio

    rungs = (
        RungResult(
            rung="L0",
            rung_id="random_walk_v1",
            metric=random_ratio,
            beaten=composable_ratio > random_ratio,
            detail=random_walk.to_dict(),
        ),
        RungResult(
            rung="L1",
            rung_id="full_information_greedy_v1",
            metric=oracle_ratio,
            beaten=composable_ratio >= oracle_ratio,
            detail=oracle.to_dict(),
        ),
    )
    skill = SkillLadderSummary(
        domain="foraging",
        benchmark_id=BENCHMARK_ID,
        metric_name="energy_collected_over_oracle",
        skill_index=interpolated_index(composable_ratio, random_ratio, oracle_ratio),
        rungs=rungs,
        notes=(
            "The oracle collects every scripted food item under the same speed, "
            "bounds, and capture rules, making gross scheduled energy an attainable "
            "ceiling. The random-walk floor ignores food."
        ),
    )
    runtime = time.perf_counter() - started

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": composable_ratio,
        "score_breakdown": {
            "composable_energy_ratio": composable_ratio,
            "random_walk_energy_ratio": random_ratio,
            "oracle_energy_ratio": oracle_ratio,
        },
        "runtime_seconds": runtime,
        "metadata": {
            "score_mode": "gross food energy collected / attainable oracle energy",
            "oracle_energy": oracle_energy,
            "composable": composable.to_dict(),
            "random_walk": random_walk.to_dict(),
            "oracle": oracle.to_dict(),
            "skill": skill.to_dict(),
        },
    }
