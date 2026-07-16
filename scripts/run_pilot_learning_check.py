"""Pilot check: prove learning in both domains before transfer.

Evaluates 4 seeds. For each seed:
1. Food Domain (held-out validation):
   - Initial population (mean score of shared founders)
   - Neutral evolution (drifted control)
   - Food-trained (active selection on food)
2. Ball Domain (held-out validation):
   - Initial population (mean score of shared founders)
   - Neutral evolution (drifted control)
   - Ball-trained (active selection on ball)

Verifies Gate B and Gate C.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.behavior.target_memory import TargetMemoryParams
from core.behavior.target_memory_transfer_gym import (
    evaluate_params_on_set,
    generate_scenario_set,
)
from core.behavior.target_memory_transfer_evolution import (
    TargetMemoryGenome,
    run_evolution,
    generate_diverse_population,
)

SEEDS = (0, 1, 2, 3)
POP_SIZE = 32
GENERATIONS = 30
RUNS = 3
FOOD_TRAIN_COUNT = 16
FOOD_VAL_COUNT = 8
BALL_TRAIN_COUNT = 16
BALL_VAL_COUNT = 8


def evaluate_population(pop: list[TargetMemoryGenome], scenarios) -> float:
    return sum(evaluate_params_on_set(g.params, scenarios).overall_score for g in pop) / len(pop)


def main():
    parser = argparse.ArgumentParser(description="Pilot learning check")
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    args = parser.parse_args()

    print(f"Running pilot check across seeds: {args.seeds}")
    print(f"Budget: {POP_SIZE} pop | {GENERATIONS} gen | {RUNS} runs")
    print(
        f"Scenarios: food={FOOD_TRAIN_COUNT}t/{FOOD_VAL_COUNT}v, ball={BALL_TRAIN_COUNT}t/{BALL_VAL_COUNT}v"
    )
    print("-" * 70)

    rows = []
    food_learn_gains = []
    ball_learn_gains = []
    food_vs_drift_gains = []
    ball_vs_drift_gains = []

    for seed in args.seeds:
        print(f"\nEvaluating Seed {seed}...")
        # Scenarios
        train_food = generate_scenario_set("train", seed, count=FOOD_TRAIN_COUNT)
        val_food = generate_scenario_set("validation", seed, count=FOOD_VAL_COUNT)
        train_ball = generate_scenario_set("ball_train", seed, count=BALL_TRAIN_COUNT)
        val_ball = generate_scenario_set("ball_validation", seed, count=BALL_VAL_COUNT)

        default_genome = TargetMemoryGenome(params=TargetMemoryParams())

        # Generate shared founders for each of the RUNS
        shared_founders_list = []
        for run_idx in range(RUNS):
            init_rng = random.Random(seed + 7000 + run_idx * 100)
            pop = generate_diverse_population(default_genome, POP_SIZE, init_rng)
            shared_founders_list.append(pop)

        # 1. Food Domain
        print("  Evolving food domain...")
        init_food_scores = [evaluate_population(pop, val_food) for pop in shared_founders_list]
        init_food_avg = sum(init_food_scores) / len(init_food_scores)

        neutral_food_genomes = []
        food_trained_genomes = []

        for run_idx in range(RUNS):
            run_rng_neutral = random.Random(seed + 8000 + run_idx * 100)
            best_neutral, _, _ = run_evolution(
                shared_founders_list[run_idx],
                train_food,
                GENERATIONS,
                POP_SIZE,
                run_rng_neutral,
                shuffle_fitness=True,
            )
            neutral_food_genomes.append(best_neutral)

            run_rng_active = random.Random(seed + 9000 + run_idx * 100)
            best_active, _, _ = run_evolution(
                shared_founders_list[run_idx],
                train_food,
                GENERATIONS,
                POP_SIZE,
                run_rng_active,
                validation_scenarios=val_food,
            )
            food_trained_genomes.append(best_active)

        drift_food_avg = (
            sum(
                evaluate_params_on_set(g.params, val_food).overall_score
                for g in neutral_food_genomes
            )
            / RUNS
        )
        select_food_avg = (
            sum(
                evaluate_params_on_set(g.params, val_food).overall_score
                for g in food_trained_genomes
            )
            / RUNS
        )

        # 2. Ball Domain
        print("  Evolving ball domain...")
        init_ball_scores = [evaluate_population(pop, val_ball) for pop in shared_founders_list]
        init_ball_avg = sum(init_ball_scores) / len(init_ball_scores)

        neutral_ball_genomes = []
        ball_trained_genomes = []

        for run_idx in range(RUNS):
            run_rng_neutral = random.Random(seed + 8500 + run_idx * 100)
            best_neutral, _, _ = run_evolution(
                shared_founders_list[run_idx],
                train_ball,
                GENERATIONS,
                POP_SIZE,
                run_rng_neutral,
                shuffle_fitness=True,
            )
            neutral_ball_genomes.append(best_neutral)

            run_rng_active = random.Random(seed + 10000 + run_idx * 100)
            best_active, _, _ = run_evolution(
                shared_founders_list[run_idx],
                train_ball,
                GENERATIONS,
                POP_SIZE,
                run_rng_active,
                validation_scenarios=val_ball,
            )
            ball_trained_genomes.append(best_active)

        drift_ball_avg = (
            sum(
                evaluate_params_on_set(g.params, val_ball).overall_score
                for g in neutral_ball_genomes
            )
            / RUNS
        )
        select_ball_avg = (
            sum(
                evaluate_params_on_set(g.params, val_ball).overall_score
                for g in ball_trained_genomes
            )
            / RUNS
        )

        row = {
            "seed": seed,
            "food_init": init_food_avg,
            "food_drift": drift_food_avg,
            "food_select": select_food_avg,
            "ball_init": init_ball_avg,
            "ball_drift": drift_ball_avg,
            "ball_select": select_ball_avg,
        }
        rows.append(row)

        food_learn_gains.append(select_food_avg - init_food_avg)
        ball_learn_gains.append(select_ball_avg - init_ball_avg)
        food_vs_drift_gains.append(select_food_avg - drift_food_avg)
        ball_vs_drift_gains.append(select_ball_avg - drift_ball_avg)

        print(
            f"  Food: Initial={init_food_avg:.4f} | Drift={drift_food_avg:.4f} | Select={select_food_avg:.4f} (gain={select_food_avg - init_food_avg:+.4f})"
        )
        print(
            f"  Ball: Initial={init_ball_avg:.4f} | Drift={drift_ball_avg:.4f} | Select={select_ball_avg:.4f} (gain={select_ball_avg - init_ball_avg:+.4f})"
        )

    # Render results summary
    print("\n" + "=" * 70)
    print(" PILOT CHECK RESULTS SUMMARY")
    print("=" * 70)
    print(
        "| Seed | Food Init | Food Drift | Food Select | Food Gain | Ball Init | Ball Drift | Ball Select | Ball Gain |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(
            f"| {r['seed']} | {r['food_init']:.4f} | {r['food_drift']:.4f} | {r['food_select']:.4f} | {r['food_select'] - r['food_init']:+.4f} | "
            f"{r['ball_init']:.4f} | {r['ball_drift']:.4f} | {r['ball_select']:.4f} | {r['ball_select'] - r['ball_init']:+.4f} |"
        )
    print("-" * 70)
    print(f"Mean Food Gain vs Init:  {sum(food_learn_gains)/len(food_learn_gains):+.4f}")
    print(f"Mean Food Gain vs Drift: {sum(food_vs_drift_gains)/len(food_vs_drift_gains):+.4f}")
    print(f"Mean Ball Gain vs Init:  {sum(ball_learn_gains)/len(ball_learn_gains):+.4f}")
    print(f"Mean Ball Gain vs Drift: {sum(ball_vs_drift_gains)/len(ball_vs_drift_gains):+.4f}")
    print()

    # Verdicts
    f_pass = all(g > 0.002 for g in food_vs_drift_gains) and all(
        g > 0.002 for g in food_learn_gains
    )
    b_pass = all(g > 0.002 for g in ball_vs_drift_gains) and all(
        g > 0.002 for g in ball_learn_gains
    )

    print(f"Gate B (Food Learning) Verdict: {'PASS' if f_pass else 'FAIL'}")
    print(f"Gate C (Ball Learning) Verdict: {'PASS' if b_pass else 'FAIL'}")


if __name__ == "__main__":
    main()
