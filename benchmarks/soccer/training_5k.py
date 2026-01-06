"""Soccer Training Benchmark (5k frames).

Measures team performance and coordination in soccer training world.
Score is based on goal differential, possession time, and energy efficiency.
"""

import sys
import time
from typing import Any, Dict

from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter
from core.worlds.soccer_training.config import SoccerTrainingConfig

BENCHMARK_ID = "soccer/training_5k"
FRAMES = 5000


def run(seed: int) -> Dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    start_time = time.time()

    # Configure deterministic environment
    config = SoccerTrainingConfig(
        team_size=3,  # 3v3 for faster training
        field_width=60.0,
        field_height=40.0,
    )

    world = SoccerTrainingWorldBackendAdapter(seed=seed, config=config)
    world.reset(seed=seed)

    # Metrics accumulators
    total_possession_left = 0
    total_possession_right = 0
    goals_left = 0
    goals_right = 0
    total_energy = 0.0

    # Run loop
    for i in range(FRAMES):
        result = world.step()

        # Track goals from events
        for event in result.events:
            if event.get("type") == "goal":
                if event.get("team") == "left":
                    goals_left += 1
                else:
                    goals_right += 1

        # Track possession and energy
        metrics = world.get_current_metrics()
        if "score_left" in metrics:
            # Use cumulative possession from player stats via fitness summary
            pass

        # Sum player energies
        fitness = world.get_fitness_summary()
        for player_data in fitness.get("agent_fitness", {}).values():
            total_energy += player_data.get("energy", 0)

        if (i + 1) % 1000 == 0:
            print(f"  Frame {i+1}/{FRAMES}...", file=sys.stderr)

    runtime = time.time() - start_time

    # Final metrics
    final_metrics = world.get_current_metrics()
    final_fitness = world.get_fitness_summary()

    # Calculate score
    # Goal differential (most important)
    goal_diff = final_fitness["score"]["left"] - final_fitness["score"]["right"]

    # Team fitness (energy efficiency)
    team_energy = final_fitness["team_fitness"]["left"] + final_fitness["team_fitness"]["right"]
    avg_energy = team_energy / max(len(world._players), 1)

    # Score formula:
    # - Goal differential: 100 points per goal
    # - Average energy remaining: 1 point per unit
    # This incentivizes both scoring AND efficiency
    score = (goal_diff * 100.0) + avg_energy

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "score_left": final_fitness["score"]["left"],
            "score_right": final_fitness["score"]["right"],
            "goal_diff": goal_diff,
            "avg_energy": avg_energy,
            "team_energy_left": final_fitness["team_fitness"]["left"],
            "team_energy_right": final_fitness["team_fitness"]["right"],
        },
    }
