"""Tank Ecosystem Health Benchmark (10k frames).

Measures evolutionary fitness of the ecosystem: generation speed, diversity,
starvation rate, and population stability. Complements survival_5k which only
measures raw energy * population.

This benchmark was created as a Layer 2 meta-evolution improvement to provide
selection pressure for changes that improve evolutionary dynamics, not just
short-term population survival.

Score formula:
    score = generation_rate * diversity_bonus * stability_bonus * (1 - starvation_penalty)

Higher is better. Rewards:
    - Fast generation turnover (evolution speed)
    - Genetic diversity (unique algorithms, trait variance)
    - Population stability (low variance in population over time)
    - Low starvation rate (fish that can actually find food)
"""

from __future__ import annotations

import math
import sys
import time
from collections.abc import Callable
from typing import Any

from core.worlds import WorldRegistry

BENCHMARK_ID = "tank/ecosystem_health_10k"
FRAMES = 10000
SAMPLE_INTERVAL = 100  # Sample every 100 frames for population stability tracking

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
}

# Effective configuration captured by the champion config hash
# (core/solutions/config_hash.py). Anything that changes the score belongs here.
CONFIG: dict[str, Any] = {
    "frames": FRAMES,
    "sample_interval": SAMPLE_INTERVAL,
    "world_config": WORLD_CONFIG,
}


def run(
    seed: int, fingerprint_callback: Callable[[Any, int], None] | None = None
) -> dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    start_time = time.time()

    config = dict(WORLD_CONFIG)

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)
    if fingerprint_callback is not None:
        fingerprint_callback(world, 0)

    # Accumulators
    population_samples = []
    total_deaths = 0
    starvation_deaths = 0
    max_generation = 0

    for i in range(FRAMES):
        world.step()
        if fingerprint_callback is not None:
            fingerprint_callback(world, i + 1)

        if (i + 1) % SAMPLE_INTERVAL == 0:
            stats = world.get_stats(include_distributions=False)
            # BUG FIX: Use fish_count, NOT len(world.entities_list) which
            # includes food, crabs, balls, goal zones, etc.
            pop = stats.get("fish_count", 0)
            population_samples.append(pop)

            # Track death causes
            death_causes = stats.get("death_causes", {})
            frame_total = sum(death_causes.values())
            frame_starvation = death_causes.get("starvation", 0)
            total_deaths = frame_total
            starvation_deaths = frame_starvation

            # Track generation
            gen = stats.get("max_generation", 0)
            if gen > max_generation:
                max_generation = gen

            # Track diversity
            diversity_stats = stats.get("diversity_stats", {})

        if (i + 1) % 2000 == 0:
            print(f"  Frame {i+1}/{FRAMES}...", file=sys.stderr)

    runtime = time.time() - start_time

    # Final stats
    stats = world.get_stats(include_distributions=True)
    diversity_stats = stats.get("diversity_stats", {})
    death_causes = stats.get("death_causes", {})

    total_deaths = sum(death_causes.values())
    starvation_deaths = death_causes.get("starvation", 0)
    starvation_rate = starvation_deaths / max(total_deaths, 1)

    unique_algorithms = diversity_stats.get("unique_algorithms", 1)
    diversity_score = diversity_stats.get("diversity_score", 0.0)

    # --- Score Components ---

    # 1. Generation rate: generations per 10k frames (higher = faster evolution)
    generation_rate = max_generation / (FRAMES / 10000.0)

    # 2. Diversity bonus: log scale, rewards having multiple strategies
    diversity_bonus = 1.0 + math.log2(max(unique_algorithms, 1)) * 0.3 + diversity_score

    # 3. Population stability: 1 / (1 + coefficient of variation)
    if population_samples:
        mean_pop = sum(population_samples) / len(population_samples)
        if mean_pop > 0:
            variance = sum((p - mean_pop) ** 2 for p in population_samples) / len(
                population_samples
            )
            cv = math.sqrt(variance) / mean_pop
            stability_bonus = 1.0 / (1.0 + cv)
        else:
            stability_bonus = 0.01  # Extinction
    else:
        stability_bonus = 0.01

    # 4. Starvation penalty: high starvation = bad food-seeking
    starvation_penalty = starvation_rate * 0.5  # Max 50% penalty at 100% starvation

    # Combined score
    score = generation_rate * diversity_bonus * stability_bonus * (1.0 - starvation_penalty)

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "max_generation": max_generation,
            "generation_rate": generation_rate,
            "starvation_rate": round(starvation_rate, 4),
            "starvation_deaths": starvation_deaths,
            "total_deaths": total_deaths,
            "unique_algorithms": unique_algorithms,
            "diversity_score": round(diversity_score, 4),
            "diversity_bonus": round(diversity_bonus, 4),
            "stability_bonus": round(stability_bonus, 4),
            "starvation_penalty": round(starvation_penalty, 4),
            "mean_population": round(mean_pop, 2) if population_samples else 0,
            "final_population": stats.get("fish_count", 0),
            "final_total_entities": len(world.entities_list),
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    if args.verify_determinism:
        res1 = run(args.seed)
        res2 = run(args.seed)
        if res1["score"] == res2["score"]:
            print(f"DETERMINISM PASSED: {res1['score']}")
            sys.exit(0)
        else:
            print(f"DETERMINISM FAILED: {res1['score']} != {res2['score']}")
            sys.exit(1)

    result = run(args.seed)
    print(json.dumps(result, indent=2))
