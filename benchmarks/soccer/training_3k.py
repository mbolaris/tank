"""Soccer Training Benchmark (3k frames).

Measures team performance and coordination in soccer using RCSS-Lite engine.
Score is based on goal differential, possession time, and stamina efficiency.

Reduced from 5k to 3k frames for faster evolution iteration.
"""

import sys
import time
from typing import Any, Dict

from core.code_pool import create_default_genome_code_pool
from core.genetics import Genome
from core.minigames.soccer import SoccerMatchRunner

BENCHMARK_ID = "soccer/training_3k"
FRAMES = 3000


def run(seed: int) -> Dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    import random

    start_time = time.time()

    # Create genome code pool for autopolicy
    genome_code_pool = create_default_genome_code_pool()

    # Create population with default policies
    rng = random.Random(seed)
    team_size = 3  # 3v3 for faster training
    population_size = team_size * 2

    population = []
    for _ in range(population_size):
        genome = Genome.random(use_algorithm=False, rng=rng)
        # Assign default soccer policy
        default_id = genome_code_pool.get_default("soccer_policy")
        if default_id:
            from core.genetics.trait import GeneticTrait

            genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
        population.append(genome)

    # Create match runner
    runner = SoccerMatchRunner(
        team_size=team_size,
        genome_code_pool=genome_code_pool,
    )

    # Run episode
    print(f"  Running {FRAMES} frames...", file=sys.stderr)
    episode_result, agent_results = runner.run_episode(
        genomes=population,
        seed=seed,
        frames=FRAMES,
        goal_weight=100.0,
    )

    runtime = time.time() - start_time

    # Calculate metrics from episode result
    score_left = episode_result.score_left
    score_right = episode_result.score_right
    goal_diff = score_left - score_right
    total_goals = score_left + score_right

    # Possession from player stats
    possession_left = 0
    possession_right = 0
    for pid, stats in episode_result.player_stats.items():
        if stats.team == "left":
            possession_left += stats.possessions
        else:
            possession_right += stats.possessions

    total_possession = possession_left + possession_right
    # Convert frames to approximate seconds
    possession_diff = (possession_left - possession_right) / 60.0

    # Team fitness from agent results
    team_fitness_left = sum(r.fitness for r in agent_results if r.team == "left")
    team_fitness_right = sum(r.fitness for r in agent_results if r.team == "right")
    team_fitness = team_fitness_left + team_fitness_right
    avg_fitness = team_fitness / max(population_size, 1)

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
            "score_left": score_left,
            "score_right": score_right,
            "total_goals": total_goals,
            "goal_diff": goal_diff,
            "possession_left": possession_left,
            "possession_right": possession_right,
            "total_possession": total_possession,
            "possession_diff": possession_diff,
            "avg_fitness": avg_fitness,
            "team_fitness_left": team_fitness_left,
            "team_fitness_right": team_fitness_right,
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
