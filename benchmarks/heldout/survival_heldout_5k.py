"""Held-out Tank Survival Benchmark (5k frames).

Measures the stability and robustness of the ecosystem over a medium duration.
This is a held-out benchmark that agents are not permitted to edit.
"""

import sys
import time
from collections.abc import Callable
from typing import Any

from core.worlds import WorldRegistry
from core.worlds.interfaces import FAST_STEP_ACTION

BENCHMARK_ID = "heldout/survival_heldout_5k"
FRAMES = 5000
EXPECTED_RUNTIME_SECONDS = 45

# Held-out configuration: slightly different from the public survival_5k
WORLD_CONFIG: dict[str, Any] = {
    "headless": True,
    "screen_width": 1800,  # 1800 instead of 2000
    "screen_height": 1800,  # 1800 instead of 2000
    "max_population": 50,  # 50 instead of 60
    "critical_population_threshold": 4,  # 4 instead of 5
    "emergency_spawn_cooldown": 100,  # 100 instead of 90
    "poker_activity_enabled": False,
    "plants_enabled": False,
    "auto_food_spawn_rate": 10,  # 10 instead of 9
    "soccer_enabled": False,
}

CONFIG: dict[str, Any] = {"frames": FRAMES, "world_config": WORLD_CONFIG}


def run(
    seed: int, fingerprint_callback: Callable[[Any, int], None] | None = None
) -> dict[str, Any]:
    """Run the benchmark deterministically."""
    start_time = time.time()

    config = dict(WORLD_CONFIG)

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)
    if fingerprint_callback is not None:
        fingerprint_callback(world, 0)

    # Metrics accumulators
    total_fish_energy_integral = 0.0
    total_fish_pop_integral = 0
    extinctions = 0
    samples = 0
    max_generation = 0

    for i in range(FRAMES):
        world.step({FAST_STEP_ACTION: True})
        if fingerprint_callback is not None:
            fingerprint_callback(world, i + 1)

        # Get fish count, total fish energy, and max generation directly from entities
        fish_list = [e for e in world.entities_list if getattr(e, "snapshot_type", None) == "fish"]
        current_fish_pop = len(fish_list)
        current_fish_energy = sum(
            getattr(fish, "energy", 0.0)
            + getattr(getattr(fish, "_reproduction_component", None), "overflow_energy_bank", 0.0)
            for fish in fish_list
        )

        total_fish_energy_integral += current_fish_energy
        total_fish_pop_integral += current_fish_pop
        samples += 1

        if current_fish_pop == 0:
            extinctions += 1

        if fish_list:
            gen = max(getattr(fish, "generation", 0) for fish in fish_list)
            if gen > max_generation:
                max_generation = gen

        if (i + 1) % 1000 == 0:
            print(f"  Frame {i+1}/{FRAMES} (fish={current_fish_pop})...", file=sys.stderr)

    runtime = time.time() - start_time

    # Final stats snapshot for score breakdown
    final_stats = world.get_stats(include_distributions=False)
    death_causes = final_stats.get("death_causes", {})
    total_deaths = sum(death_causes.values())
    starvation_deaths = death_causes.get("starvation", 0)
    starvation_rate = starvation_deaths / max(total_deaths, 1)
    diversity_stats = final_stats.get("diversity_stats", {})

    # Calculate Score
    avg_fish_energy = total_fish_energy_integral / FRAMES
    avg_fish_pop = total_fish_pop_integral / FRAMES
    score = (avg_fish_energy * avg_fish_pop) / 1000.0

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "score_breakdown": {
            "avg_energy": avg_fish_energy,
            "avg_pop": avg_fish_pop,
        },
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "avg_energy": avg_fish_energy,
            "avg_pop": avg_fish_pop,
            "extinct": extinctions > 0,
            "samples": samples,
            "max_generation": max_generation,
            "extinction_frames": extinctions,
            "starvation_rate": round(starvation_rate, 4),
            "starvation_deaths": starvation_deaths,
            "total_deaths": total_deaths,
            "death_causes": death_causes,
            "diversity_score": round(diversity_stats.get("diversity_score", 0.0), 4),
            "unique_algorithms": diversity_stats.get("unique_algorithms", 0),
            "final_fish_count": final_stats.get("fish_count", 0),
            "final_food_count": final_stats.get("food_count", 0),
            "final_total_entities": len(world.entities_list),
            "population_scope": "fish",
            "final_total_entities_role": "diagnostic_only",
        },
    }


if __name__ == "__main__":
    import argparse
    import json
    import subprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    if args.verify_determinism:
        cmd = [sys.executable, __file__, "--seed", str(args.seed)]
        res1 = subprocess.run(cmd, capture_output=True, text=True, check=True)
        res2 = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data1 = json.loads(res1.stdout)
        data2 = json.loads(res2.stdout)
        if data1["score"] == data2["score"]:
            print(f"DETERMINISM PASSED: {data1['score']}")
            sys.exit(0)
        else:
            print(f"DETERMINISM FAILED: {data1['score']} != {data2['score']}")
            sys.exit(1)

    result = run(args.seed)
    print(json.dumps(result, indent=2))
