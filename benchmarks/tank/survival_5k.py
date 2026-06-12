"""Tank Survival Benchmark (5k frames).

Measures the stability and robustness of the ecosystem over a medium duration.
Score is calculated based on integral **fish** energy and **fish** population
stability.

IMPORTANT: Population is measured as the number of *fish* entities only, not
all entities in the world (which would include food, crabs, balls, etc.).
"""

import sys
import time
from typing import Any

from core.worlds import WorldRegistry

BENCHMARK_ID = "tank/survival_5k"
FRAMES = 5000
METRICS_INTERVAL = 250  # Sample metrics periodically, not every frame

# World configuration, replicating SimulationConfig.headless_fast() parameters.
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
    # Pin soccer league off so default-config changes cannot shift the score.
    # Ball+goals remain (tank_practice_enabled defaults to True) for the
    # SoccerSystem kick/goal energy path, but the league never schedules
    # matches and therefore never injects refill-to-max rewards.
    "soccer_enabled": False,
}

# Effective configuration captured by the champion config hash
# (core/solutions/config_hash.py). Anything that changes the score belongs here.
CONFIG: dict[str, Any] = {"frames": FRAMES, "world_config": WORLD_CONFIG}


def run(seed: int) -> dict[str, Any]:
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

    # Metrics accumulators
    total_fish_energy_integral = 0.0
    total_fish_pop_integral = 0
    extinctions = 0
    samples = 0
    max_generation = 0

    # Run loop
    for i in range(FRAMES):
        world.step()

        # Sample metrics every frame for accuracy
        stats = world.get_stats(include_distributions=False)

        # BUG FIX: Use fish_count from stats, NOT len(world.entities_list).
        # entities_list includes Food, LiveFood, Crab, Ball, GoalZone, Castle,
        # etc. — inflating the population count and corrupting the score.
        current_fish_pop = stats.get("fish_count", 0)
        current_fish_energy = stats.get("fish_energy", 0)

        total_fish_energy_integral += current_fish_energy
        total_fish_pop_integral += current_fish_pop
        samples += 1

        if current_fish_pop == 0:
            extinctions += 1

        gen = stats.get("max_generation", 0)
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
    # Average fish energy per frame * Average fish population per frame / 1000
    # (Penalizing early extinction heavily since integrals will be small)
    avg_fish_energy = total_fish_energy_integral / FRAMES
    avg_fish_pop = total_fish_pop_integral / FRAMES

    # Score definition: (Avg Fish Energy * Avg Fish Pop) / 1000
    # Higher is better.
    score = (avg_fish_energy * avg_fish_pop) / 1000.0

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "avg_energy": avg_fish_energy,
            "avg_pop": avg_fish_pop,
            "extinct": extinctions > 0,
            "samples": samples,
            # --- Score breakdown (new) ---
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
