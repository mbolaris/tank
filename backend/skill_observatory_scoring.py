"""Memoized scoring primitives for the Skill Observatory.

Two independent caches live here, both keyed by a config hash so a changed
benchmark config invalidates stale entries rather than silently reusing them:
a bounded LRU of per-genome multi-seed scores (``evaluate_genome_with_cache``),
and an unbounded memo of the engine's own default-controller baseline
(``compute_foraging_gym_summary``).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from typing import Any

from backend.skill_observatory_policies import evaluate_custom_genome


def controller_fingerprint(genome: Any) -> str:
    """Stable identity hash for a genome's movement-controller-relevant genes.

    Two genomes that differ only in unrelated physical traits must fingerprint
    identically, so the Observatory doesn't create a separate cache entry (and
    a separate multi-seed evaluation) for phenotypically identical controllers.
    """
    from unittest.mock import Mock

    from core.genetics.genome import GENOME_SCHEMA_VERSION
    from core.genetics.genome_codec import genome_to_dict

    if isinstance(genome, Mock):
        return "mock_controller"
    payload = genome_to_dict(genome, schema_version=GENOME_SCHEMA_VERSION)
    controller_fields = (
        "aggression",
        "pursuit_aggression",
        "prediction_skill",
        "hunting_stamina",
        "behavior",
        "behavior_graph",
        "target_pursuit_module",
        "movement_policy_id",
        "movement_policy_params",
    )
    controller_payload = {key: payload.get(key) for key in controller_fields}
    encoded = json.dumps(controller_payload, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def module_fingerprint(genome: Any) -> str:
    """Stable identity hash for a genome's target-pursuit behavior module."""
    from unittest.mock import Mock

    if isinstance(genome, Mock):
        return "mock_module"

    module_trait = getattr(genome.behavioral, "target_pursuit_module", None)
    module = module_trait.value if module_trait is not None else None
    if module is not None:
        payload = module.to_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
        return "graph_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:8]

    behavior_trait = getattr(genome.behavioral, "behavior", None)
    behavior = behavior_trait.value if behavior_trait is not None else None
    if behavior is not None:
        payload = {
            "threat_response": behavior.threat_response.name,
            "food_approach": behavior.food_approach.name,
            "social_mode": behavior.social_mode.name,
            "poker_engagement": behavior.poker_engagement.name,
            "parameters": behavior.parameters,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
        return "comp_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:8]

    return "default"


def legacy_prediction_skill_of(genome: Any) -> float | None:
    """Best-effort float extraction of a genome's legacy prediction_skill trait."""
    from unittest.mock import Mock

    behavioral = getattr(genome, "behavioral", None)
    trait = getattr(behavioral, "prediction_skill", None) if behavioral is not None else None
    if trait is None:
        return None
    val = getattr(trait, "value", None)
    if val is None or isinstance(val, Mock):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


_MAX_OBSERVATORY_CACHE_ENTRIES = 256
_OBSERVATORY_EVALUATION_CACHE: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()


def evaluate_genome_with_cache(
    genome: Any,
    config_hash: str,
    seeds: tuple[int, ...],
    simulation_config: Any,
    genome_code_pool: Any,
) -> dict[str, Any]:
    """Score one genome across ``seeds``, cached by (controller fingerprint, config_hash)."""
    cache_key = (controller_fingerprint(genome), config_hash)
    if cache_key in _OBSERVATORY_EVALUATION_CACHE:
        _OBSERVATORY_EVALUATION_CACHE.move_to_end(cache_key)
        return _OBSERVATORY_EVALUATION_CACHE[cache_key]

    scores = []
    food_collected_list = []
    for seed in seeds:
        res = evaluate_custom_genome(
            genome,
            seed,
            subject="full_production",
            simulation_config=simulation_config,
            genome_code_pool=genome_code_pool,
        )
        scores.append(res.composable_ratio)
        food_collected_list.append(res.composable.food_collected)

    n_trials = len(scores)
    mean_score = sum(scores) / n_trials
    if n_trials > 1:
        variance = sum((x - mean_score) ** 2 for x in scores) / (n_trials - 1)
        sem = math.sqrt(variance) / math.sqrt(n_trials)
    else:
        sem = 0.0

    result = {
        "score": mean_score,
        "average_food": sum(food_collected_list) / len(food_collected_list),
        "uncertainty": sem,
        "sample_size": n_trials,
    }
    _OBSERVATORY_EVALUATION_CACHE[cache_key] = result
    _OBSERVATORY_EVALUATION_CACHE.move_to_end(cache_key)
    while len(_OBSERVATORY_EVALUATION_CACHE) > _MAX_OBSERVATORY_CACHE_ENTRIES:
        _OBSERVATORY_EVALUATION_CACHE.popitem(last=False)
    return result


# The versioned seed cohort every foraging-gym summary/observatory result is
# measured against; changing it changes what "the baseline" means, so it's
# folded into the config hash below rather than a free-floating constant.
FORAGING_GYM_SUMMARY_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)

_FORAGING_GYM_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}


def compute_foraging_gym_summary() -> dict[str, Any]:
    """Aggregate the engine's default foraging-gym baseline across the fixed
    seed cohort, cached by config hash.

    Both the ``/foraging-gym/summary`` endpoint and ``evaluate_observatory_snapshot``
    (which compares a tank's best forager against this same baseline) call
    this, so the 8-seed run only ever happens once per config.
    """
    from benchmarks.tank.foraging_gym import BENCHMARK_ID as FORAGING_GYM_ID
    from benchmarks.tank.foraging_gym import CONFIG as FORAGING_GYM_CONFIG
    from benchmarks.tank.foraging_gym import run as run_gym
    from core.solutions.config_hash import compute_config_hash

    summary_config = {
        **FORAGING_GYM_CONFIG,
        "summary_seeds": FORAGING_GYM_SUMMARY_SEEDS,
    }
    config_hash = compute_config_hash(
        benchmark_id=FORAGING_GYM_ID,
        seed=0,
        benchmark_config=summary_config,
    )
    if config_hash in _FORAGING_GYM_SUMMARY_CACHE:
        return _FORAGING_GYM_SUMMARY_CACHE[config_hash]

    per_seed_results = {}
    scores = []
    wandering_scores = []
    food_collected_list = []
    energy_collected_list = []
    for s in FORAGING_GYM_SUMMARY_SEEDS:
        res = run_gym(s)
        per_seed_results[str(s)] = res
        scores.append(res["score"])
        wandering_scores.append(res["score_breakdown"]["random_walk_energy_ratio"])
        composable_meta = res["metadata"]["composable"]
        food_collected_list.append(composable_meta["food_collected"])
        energy_collected_list.append(composable_meta["energy_collected"])

    n = len(scores)
    mean_score = sum(scores) / n
    wandering_mean = sum(wandering_scores) / n
    perfect_mean = 1.0  # Oracle is always 1.0

    # 95% confidence interval using the t-distribution for n=8 (df=7, t=2.365)
    if n > 1:
        variance = sum((x - mean_score) ** 2 for x in scores) / (n - 1)
        std_err = math.sqrt(variance) / math.sqrt(n)
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
            "seeds": list(FORAGING_GYM_SUMMARY_SEEDS),
            "per_seed": per_seed_results,
        },
    }
    _FORAGING_GYM_SUMMARY_CACHE[config_hash] = summary
    return summary
