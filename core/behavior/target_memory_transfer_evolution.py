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


@dataclass
class TargetMemoryGenome:
    """Standalone evolutionary wrapper for TargetMemoryParams in the transfer gym assay.
    Carries its own heritable, evolvable mutation rate and strength (meta-genes),
    matching the semantics and bounds of GeneticTrait under live behavioral inheritance."""

    params: TargetMemoryParams
    mutation_rate: float = 1.0
    mutation_strength: float = 1.0

    def to_dict(self) -> dict[str, float]:
        d = self.params.to_dict()
        d["mutation_rate"] = self.mutation_rate
        d["mutation_strength"] = self.mutation_strength
        return d

    def crossed_over(
        self,
        other: TargetMemoryGenome,
        *,
        weight1: float,
        mutation_rate: float,
        mutation_strength: float,
        rng: random.Random,
    ) -> TargetMemoryGenome:
        from core.genetics.behavioral_inheritance import inherit_behavior_graph
        from core.genetics.trait import GeneticTrait

        t1 = GeneticTrait(
            self.params,
            mutation_rate=self.mutation_rate,
            mutation_strength=self.mutation_strength,
        )
        t2 = GeneticTrait(
            other.params,
            mutation_rate=other.mutation_rate,
            mutation_strength=other.mutation_strength,
        )

        child_trait = inherit_behavior_graph(
            t1,
            t2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        assert child_trait is not None

        return TargetMemoryGenome(
            params=child_trait.value,
            mutation_rate=child_trait.mutation_rate,
            mutation_strength=child_trait.mutation_strength,
        )


def run_evolution(
    initial_population: list[TargetMemoryGenome],
    scenarios: list[TargetMemoryScenario],
    generations: int,
    pop_size: int,
    rng: random.Random,
    target_score_threshold: float | None = None,
    validation_scenarios: list[TargetMemoryScenario] | None = None,
    shuffle_fitness: bool = False,
) -> tuple[TargetMemoryGenome, list[float], int]:
    """Run genetic algorithm over TargetMemoryGenome with optional validation
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
        seed_genome = population[rng.randrange(len(population))]
        var = seed_genome.crossed_over(
            seed_genome, weight1=1.0, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        population.append(var)

    pop_scores = [evaluate_params_on_set(c.params, scenarios).overall_score for c in population]
    if shuffle_fitness:
        rng.shuffle(pop_scores)

    best_score = max(pop_scores)
    best_genome = population[pop_scores.index(best_score)]

    history = [best_score]

    selected_genome = best_genome
    best_validation_score = float("-inf")
    if validation_scenarios is not None:
        best_validation_score = evaluate_params_on_set(
            best_genome.params, validation_scenarios
        ).overall_score

    if target_score_threshold is not None:
        gen0_gate_score = best_validation_score if validation_scenarios is not None else best_score
        if gen0_gate_score >= target_score_threshold:
            if shuffle_fitness:
                return population[rng.randrange(len(population))], history, 0
            return best_genome, history, 0

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
            evaluate_params_on_set(c.params, scenarios).overall_score for c in population[1:]
        ]
        if shuffle_fitness:
            rng.shuffle(pop_scores)

        gen_best = max(pop_scores)
        if gen_best > best_score:
            best_score = gen_best
            best_genome = population[pop_scores.index(gen_best)]

        history.append(best_score)

        gate_score = best_score
        if validation_scenarios is not None:
            elite = population[pop_scores.index(max(pop_scores))]
            validation_score = evaluate_params_on_set(
                elite.params, validation_scenarios
            ).overall_score
            gate_score = validation_score
            if validation_score > best_validation_score:
                best_validation_score = validation_score
                selected_genome = elite

        if target_score_threshold is not None and gate_score >= target_score_threshold:
            if shuffle_fitness:
                return population[rng.randrange(len(population))], history, gen
            return selected_genome, history, gen

    if shuffle_fitness:
        return population[rng.randrange(len(population))], history, generations

    if validation_scenarios is None:
        return best_genome, history, generations

    return selected_genome, history, generations


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


def generate_diverse_population(
    default_genome: TargetMemoryGenome,
    pop_size: int,
    rng: random.Random,
) -> list[TargetMemoryGenome]:
    """Initialize a diverse population by mutating the default genome."""
    population = [default_genome]
    while len(population) < pop_size:
        seed_genome = population[rng.randrange(len(population))]
        var = seed_genome.crossed_over(
            seed_genome, weight1=1.0, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        population.append(var)
    return population


def evaluate_target_memory_transfer(
    seed: int, config: TransferStudyConfig | None = None
) -> TargetMemoryTransferEvaluation:
    """Evolve populations over food scenarios; evaluate zero-shot and measure
    adaptation on ball scenarios, against a founder-default disjoint control."""
    cfg = config if config is not None else TransferStudyConfig()
    train_food = generate_scenario_set("train", seed, count=cfg.food_train_count)
    validation_food = generate_scenario_set("validation", seed, count=cfg.food_validation_count)
    test_food = generate_scenario_set(
        "food_held_out", seed, count=cfg.food_validation_count
    )  # food held-out set
    test_ball = generate_scenario_set("held_out", seed, count=cfg.ball_held_out_count)
    train_ball = generate_scenario_set("ball_train", seed, count=cfg.ball_train_count)
    validation_ball = generate_scenario_set(
        "ball_validation", seed, count=cfg.ball_validation_count
    )

    default_genome = TargetMemoryGenome(params=TargetMemoryParams())
    summaries: dict[str, EvaluationSummary] = {}
    summaries_food: dict[str, EvaluationSummary] = {}

    # Generate shared diverse founder populations for all runs
    shared_founders = []
    for run_idx in range(cfg.evolution_runs):
        init_rng = random.Random(seed + 7000 + run_idx * 100)
        pop = generate_diverse_population(default_genome, cfg.population_size, init_rng)
        shared_founders.append(pop)

    # Group 1: naive greedy (no memory at all)
    summaries["naive_greedy"] = evaluate_naive_greedy_on_set(test_ball)

    # Group 2: default/founder params reference
    summaries["default_params"] = evaluate_params_on_set(default_genome.params, test_ball)
    summaries_food["default_params"] = evaluate_params_on_set(default_genome.params, test_food)

    # Evaluate the starting founders on both sets
    all_founder_genomes = [g for pop in shared_founders for g in pop]
    summaries["founders"] = average_summaries(
        [evaluate_params_on_set(g.params, test_ball) for g in all_founder_genomes]
    )
    summaries_food["founders"] = average_summaries(
        [evaluate_params_on_set(g.params, test_food) for g in all_founder_genomes]
    )

    # Group 3: structurally matched no-selection control (neutral drift)
    neutral_genomes_list = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 8000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            shared_founders[run_idx],
            train_food,
            cfg.generations,
            cfg.population_size,
            run_rng,
            shuffle_fitness=True,
        )
        neutral_genomes_list.append(best_of_run)
    summaries["neutral_evolution"] = average_summaries(
        [evaluate_params_on_set(p.params, test_ball) for p in neutral_genomes_list]
    )
    summaries_food["neutral_evolution"] = average_summaries(
        [evaluate_params_on_set(p.params, test_food) for p in neutral_genomes_list]
    )

    # Group 4: food-trained populations (shared arm's basis) - zero-shot on ball
    food_trained_genomes_list = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 9000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            shared_founders[run_idx],
            train_food,
            cfg.generations,
            cfg.population_size,
            run_rng,
            validation_scenarios=validation_food,
        )
        food_trained_genomes_list.append(best_of_run)

    summaries["food_trained"] = average_summaries(
        [evaluate_params_on_set(p.params, test_ball) for p in food_trained_genomes_list]
    )
    summaries_food["food_trained"] = average_summaries(
        [evaluate_params_on_set(p.params, test_food) for p in food_trained_genomes_list]
    )

    # Group 5: ball-trained (task-specific reference)
    ball_trained_genomes_list = []
    for run_idx in range(cfg.evolution_runs):
        run_rng = random.Random(seed + 10000 + run_idx * 100)
        best_of_run, _, _ = run_evolution(
            shared_founders[run_idx],
            train_ball,
            cfg.generations,
            cfg.population_size,
            run_rng,
            validation_scenarios=validation_ball,
        )
        ball_trained_genomes_list.append(best_of_run)

    summaries["ball_trained"] = average_summaries(
        [evaluate_params_on_set(p.params, test_ball) for p in ball_trained_genomes_list]
    )
    summaries_food["ball_trained"] = average_summaries(
        [evaluate_params_on_set(p.params, test_food) for p in ball_trained_genomes_list]
    )

    # Adaptation speed: shared arm (continuing from food-trained values) vs
    # disjoint arm (starting from founder/default params - never touched by
    # food selection), both unfrozen under the same ball-domain training set
    # and budget. Training and selection happen on train_ball; the reference
    # bar and each generation's threshold check are measured on
    # validation_ball.
    default_score_val = evaluate_params_on_set(default_genome.params, validation_ball).overall_score
    ball_reference_val_scores = [
        evaluate_params_on_set(p.params, validation_ball).overall_score
        for p in ball_trained_genomes_list
    ]
    ball_reference_score = sum(ball_reference_val_scores) / len(ball_reference_val_scores)
    reference_gap = ball_reference_score - default_score_val

    # Calculate source domain validation performance
    food_val_score_default = evaluate_params_on_set(
        default_genome.params, validation_food
    ).overall_score
    food_val_scores_food_trained = [
        evaluate_params_on_set(p.params, validation_food).overall_score
        for p in food_trained_genomes_list
    ]
    food_val_score_food_trained = sum(food_val_scores_food_trained) / len(
        food_val_scores_food_trained
    )

    # Convert genomes/params to dicts for reporting
    food_trained_genomes = [p.to_dict() for p in food_trained_genomes_list]
    ball_trained_genomes = [p.to_dict() for p in ball_trained_genomes_list]
    founder_genomes = [p.to_dict() for p in all_founder_genomes]
    neutral_genomes = [p.to_dict() for p in neutral_genomes_list]

    if reference_gap < MIN_REFERENCE_EFFECT:
        return TargetMemoryTransferEvaluation(
            group_summaries=summaries,
            adaptation_generations_food=None,
            adaptation_generations_default=None,
            adaptation_threshold=None,
            adaptation_reference_established=False,
            adaptation_reference_gap=reference_gap,
            food_validation_score_default=food_val_score_default,
            food_validation_score_food_trained=food_val_score_food_trained,
            food_trained_genomes=food_trained_genomes,
            ball_trained_genomes=ball_trained_genomes,
            founder_genomes=founder_genomes,
            neutral_genomes=neutral_genomes,
            group_summaries_food=summaries_food,
        )

    adaptation_threshold = default_score_val + reference_gap * 0.75

    adapt_runs_food = []
    adapt_runs_default = []
    for run_idx in range(cfg.evolution_runs):
        food_seed = food_trained_genomes_list[run_idx % len(food_trained_genomes_list)]
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

        initial_pop_disjoint = [default_genome] * cfg.population_size
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
        food_validation_score_default=food_val_score_default,
        food_validation_score_food_trained=food_val_score_food_trained,
        food_trained_genomes=food_trained_genomes,
        ball_trained_genomes=ball_trained_genomes,
        founder_genomes=founder_genomes,
        neutral_genomes=neutral_genomes,
        group_summaries_food=summaries_food,
    )
