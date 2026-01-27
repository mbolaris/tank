"""Soccer Training Benchmark (3k frames).

Measures team performance and coordination in soccer using RCSS-Lite engine.
Score is side-invariant and aggregated across multiple seeds with team swapping
to reduce left/right assignment noise.

Reduced from 5k to 3k frames for faster evolution iteration.
"""

import sys
import time
from typing import Any, Dict, List

from core.code_pool import create_default_genome_code_pool
from core.genetics import Genome
from core.minigames.soccer import SoccerMatchRunner

BENCHMARK_ID = "soccer/training_3k"
FRAMES = 3000
DEFAULT_N_SEEDS = 5
SCORE_SCALE = 0.1


def _create_default_population(
    seed: int,
    population_size: int,
    genome_code_pool: Any,
) -> List[Genome]:
    import random

    rng = random.Random(seed)

    population: List[Genome] = []
    default_id = genome_code_pool.get_default("soccer_policy")
    if default_id:
        from core.genetics.trait import GeneticTrait

    for _ in range(population_size):
        genome = Genome.random(use_algorithm=False, rng=rng)
        if default_id:
            genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
        population.append(genome)

    return population


def _run_episode(
    runner: SoccerMatchRunner,
    population: List[Genome],
    seed: int,
    frames: int,
) -> Dict[str, Any]:
    episode_result, agent_results = runner.run_episode(
        genomes=population,
        seed=seed,
        frames=frames,
        goal_weight=100.0,
    )

    score_left = episode_result.score_left
    score_right = episode_result.score_right
    goal_diff = score_left - score_right
    total_goals = score_left + score_right

    possession_left = 0
    possession_right = 0
    for _pid, stats in episode_result.player_stats.items():
        if stats.team == "left":
            possession_left += stats.possessions
        else:
            possession_right += stats.possessions

    total_possession = possession_left + possession_right
    possession_diff = (possession_left - possession_right) / 60.0

    team_fitness_left = sum(r.fitness for r in agent_results if r.team == "left")
    team_fitness_right = sum(r.fitness for r in agent_results if r.team == "right")
    team_fitness = team_fitness_left + team_fitness_right
    avg_fitness = team_fitness / max(len(population), 1)

    # Side-invariant score (left/right labels do not matter).
    score = avg_fitness * SCORE_SCALE

    return {
        "score": score,
        "avg_fitness": avg_fitness,
        "team_fitness_left": team_fitness_left,
        "team_fitness_right": team_fitness_right,
        "score_left": score_left,
        "score_right": score_right,
        "total_goals": total_goals,
        "goal_diff": goal_diff,
        "possession_left": possession_left,
        "possession_right": possession_right,
        "total_possession": total_possession,
        "possession_diff": possession_diff,
    }


def run(
    seed: int,
    *,
    n_seeds: int = DEFAULT_N_SEEDS,
    frames: int = FRAMES,
    team_size: int = 3,
) -> Dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Random seed for the simulation
        n_seeds: Number of seeds to aggregate over (default: training benchmark setting)
        frames: Frames per episode (default: training benchmark setting)
        team_size: Players per team (default: 3)

    Returns:
        Result dictionary with score, metrics, and metadata
    """
    start_time = time.time()

    # Create genome code pool for autopolicy
    genome_code_pool = create_default_genome_code_pool()

    # Create match runner
    runner = SoccerMatchRunner(
        team_size=team_size,
        genome_code_pool=genome_code_pool,
    )

    population_size = team_size * 2
    seeds = [seed + i for i in range(n_seeds)]

    per_seed_results: List[Dict[str, Any]] = []
    per_seed_scores: List[float] = []

    base_seed_normal: Dict[str, Any] = {}

    for eval_seed in seeds:
        population = _create_default_population(
            seed=eval_seed,
            population_size=population_size,
            genome_code_pool=genome_code_pool,
        )
        swapped_population = population[team_size:] + population[:team_size]

        print(
            f"  Seed {eval_seed}: {frames} frames x2 (normal + swapped)...",
            file=sys.stderr,
        )

        normal = _run_episode(runner, population, seed=eval_seed, frames=frames)
        swapped = _run_episode(runner, swapped_population, seed=eval_seed, frames=frames)
        if eval_seed == seed:
            base_seed_normal = normal

        per_seed_score = (normal["score"] + swapped["score"]) / 2.0
        per_seed_scores.append(per_seed_score)
        per_seed_results.append(
            {
                "seed": eval_seed,
                "per_seed_score": per_seed_score,
                "normal": normal,
                "swapped": swapped,
            }
        )

    score = sum(per_seed_scores) / max(len(per_seed_scores), 1)

    runtime = time.time() - start_time

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": runtime,
        "metadata": {
            # Legacy fields required for champion reproduction checks.
            # Derived from the base-seed normal run so existing champions remain valid.
            "frames": frames,
            "score_left": base_seed_normal.get("score_left"),
            "score_right": base_seed_normal.get("score_right"),
            "total_goals": base_seed_normal.get("total_goals"),
            "goal_diff": base_seed_normal.get("goal_diff"),
            "possession_left": base_seed_normal.get("possession_left"),
            "possession_right": base_seed_normal.get("possession_right"),
            "total_possession": base_seed_normal.get("total_possession"),
            "possession_diff": base_seed_normal.get("possession_diff"),
            "avg_fitness": base_seed_normal.get("avg_fitness"),
            "team_fitness_left": base_seed_normal.get("team_fitness_left"),
            "team_fitness_right": base_seed_normal.get("team_fitness_right"),
            # New aggregation metadata.
            "team_size": team_size,
            "population_size": population_size,
            "n_seeds": n_seeds,
            "seeds": seeds,
            "score_mode": f"avg_fitness*{SCORE_SCALE} (side-invariant)",
            "score_scale": SCORE_SCALE,
            "per_seed_results": per_seed_results,
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
        score_diff = abs(res1["score"] - res2["score"])
        if score_diff > 1e-9:
            print(f"DETERMINISM FAILED: {res1['score']} != {res2['score']}", file=sys.stderr)
            sys.exit(1)
        print(f"DETERMINISM PASSED: {res1['score']}")
    else:
        result = run(args.seed)
        print(json.dumps(result, indent=2))
