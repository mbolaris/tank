"""Soccer Training Benchmark (5k frames).

Measures team performance and coordination in soccer world.
Score is based on goal differential, possession time, and stamina efficiency.
"""

import sys
import time
from typing import Any, Dict

from core.code_pool import create_default_genome_code_pool
from core.worlds.soccer.backend import SoccerWorldBackendAdapter
from core.worlds.soccer.config import SoccerWorldConfig

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

    # Create genome code pool for autopolicy
    genome_code_pool = create_default_genome_code_pool()

    # Configure deterministic environment
    config = SoccerWorldConfig(
        team_size=3,  # 3v3 for faster training
        field_width=60.0,
        field_height=40.0,
    )

    world = SoccerWorldBackendAdapter(seed=seed, config=config, genome_code_pool=genome_code_pool)
    world.reset(seed=seed)

    # Run loop - autopolicy drives players automatically
    for i in range(FRAMES):
        world.step()

        if (i + 1) % 1000 == 0:
            print(f"  Frame {i+1}/{FRAMES}...", file=sys.stderr)

    runtime = time.time() - start_time

    # Final metrics
    final_fitness = world.get_fitness_summary()

    # Calculate score
    # Goal differential (primary objective)
    goal_diff = final_fitness["score"]["left"] - final_fitness["score"]["right"]
    total_goals = final_fitness["score"]["left"] + final_fitness["score"]["right"]

    # Possession differential (secondary objective)
    possession_left = 0
    possession_right = 0
    for agent_data in final_fitness["agent_fitness"].values():
        if agent_data["team"] == "left":
            possession_left += agent_data["possessions"]
        else:
            possession_right += agent_data["possessions"]

    total_possession = possession_left + possession_right
    # Convert frames to approximate seconds
    possession_diff = (possession_left - possession_right) / 60.0

    # Team fitness (based on accumulated stats, not energy)
    team_fitness = final_fitness["team_fitness"]["left"] + final_fitness["team_fitness"]["right"]
    player_count = max(config.team_size * 2, 1)
    avg_fitness = team_fitness / player_count

    # Score formula:
    # - Goal differential: 100 points per goal
    # - Possession diff: 1.0 point per second of advantage
    # - Average fitness: 0.1 points per fitness unit
    score = (goal_diff * 100.0) + (possession_diff * 1.0) + (avg_fitness * 0.1)

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            "frames": FRAMES,
            "score_left": final_fitness["score"]["left"],
            "score_right": final_fitness["score"]["right"],
            "total_goals": total_goals,
            "goal_diff": goal_diff,
            "possession_left": possession_left,
            "possession_right": possession_right,
            "total_possession": total_possession,
            "possession_diff": possession_diff,
            "avg_fitness": avg_fitness,
            "team_fitness_left": final_fitness["team_fitness"]["left"],
            "team_fitness_right": final_fitness["team_fitness"]["right"],
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
