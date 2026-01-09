"""Soccer evolution experiment runner.

This module provides a deterministic, seeded experiment runner for evolving
soccer policies using the RCSS-Lite minigame engine. It runs generations of
agents, evaluates fitness, and selects/mutates genomes.

Fitness Formula:
    fitness = goals * 100 + assists * 50 + possessions * 0.1 + shaped_rewards
    (Shaped rewards include distance to ball, shot quality, and stamina efficiency)
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from core.code_pool import GenomeCodePool, create_default_genome_code_pool
from core.genetics import Genome
from core.genetics.code_policy_traits import assign_random_policy, mutate_code_policies
from core.minigames.soccer import AgentResult, SoccerMatchRunner

LEFT_TEAM = "left"
RIGHT_TEAM = "right"


@dataclass
class GenerationStats:
    """Statistics for a single generation."""

    generation: int
    best_fitness: float
    mean_fitness: float
    best_genome_id: str
    population_size: int
    goals_left: int
    goals_right: int


@dataclass
class EvolutionResult:
    """Final result of an evolution run."""

    generations: list[GenerationStats]
    best_genome: Genome
    best_fitness: float
    final_seed: int


def create_population(
    rng: random.Random,
    population_size: int,
    genome_code_pool: GenomeCodePool,
) -> list[Genome]:
    """Create initial population with random genomes and soccer policies.

    Args:
        rng: Seeded RNG for determinism
        population_size: Number of genomes to create
        genome_code_pool: Pool containing available soccer policies

    Returns:
        List of initialized Genome objects with soccer policies assigned
    """
    population: list[Genome] = []

    for _ in range(population_size):
        genome = Genome.random(use_algorithm=False, rng=rng)

        # Assign default soccer policy for Gen0 (functional baseline)
        # This ensures all initial agents can actually play soccer
        default_id = genome_code_pool.get_default("soccer_policy")
        if default_id:
            from core.genetics.trait import GeneticTrait

            genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
            genome.behavioral.soccer_policy_params = GeneticTrait({})
        else:
            # Fallback: assign random if no default (shouldn't happen)
            assign_random_policy(genome.behavioral, genome_code_pool, "soccer_policy", rng)

        population.append(genome)

    return population


def evaluate_population(
    population: list[Genome],
    seed: int,
    episode_frames: int,
    genome_code_pool: GenomeCodePool,
    goal_weight: float = 100.0,
    possession_weight: float = 0.1,
) -> list[AgentResult]:
    """Evaluate all genomes by running soccer episodes using RCSS-Lite engine.

    Args:
        population: List of genomes to evaluate
        seed: Seed for deterministic episode
        episode_frames: Number of frames per episode
        genome_code_pool: Pool for policy execution
        goal_weight: Weight for goals in fitness
        possession_weight: Weight for possession in fitness

    Returns:
        List of AgentResult with fitness scores
    """
    # Create match runner with deterministic seed
    team_size = max(1, len(population) // 2)

    runner = SoccerMatchRunner(
        team_size=team_size,
        genome_code_pool=genome_code_pool,
    )

    # Run episode and get results
    _episode_result, agent_results = runner.run_episode(
        genomes=population,
        seed=seed,
        frames=episode_frames,
        goal_weight=goal_weight,
    )

    return agent_results


def select_parents(
    results: list[AgentResult],
    top_k: int,
) -> list[Genome]:
    """Select top-performing genomes as parents for next generation.

    Uses truncation selection: take top K by fitness.

    Args:
        results: Evaluation results sorted by fitness
        top_k: Number of top performers to select

    Returns:
        List of parent genomes
    """
    # Sort by fitness descending
    sorted_results = sorted(results, key=lambda r: r.fitness, reverse=True)
    return [r.genome for r in sorted_results[:top_k]]


def create_next_generation(
    parents: list[Genome],
    population_size: int,
    rng: random.Random,
    genome_code_pool: GenomeCodePool,
) -> list[Genome]:
    """Create next generation via reproduction and pool-aware mutation.

    Uses mutate_code_policies() for proper per-kind mutation instead of
    the flat available_policies approach.

    Args:
        parents: Selected parent genomes
        population_size: Target size for next generation
        rng: Seeded RNG for determinism
        genome_code_pool: Pool for policy mutation

    Returns:
        New population of genomes
    """
    next_gen: list[Genome] = []

    # Elitism: keep best parent unchanged
    if parents:
        next_gen.append(parents[0])

    # Fill rest with mutated offspring
    while len(next_gen) < population_size:
        parent = rng.choice(parents) if parents else Genome.random(use_algorithm=False, rng=rng)

        # Clone and apply pool-aware mutation
        child = Genome.clone_with_mutation(parent, rng=rng)

        # Apply pool-aware mutation to code policies (soccer-specific)
        mutate_code_policies(child.behavioral, genome_code_pool, rng)

        # Ensure child has a soccer policy
        if child.behavioral.soccer_policy_id.value is None:
            assign_random_policy(child.behavioral, genome_code_pool, "soccer_policy", rng)

        next_gen.append(child)

    return next_gen[:population_size]


def run_generations(
    seed: int,
    generations: int = 10,
    population_size: int = 20,
    episode_frames: int = 300,
    top_k_selection: int = 5,
    goal_weight: float = 100.0,
    mutation_rate: float = 0.1,
    verbose: bool = False,
) -> EvolutionResult:
    """Run deterministic soccer evolution experiment.

    Args:
        seed: Initial random seed for reproducibility
        generations: Number of generations to run
        population_size: Size of each generation
        episode_frames: Frames per evaluation episode
        top_k_selection: Number of top performers to select as parents
        goal_weight: Weight for goals in fitness calculation
        mutation_rate: Probability of mutation (unused, for API compat)
        verbose: If True, print per-generation progress

    Returns:
        EvolutionResult with all generation stats and best genome
    """
    rng = random.Random(seed)
    genome_code_pool = create_default_genome_code_pool()

    # Initialize population
    population = create_population(rng, population_size, genome_code_pool)

    generation_stats: list[GenerationStats] = []
    best_overall_genome: Genome | None = None
    best_overall_fitness = float("-inf")

    for gen in range(generations):
        # Evaluate using a deterministic seed derived from generation
        eval_seed = seed + gen * 1000
        results = evaluate_population(
            population,
            seed=eval_seed,
            episode_frames=episode_frames,
            genome_code_pool=genome_code_pool,
            goal_weight=goal_weight,
        )

        # Calculate stats
        fitnesses = [r.fitness for r in results]
        best_fitness = max(fitnesses) if fitnesses else 0.0
        mean_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0

        # Find best agent
        best_agent = max(results, key=lambda r: r.fitness) if results else None
        best_id = best_agent.player_id if best_agent else ""

        # Track overall best
        if best_agent and best_agent.fitness > best_overall_fitness:
            best_overall_fitness = best_agent.fitness
            best_overall_genome = best_agent.genome

        # Calculate team goals
        goals_left = sum(r.goals for r in results if r.team == LEFT_TEAM)
        goals_right = sum(r.goals for r in results if r.team == RIGHT_TEAM)

        stats = GenerationStats(
            generation=gen,
            best_fitness=best_fitness,
            mean_fitness=mean_fitness,
            best_genome_id=best_id,
            population_size=len(population),
            goals_left=goals_left,
            goals_right=goals_right,
        )
        generation_stats.append(stats)

        if verbose:
            print(
                f"Gen {gen}: best={best_fitness:.2f}, mean={mean_fitness:.2f}, "
                f"goals L/R={goals_left}/{goals_right}"
            )

        # Select and reproduce (except on last generation)
        if gen < generations - 1:
            parents = select_parents(results, top_k_selection)
            population = create_next_generation(
                parents,
                population_size,
                rng,
                genome_code_pool,
            )

    # Return result
    return EvolutionResult(
        generations=generation_stats,
        best_genome=best_overall_genome or Genome.random(use_algorithm=False, rng=rng),
        best_fitness=best_overall_fitness,
        final_seed=seed + (generations - 1) * 1000,
    )
