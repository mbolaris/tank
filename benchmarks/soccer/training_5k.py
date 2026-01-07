"""Soccer Training Benchmark (5k frames).

Measures team performance and coordination in soccer training world.
Score is based on goal differential, possession time, and energy efficiency.
"""

import sys
import time
from typing import Any, Dict

from core.worlds.soccer_training.config import SoccerTrainingConfig
from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter

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

    # Run loop
    for i in range(FRAMES):
        world.step()

        if (i + 1) % 1000 == 0:
            print(f"  Frame {i+1}/{FRAMES}...", file=sys.stderr)

    runtime = time.time() - start_time

    # Final metrics
    # Final metrics
    world.get_current_metrics()
    final_fitness = world.get_fitness_summary()

    # Calculate score
    # Goal differential (primary objective)
    goal_diff = final_fitness["score"]["left"] - final_fitness["score"]["right"]

    # Possession differential (secondary objective)
    # Possession stats are tracked in agent_fitness (frames in possession)
    possession_left = 0
    possession_right = 0
    for agent_data in final_fitness["agent_fitness"].values():
        if agent_data["team"] == "left":
            possession_left += agent_data["possessions"]
        else:
            possession_right += agent_data["possessions"]

    # Convert frames to seconds (approximate using timestep if available, or just use raw frames for now)
    # The config has frame_rate = 30 default.
    # We'll use raw frames for the diff score since it's relative.
    possession_diff = (possession_left - possession_right) / 30.0  # Convert to seconds roughly

    # Team fitness (energy efficiency)
    team_energy = final_fitness["team_fitness"]["left"] + final_fitness["team_fitness"]["right"]
    # Provide a floor for player count to avoid division by zero
    player_count = max(config.team_size * 2, 1)
    avg_energy = team_energy / player_count

    # Score formula:
    # - Goal differential: 100 points per goal
    # - Possession diff: 1.0 point per second of advantage
    # - Average energy: 0.1 points per energy unit (efficiency bonus)
    score = (goal_diff * 100.0) + (possession_diff * 1.0) + (avg_energy * 0.1)

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
            "possession_left": possession_left,
            "possession_right": possession_right,
            "possession_diff": possession_diff,
            "avg_energy": avg_energy,
            "team_energy_left": final_fitness["team_fitness"]["left"],
            "team_energy_right": final_fitness["team_fitness"]["right"],
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
        if res1["score"] != res2["score"]:
            print(f"DETERMINISM FAILED: {res1['score']} != {res2['score']}", file=sys.stderr)
            sys.exit(1)
        print(f"DETERMINISM PASSED: {res1['score']}")
    else:
        result = run(args.seed)
        print(json.dumps(result, indent=2))
