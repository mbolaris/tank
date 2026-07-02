"""Frozen selection-response assay for Tank World evolvability.

This benchmark measures whether a population shows directional heritable trait
response while retaining enough diversity to keep evolving. It intentionally
complements ``ecosystem_health_10k``: that benchmark rewards generation speed,
while this assay decomposes selection response per generation so fast churn with
flat or collapsing traits is visible.

The multi-seed held-out surface is ``tools/run_selection_response_assay.py``.
This module remains a normal single-seed benchmark so it works with
``tools/run_bench.py`` and the existing config-hash/determinism machinery.
"""

from __future__ import annotations

import math
import sys
import time
from collections.abc import Callable
from typing import Any

from core.entities import Fish
from core.services.stats.trait_trends import EVOLUTION_TRAIT_KEYS, compute_trait_means
from core.worlds import WorldRegistry

BENCHMARK_ID = "tank/selection_response_10k"
FRAMES = 10000
SAMPLE_INTERVAL = 1000
FROZEN_SEEDS = (42, 7, 123)
TRAIT_DRIFT_SELECTION_PCT = 5.0

WORLD_CONFIG: dict[str, Any] = {
    "headless": True,
    "screen_width": 2000,
    "screen_height": 2000,
    "max_population": 60,
    "critical_population_threshold": 5,
    "emergency_spawn_cooldown": 90,
    "poker_activity_enabled": False,
    "plants_enabled": False,
    "auto_food_spawn_rate": 9,
    "soccer_enabled": False,
    "panic_button_enabled": True,
}

CONFIG: dict[str, Any] = {
    "frames": FRAMES,
    "sample_interval": SAMPLE_INTERVAL,
    "trait_drift_selection_pct": TRAIT_DRIFT_SELECTION_PCT,
    "frozen_seeds": FROZEN_SEEDS,
    "world_config": WORLD_CONFIG,
}


def run(
    seed: int, fingerprint_callback: Callable[[Any, int], None] | None = None
) -> dict[str, Any]:
    """Run the frozen selection-response benchmark for one seed."""
    start_time = time.time()
    samples = collect_samples(seed=seed, frames=FRAMES, interval=SAMPLE_INTERVAL)
    runtime = time.time() - start_time
    result = score_samples(samples, seed=seed, runtime_seconds=runtime)
    if fingerprint_callback is not None:
        # This benchmark collects internal samples rather than exposing every
        # frame. Re-run through the canonical world loop when fingerprints are
        # requested so the caller still gets comparable replay artifacts.
        _run_fingerprint_pass(seed, fingerprint_callback)
    return result


def collect_samples(seed: int, frames: int, interval: int) -> list[dict[str, Any]]:
    """Run a deterministic headless tank world and sample evolvability signals."""
    config = dict(WORLD_CONFIG)
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    samples: list[dict[str, Any]] = []
    for frame in range(1, frames + 1):
        world.step()
        if frame % interval == 0:
            samples.append(_sample_world(world, frame))
        if frame % 2000 == 0:
            print(f"  Frame {frame}/{frames}...", file=sys.stderr)
    return samples


