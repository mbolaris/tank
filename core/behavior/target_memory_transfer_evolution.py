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
from dataclasses import dataclass

from core.behavior.target_memory import TargetMemoryParams
from core.behavior.target_memory_transfer_gym import (
    CROSSOVER_WEIGHT,
    EVOLUTION_RUNS,
    GENERATIONS,
    MIN_REFERENCE_EFFECT,
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
    shuffle_fitness: bool = False,
) -> tuple[TargetMemoryParams, list[float], int]:
    """Run genetic algorithm over TargetMemoryParams with optional validation
    selection. Mirrors core/pursuit/transfer_gym.py's run_evolution shape.

    ``target_score_threshold`` semantics depend on whether validation
    scenarios are provided:

    - With ``validation_scenarios``: the threshold is compared against each
      generation's elite score *on the validation set*, never against
      training fitness. Selection still happens on ``scenarios`` (the
      training set), so "generations to threshold" measures how fast the
      lineage *generalizes* to the reference bar rather than how fast it
      fits the exact training scenarios.
    - Without ``validation_scenarios``: the threshold is compared against
      the best training score (legacy in-domain behavior).

    ``shuffle_fitness=True`` turns the run into a structurally matched
    no-selection control: fitness is still evaluated for every candidate
    (same compute), but the scores are shuffled among the population before
    elitism/tournaments act on them, decoupling selection from genotype
    while preserving lineage depth, crossover count, and mutation count.
    The returned "best" individual is then a random draw from the drifted
    population - exactly what a selection-removed control should hand back.
    """
    population = list(initial_population)
    while len(population) < pop_size:
        seed_params = population[rng.randrange(len(population))]
        var = seed_params.crossed_over(
            seed_params, weight1=1.0, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        population.append(var)

    pop_scores = [evaluate_params_on_set(c, scenarios).overall_score for c in population]
    if shuffle_fitness:
        rng.shuffle(pop_scores)

    best_score = max(pop_scores)
    best_params = population[pop_scores.index(best_score)]

    history = [best_score]

    selected_params = best_params
    best_validation_score = float("-inf")
    if validation_scenarios is not None:
        best_validation_score = evaluate_params_on_set(
            best_params, validation_scenarios
        ).overall_score

    if target_score_threshold is not None:
        gen0_gate_score = best_validation_score if validation_scenarios is not None else best_score
        if gen0_gate_score >= target_score_threshold:
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
        pop_scores = [best_score] + [
            evaluate_params_on_set(c, scenarios).overall_score for c in population[1:]
        ]
        if shuffle_fitness:
            rng.shuffle(pop_scores)

        gen_best = max(pop_scores)
        if gen_best > best_score:
            best_score = gen_best
            best_params = population[pop_scores.index(gen_best)]

        history.append(best_score)

        gate_score = best_score
        if validation_scenarios is not None:
            elite = population[pop_scores.index(max(pop_scores))]
            validation_score = evaluate_params_on_set(elite, validation_scenarios).overall_score
            gate_score = validation_score
            if validation_score > best_validation_score:
                best_validation_score = validation_score
                selected_params = elite

        if target_score_threshold is not None and gate_score >= target_score_threshold:
            return selected_params, history, gen

    return selected_params, history, generations


@dataclass(frozen=True)
class TransferStudyConfig:
    """Evolution/scenario budget for one transfer evaluation.

    The defaults reproduce the frozen CI benchmark budget exactly (see the
    module constants in target_memory_transfer_gym.py), so
    ``evaluate_target_memory_transfer(seed)`` is unchanged. Scaled-up budgets
    are the multi-run study's business (core/behavior/
    target_memory_transfer_study.py + scripts/run_target_memory_transfer_
    study.py); the CI benchmark must stay fast, so its budget is not raised
    here. ``None`` scenario counts mean "the generator's default set size".
    """

    population_size: int = POPULATION_SIZE
    generations: int = GENERATIONS
    evolution_runs: int = EVOLUTION_RUNS
    food_train_count: int | None = None
    food_validation_count: int | None = None
    ball_held_out_count: int | None = None
    ball_train_count: int | None = None
    ball_validation_count: int | None = None


def evaluate_target_memory_transfer(
    seed: int, config: TransferStudyConfig | None = None
) -> TargetMemoryTransferEvaluation:
    """Evolve populations over food scenarios; evaluate zero-shot and measure
    adaptation on ball scenarios, against a founder-default disjoint control."""
    cfg = config if config is not None else TransferStudyConfig()
    train_food = generate_scenario_set("train", seed, count=cfg.food_train_count)
    validation_food = generate_scenario_set("validation", seed, count=cfg.food_validation_count)
    test_ball = generate_scenario_set("held_out", seed, count=cfg.ball_held_out_count)
    train_ball = generate_scenario_set("ball_train", seed, count=cfg.ball_train_count)
    validation_ball = generate_scenario_set(
        "ball_validation", seed, count=cfg.ball_validation_count
    )

    default_params = TargetMemoryParams()
    summaries: dict[str, EvaluationSummary] = {}

    # Group 1: naive greedy (no memory at all)
    summaries["naive_greedy"] = evaluate_naive_greedy_on_set(test_ball)

    # Group 2: default/founder params - also the disjoint arm's zero-shot
    # baseline (a target_memory that food selection never touched).
    summaries["default_params"] = evaluate_params_on_set(default_params, test_ball)

    # Group 3: structurally matched no-selection control. Replaces v1's
    # random search (one-step mutations around the default), which was not
    # lineage-matched to the evolutionary arms: evolution explores cumulative
    # lineages through selection, crossover, and repeated mutation, so "does
    # food *selection* matter" needs a control with the same lineage depth,
    # operator mix, and compute but selection decoupled from genotype
    # (shuffled fitness). The difference between food_trained and this group
    # is then attributable to selection, not to mutation-walk drift.
    neutral_params = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 8000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            [default_params],
            train_food,
            cfg.generations,
            cfg.population_size,
            run_rng,
            shuffle_fitness=True,
        )
        neutral_params.append(best_of_run)
    summaries["neutral_evolution"] = average_summaries(
        [evaluate_params_on_set(p, test_ball) for p in neutral_params]
    )

    # Group 4: food-trained populations (shared arm's basis) - zero-shot on ball
    food_trained_params = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 9000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            [default_params],
            train_food,
            cfg.generations,
            cfg.population_size,
            run_rng,
            validation_scenarios=validation_food,
        )
        food_trained_params.append(best_of_run)

    food_evals = [evaluate_params_on_set(p, test_ball) for p in food_trained_params]
    summaries["food_trained"] = average_summaries(food_evals)

    # Group 5: ball-trained (task-specific reference)
    ball_trained_params = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 10000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            [default_params],
            train_ball,
            cfg.generations,
            cfg.population_size,
            run_rng,
            validation_scenarios=validation_ball,
        )
        ball_trained_params.append(best_of_run)

    ball_evals = [evaluate_params_on_set(p, test_ball) for p in ball_trained_params]
    summaries["ball_trained"] = average_summaries(ball_evals)

    # Adaptation speed: shared arm (continuing from food-trained values) vs
    # disjoint arm (starting from founder/default params - never touched by
    # food selection), both unfrozen under the same ball-domain training set
    # and budget. Training and selection happen on train_ball; the reference
    # bar and each generation's threshold check are measured on
    # validation_ball, so "generations to adapt" means generations until the
    # lineage *generalizes* to reference level, not until it fits the exact
    # training scenarios. test_ball (the zero-shot held-out set scored above)
    # must stay untouched from here on, or "adaptation speed" would just be
    # re-measuring fit to the same data already used to claim zero-shot
    # transfer.
    default_score_val = evaluate_params_on_set(default_params, validation_ball).overall_score
    ball_reference_val_scores = [
        evaluate_params_on_set(p, validation_ball).overall_score for p in ball_trained_params
    ]
    ball_reference_score = sum(ball_reference_val_scores) / len(ball_reference_val_scores)
    reference_gap = ball_reference_score - default_score_val

    if reference_gap < MIN_REFERENCE_EFFECT:
        # ball_trained didn't establish a meaningfully better-than-default
        # bar in-domain, so any threshold derived from it would be noise, not
        # a real target. Report the gap for diagnostics and skip the
        # generations-to-adapt runs rather than manufacture a near-zero bar.
        return TargetMemoryTransferEvaluation(
            group_summaries=summaries,
            adaptation_generations_food=None,
            adaptation_generations_default=None,
            adaptation_threshold=None,
            adaptation_reference_established=False,
            adaptation_reference_gap=reference_gap,
        )

    adaptation_threshold = default_score_val + reference_gap * 0.75

    # Both arms get paired but independent RNG streams per run (distinct
    # fixed salts, same run index), the same training set, the same budget,
    # and the same validation-measured bar - the starting population is the
    # only difference between them.
    adapt_runs_food = []
    adapt_runs_default = []
    for run_idx in range(cfg.evolution_runs):
        food_seed = food_trained_params[run_idx % len(food_trained_params)]
        initial_pop_shared = [food_seed] * cfg.population_size
        _, _, gens_shared = run_evolution(
            initial_pop_shared,
            train_ball,
            cfg.generations * 2,
            cfg.population_size,
            random.Random(seed + 11000 + run_idx * 100),
            target_score_threshold=adaptation_threshold,
            validation_scenarios=validation_ball,
        )
        adapt_runs_food.append(gens_shared)

        initial_pop_disjoint = [default_params] * cfg.population_size
        _, _, gens_disjoint = run_evolution(
            initial_pop_disjoint,
            train_ball,
            cfg.generations * 2,
            cfg.population_size,
            random.Random(seed + 12000 + run_idx * 100),
            target_score_threshold=adaptation_threshold,
            validation_scenarios=validation_ball,
        )
        adapt_runs_default.append(gens_disjoint)

    avg_gens_food = int(round(sum(adapt_runs_food) / len(adapt_runs_food)))
    avg_gens_default = int(round(sum(adapt_runs_default) / len(adapt_runs_default)))

    return TargetMemoryTransferEvaluation(
        group_summaries=summaries,
        adaptation_generations_food=avg_gens_food,
        adaptation_generations_default=avg_gens_default,
        adaptation_threshold=adaptation_threshold,
        adaptation_reference_established=True,
        adaptation_reference_gap=reference_gap,
    )
