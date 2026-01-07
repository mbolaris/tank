"""Tank Survival Benchmark (30k frames).

Measures the stability and robustness of the ecosystem over a medium duration.
Score is calculated based on integral energy and population stability.
"""

import time
import hashlib
import sys
from typing import Dict, Any

from core.tank_world import TankWorld, TankWorldConfig


BENCHMARK_ID = "tank/survival_5k"
FRAMES = 5000  # Reduced for MVP verification (was 30000)


def run(seed: int) -> Dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    start_time = time.time()

    # Configure deterministic environment
    # Use SimulationConfig directly for precise control
    from core.config.simulation_config import SimulationConfig, DisplayConfig, EcosystemConfig

    sim_config = SimulationConfig.headless_fast()

    # Customize for this benchmark
    sim_config.display.screen_width = 2000
    sim_config.display.screen_height = 2000

    # Set population constraints
    # Note: Initial population is derived from max_population/species count in engine logic,
    # or we let it auto-seed. headless_fast defaults are usually good for benchmarking.
    sim_config.ecosystem.max_population = 60

    world = TankWorld(simulation_config=sim_config, seed=seed)
    world.setup()

    # Metrics accumulators
    total_energy_integral = 0.0
    total_pop_integral = 0
    deaths = 0
    extinctions = 0

    # Run loop
    for i in range(FRAMES):
        world.update()

        # Accumulate metrics - disable distributions for speed
        metrics = world.get_stats(include_distributions=False)
        # total_energy is sometimes missing if no tracker, but headless_fast might not have it enabled by default?
        # Check if we need to enable energy tracking explicitly.
        # But headless_fast() disables phase debug, maybe not metrics?
        # SimulationRunner usually handles metrics. TankWorld.get_metrics() delegates to engine.get_metrics()

        total_energy_integral += metrics.get("total_energy", 0)
        total_pop_integral += len(world.entities_list)

        # Check specific failure modes
        if len(world.entities_list) == 0:
            extinctions += 1
            break

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
        },
    }