def score_samples(
    samples: list[dict[str, Any]], *, seed: int, runtime_seconds: float = 0.0
) -> dict[str, Any]:
    """Score pre-collected samples and return the benchmark result dict."""
    if len(samples) < 2:
        return {
            "benchmark_id": BENCHMARK_ID,
            "seed": seed,
            "score": 0.0,
            "runtime_seconds": runtime_seconds,
            "metadata": {
                "frames": FRAMES,
                "sample_interval": SAMPLE_INTERVAL,
                "samples": len(samples),
                "reason": "insufficient_samples",
            },
        }

    first = samples[0]
    last = samples[-1]
    frames_covered = max(1, int(last["frame"]) - int(first["frame"]))
    generations_advanced = max(0, int(last["max_generation"]) - int(first["max_generation"]))
    generation_rate = generations_advanced / (frames_covered / 10000.0)

    drift = _trait_drift(first.get("traits", {}), last.get("traits", {}))
    selected = [item for item in drift.values() if item["selection"]]
    mean_selected_abs_drift = (
        sum(abs(item["pct"]) for item in selected) / len(selected) if selected else 0.0
    )
    selected_fraction = len(selected) / max(len(EVOLUTION_TRAIT_KEYS), 1)
    drift_per_generation = mean_selected_abs_drift / max(generations_advanced, 1)

    diversity_first = float(first.get("diversity_score", 0.0) or 0.0)
    diversity_last = float(last.get("diversity_score", 0.0) or 0.0)
    diversity_retention = (
        min(1.5, diversity_last / diversity_first) if diversity_first > 0 else 0.0
    )
    diversity_floor = min(1.0, diversity_last / 0.30) if diversity_last > 0 else 0.0
    diversity_component = math.sqrt(max(0.0, diversity_retention) * max(0.0, diversity_floor))

    population_values = [float(s.get("population", 0.0) or 0.0) for s in samples]
    population_component = _stability_component(population_values)
    quality_per_generation = population_component * min(1.0, generation_rate / 5.0)

    selection_component = min(2.0, drift_per_generation / TRAIT_DRIFT_SELECTION_PCT)
    score = (
        100.0
        * selection_component
        * selected_fraction
        * diversity_component
        * quality_per_generation
    )

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime_seconds,
        "metadata": {
            "frames": FRAMES,
            "sample_interval": SAMPLE_INTERVAL,
            "samples": len(samples),
            "frame_first": first["frame"],
            "frame_last": last["frame"],
            "frames_covered": frames_covered,
            "generation_first": first["max_generation"],
            "generation_last": last["max_generation"],
            "generations_advanced": generations_advanced,
            "generation_rate_per_10k": round(generation_rate, 4),
            "selection_detected": bool(selected),
            "selected_trait_count": len(selected),
            "selected_trait_fraction": round(selected_fraction, 4),
            "mean_selected_abs_drift_pct": round(mean_selected_abs_drift, 4),
            "drift_per_generation_pct": round(drift_per_generation, 4),
            "diversity_first": round(diversity_first, 4),
            "diversity_last": round(diversity_last, 4),
            "diversity_delta": round(diversity_last - diversity_first, 4),
            "diversity_retention": round(diversity_retention, 4),
            "population_mean": round(sum(population_values) / len(population_values), 2),
            "population_cv": round(_coefficient_of_variation(population_values), 4),
            "population_component": round(population_component, 4),
            "selection_component": round(selection_component, 4),
            "diversity_component": round(diversity_component, 4),
            "quality_per_generation": round(quality_per_generation, 4),
            "trait_drift": drift,
            "score_formula": (
                "100 * selection_component * selected_trait_fraction * "
                "diversity_component * quality_per_generation"
            ),
        },
    }


def _sample_world(world: Any, frame: int) -> dict[str, Any]:
    stats = world.get_stats(include_distributions=False)
    living = [e for e in world.entities_list if isinstance(e, Fish) and not e.is_dead()]
    diversity = stats.get("diversity_stats", {})
    return {
        "frame": frame,
        "max_generation": stats.get("max_generation", 0),
        "population": stats.get("fish_count", 0),
        "births_total": stats.get("total_births", stats.get("births", 0)),
        "deaths_total": stats.get("total_deaths", stats.get("deaths", 0)),
        "diversity_score": diversity.get("diversity_score", 0.0),
        "traits": compute_trait_means(living),
    }


def _trait_drift(
    first_traits: dict[str, float], last_traits: dict[str, float]
) -> dict[str, dict[str, Any]]:
    drift: dict[str, dict[str, Any]] = {}
    for trait in EVOLUTION_TRAIT_KEYS:
        if trait not in first_traits or trait not in last_traits:
            continue
        start = float(first_traits[trait])
        end = float(last_traits[trait])
        delta = end - start
        pct = (delta / start * 100.0) if start else 0.0
        drift[trait] = {
            "start": round(start, 5),
            "end": round(end, 5),
            "delta": round(delta, 5),
            "pct": round(pct, 2),
            "selection": abs(pct) >= TRAIT_DRIFT_SELECTION_PCT,
        }
    return drift


def _stability_component(values: list[float]) -> float:
    if not values:
        return 0.0
    cv = _coefficient_of_variation(values)
    return 1.0 / (1.0 + cv)


def _coefficient_of_variation(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 1.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance) / mean


def _run_fingerprint_pass(
    seed: int, fingerprint_callback: Callable[[Any, int], None]
) -> None:
    config = dict(WORLD_CONFIG)
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)
    fingerprint_callback(world, 0)
    for frame in range(1, FRAMES + 1):
        world.step()
        fingerprint_callback(world, frame)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(json.dumps(run(args.seed), indent=2))
