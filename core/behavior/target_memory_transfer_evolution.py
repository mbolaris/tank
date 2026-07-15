"""Evolution loop and top-level assay for the target-memory transfer gym.

Split out from core/behavior/target_memory_transfer_gym.py (which owns
scenario generation and single-episode evaluation) purely to stay under the
repo's god-class line-limit ratchet - see that module's docstring for the
assay's actual design rationale (shared vs. disjoint arms, the fixed mutation
schedule, and why it's the only mutation-intensity lever wired for
target_memory today).
"""

from __future__ import annotations

import random

from core.behavior.target_memory import TargetMemoryParams
from core.behavior.target_memory_transfer_gym import (
    CROSSOVER_WEIGHT,
    EVOLUTION_RUNS,
    GENERATIONS,
    MUTATION_RATE,
    MUTATION_STRENGTH,
    POPULATION_SIZE,
    EvaluationSummary,
    TargetMemoryScenario,
    TargetMemoryTransferEvaluation,
    average_summaries,
    evaluate_naive_greedy_on_set,
    evaluate_params_on_set,
    generate_scenario_set,
)


def run_evolution(
    initial_population: list[TargetMemoryParams],
    scenarios: list[TargetMemoryScenario],
    generations: int,
    pop_size: int,
    rng: random.Random,
    target_score_threshold: float | None = None,
    validation_scenarios: list[TargetMemoryScenario] | None = None,
) -> tuple[TargetMemoryParams, list[float], int]:
    """Run genetic algorithm over TargetMemoryParams with optional validation
    selection. Mirrors core/pursuit/transfer_gym.py's run_evolution shape."""
    population = list(initial_population)
    while len(population) < pop_size:
        seed_params = population[rng.randrange(len(population))]
        var = seed_params.crossed_over(
            seed_params, weight1=1.0, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        population.append(var)

    best_params = population[0]
    best_score = float("-inf")
    pop_scores = []
    for candidate in population:
        score = evaluate_params_on_set(candidate, scenarios).overall_score
        pop_scores.append(score)
        if score > best_score:
            best_score = score
            best_params = candidate

    history = [best_score]

    selected_params = best_params
    best_validation_score = float("-inf")
    if validation_scenarios is not None:
        best_validation_score = evaluate_params_on_set(
            best_params, validation_scenarios
        ).overall_score

    if target_score_threshold is not None and best_score >= target_score_threshold:
        return best_params, history, 0

    for gen in range(1, generations + 1):
        new_population = []
        elite_idx = pop_scores.index(max(pop_scores))
        new_population.append(population[elite_idx])

        while len(new_population) < pop_size:
            t1 = rng.sample(
                list(zip(population, pop_scores, strict=False)), min(3, len(population))
            )
            parent1 = max(t1, key=lambda x: x[1])[0]

            t2 = rng.sample(
                list(zip(population, pop_scores, strict=False)), min(3, len(population))
            )
            parent2 = max(t2, key=lambda x: x[1])[0]

            child = parent1.crossed_over(
                parent2,
                weight1=CROSSOVER_WEIGHT,
                mutation_rate=MUTATION_RATE,
                mutation_strength=MUTATION_STRENGTH,
                rng=rng,
            )
            new_population.append(child)

        population = new_population
        pop_scores = [best_score]

        for candidate in population[1:]:
            score = evaluate_params_on_set(candidate, scenarios).overall_score
            pop_scores.append(score)
            if score > best_score:
                best_score = score
                best_params = candidate

        history.append(best_score)

        if validation_scenarios is not None:
            elite = population[pop_scores.index(max(pop_scores))]
            validation_score = evaluate_params_on_set(elite, validation_scenarios).overall_score
            if validation_score > best_validation_score:
                best_validation_score = validation_score
                selected_params = elite

        if target_score_threshold is not None and best_score >= target_score_threshold:
            return selected_params, history, gen

    return selected_params, history, generations


def evaluate_target_memory_transfer(seed: int) -> TargetMemoryTransferEvaluation:
    """Evolve populations over food scenarios; evaluate zero-shot and measure
    adaptation on ball scenarios, against a founder-default disjoint control."""
    train_food = generate_scenario_set("train", seed)
    validation_food = generate_scenario_set("validation", seed)
    test_ball = generate_scenario_set("held_out", seed)
    train_ball = generate_scenario_set("ball_train", seed)
    validation_ball = generate_scenario_set("ball_validation", seed)

    default_params = TargetMemoryParams()
    summaries: dict[str, EvaluationSummary] = {}

    # Group 1: naive greedy (no memory at all)
    summaries["naive_greedy"] = evaluate_naive_greedy_on_set(test_ball)

    # Group 2: default/founder params - also the disjoint arm's zero-shot
    # baseline (a target_memory that food selection never touched).
    summaries["default_params"] = evaluate_params_on_set(default_params, test_ball)

    # Group 3: compute-matched random search on food, zero-shot on ball
    rng_random = random.Random(seed + 8000)
    best_random = default_params
    best_random_score = float("-inf")
    for _ in range(POPULATION_SIZE * GENERATIONS * EVOLUTION_RUNS):
        candidate = default_params.crossed_over(
            default_params,
            weight1=1.0,
            mutation_rate=1.0,
            mutation_strength=MUTATION_STRENGTH,
            rng=rng_random,
        )
        cand_score = evaluate_params_on_set(candidate, train_food).overall_score
        if cand_score > best_random_score:
            best_random = candidate
            best_random_score = cand_score
    summaries["random_search"] = evaluate_params_on_set(best_random, test_ball)

    # Group 4: food-trained populations (shared arm's basis) - zero-shot on ball
    food_trained_params = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 9000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            [default_params],
            train_food,
            GENERATIONS,
            POPULATION_SIZE,
            run_rng,
            validation_scenarios=validation_food,
        )
        food_trained_params.append(best_of_run)

    food_evals = [evaluate_params_on_set(p, test_ball) for p in food_trained_params]
    summaries["food_trained"] = average_summaries(food_evals)

    # Group 5: ball-trained (task-specific reference)
    ball_trained_params = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 10000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            [default_params],
            train_ball,
            GENERATIONS,
            POPULATION_SIZE,
            run_rng,
            validation_scenarios=validation_ball,
        )
        ball_trained_params.append(best_of_run)

    ball_evals = [evaluate_params_on_set(p, test_ball) for p in ball_trained_params]
    summaries["ball_trained"] = average_summaries(ball_evals)

    # Adaptation speed: shared arm (continuing from food-trained values) vs
    # disjoint arm (starting from founder/default params - never touched by
    # food selection), both unfrozen under the same ball pressure and budget.
    default_score = summaries["default_params"].overall_score
    ball_reference_score = summaries["ball_trained"].overall_score
    adaptation_threshold = default_score + max(0.001, (ball_reference_score - default_score) * 0.75)

    adapt_runs_food = []
    adapt_runs_default = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 11000 + run_idx * 100)
        food_seed = food_trained_params[run_idx % len(food_trained_params)]
        initial_pop_shared = [food_seed] * POPULATION_SIZE
        _, _, gens_shared = run_evolution(
            initial_pop_shared,
            test_ball,
            GENERATIONS * 2,
            POPULATION_SIZE,
            run_rng,
            target_score_threshold=adaptation_threshold,
        )
        adapt_runs_food.append(gens_shared)

        initial_pop_disjoint = [default_params] * POPULATION_SIZE
        _, _, gens_disjoint = run_evolution(
            initial_pop_disjoint,
            test_ball,
            GENERATIONS * 2,
            POPULATION_SIZE,
            run_rng,
            target_score_threshold=adaptation_threshold,
        )
        adapt_runs_default.append(gens_disjoint)

    avg_gens_food = int(round(sum(adapt_runs_food) / len(adapt_runs_food)))
    avg_gens_default = int(round(sum(adapt_runs_default) / len(adapt_runs_default)))

    return TargetMemoryTransferEvaluation(
        group_summaries=summaries,
        adaptation_generations_food=avg_gens_food,
        adaptation_generations_default=avg_gens_default,
        adaptation_threshold=adaptation_threshold,
    )
