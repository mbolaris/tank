"""Tank Survival Benchmark (5k frames).

Measures the stability and robustness of the ecosystem over a medium duration.
Score is calculated based on integral energy and population stability.
"""

import sys
import time
from typing import Any, Dict

from core.worlds import WorldRegistry

BENCHMARK_ID = "tank/survival_5k"
FRAMES = 5000
METRICS_INTERVAL = 250  # Sample metrics periodically, not every frame


def run(seed: int) -> Dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    start_time = time.time()

    # Configure via WorldRegistry with custom config
    # Replicates SimulationConfig.headless_fast() parameters
    config = {
        "headless": True,
        "screen_width": 2000,
        "screen_height": 2000,
        "max_population": 60,
        "critical_population_threshold": 5,
        "emergency_spawn_cooldown": 90,
        "poker_activity_enabled": False,
        "plants_enabled": False,
        "auto_food_spawn_rate": 9,
    }

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    # Metrics accumulators
    total_energy_integral = 0.0
    total_pop_integral = 0
    extinctions = 0
    samples = 0

    # Run loop
    for i in range(FRAMES):
        world.step()

        # Sample metrics every frame for score consistency with champions
        # Original formula: population = len(entities_list), energy = total_energy from ecosystem
        stats = world.get_stats(include_distributions=False)

        current_pop = len(world.entities_list)
        current_energy = stats.get("total_energy", 0)

        total_energy_integral += current_energy
        total_pop_integral += current_pop
        samples += 1

        if (i + 1) % 1000 == 0:
            print(f"  Frame {i+1}/{FRAMES}...", file=sys.stderr)

    runtime = time.time() - start_time

    # Calculate Score
    # Simple metric: Average energy per frame * Average population per frame
    # (Penalizing early extinction heavily since integrals will be small)
    avg_energy = total_energy_integral / FRAMES
    avg_pop = total_pop_integral / FRAMES

    # Score definition: (Avg Energy * Avg Pop) / 1000
    # Higher is better.
    score = (avg_energy * avg_pop) / 1000.0

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "avg_energy": avg_energy,
            "avg_pop": avg_pop,
            "extinct": extinctions > 0,
            "samples": samples,
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
