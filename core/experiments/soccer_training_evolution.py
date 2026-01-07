"""Soccer training evolution experiment runner.

This module provides a deterministic, seeded experiment runner for evolving
soccer policies using the SoccerTrainingWorld. It runs generations of agents,
evaluates fitness, and selects/mutates genomes for the next generation.

Fitness Formula:
    fitness = total_team_energy + (goals_scored * goal_weight)

Energy-focused evolution ensures continuity with the tank evolution patterns
where survival (energy management) is the primary selection pressure.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from core.code_pool import GenomeCodePool, create_default_genome_code_pool
from core.genetics import Genome
from core.worlds.soccer_training.world import (
    LEFT_TEAM,
    RIGHT_TEAM,
    SoccerTrainingWorldBackendAdapter,
)


@dataclass
class AgentResult:
    """Results for a single agent after an episode."""

    player_id: str
    team: str
    goals: int
    energy: float
    fitness: float
    genome: Genome


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
    """Create initial population with random genomes.

    Args:
        rng: Seeded RNG for determinism
        population_size: Number of genomes to create
        genome_code_pool: Pool containing available soccer policies

    Returns:
        List of initialized Genome objects
    """
    population: list[Genome] = []

    # Get available soccer policies
    soccer_policy_ids = genome_code_pool.get_components_by_kind("soccer_policy")

    for _ in range(population_size):
        genome = Genome.random(use_algorithm=False, rng=rng)

        # Assign random soccer policy if available
        if soccer_policy_ids:
            policy_id = rng.choice(soccer_policy_ids)
            genome.behavioral.soccer_policy_id = genome.behavioral.soccer_policy_id.__class__(
                policy_id
            )

        population.append(genome)

    return population


def evaluate_population(
    population: list[Genome],
    seed: int,
    episode_frames: int,
    genome_code_pool: GenomeCodePool,
    goal_weight: float = 10.0,
) -> list[AgentResult]:
    """Evaluate all genomes by running soccer episodes.

    Each genome is assigned to a player, episodes are run, and fitness is computed.

    Args:
        population: List of genomes to evaluate
        seed: Seed for deterministic episode
        episode_frames: Number of frames per episode
        genome_code_pool: Pool for policy execution
        goal_weight: Weight for goals in fitness calculation

    Returns:
        List of AgentResult with fitness scores
    """
    # Create world with deterministic seed
    config: dict[str, Any] = {
        "team_size": max(1, len(population) // 2),
    }

    world = SoccerTrainingWorldBackendAdapter(
        seed=seed,
        genome_code_pool=genome_code_pool,
        **config,
    )

    # Reset to initialize field and players
    world.reset(seed=seed)

    # Assign genomes to players
    player_ids = list(world._players.keys())
    for i, genome in enumerate(population[: len(player_ids)]):
        if i < len(player_ids):
            player = world._players[player_ids[i]]
            player.genome = genome

    # Run episode
    for _ in range(episode_frames):
        world.step()

    # Collect results
    results: list[AgentResult] = []
    fitness_summary = world.get_fitness_summary()
    team_scores = fitness_summary.get("score", {})

    for player_id, player in world._players.items():
        agent_data = fitness_summary.get("agent_fitness", {}).get(player_id, {})
        goals = agent_data.get("goals", 0)
        energy = agent_data.get("energy", 0.0)

        # Fitness = energy + weighted goals
        fitness = energy + (goals * goal_weight)

        results.append(
            AgentResult(
                player_id=player_id,
                team=player.team,
                goals=goals,
                energy=energy,
                fitness=fitness,
                genome=player.genome,
            )
        )

    return results


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
    mutation_rate: float = 0.1,
) -> list[Genome]:
    """Create next generation via reproduction and mutation.

    Args:
        parents: Selected parent genomes
        population_size: Target size for next generation
        rng: Seeded RNG for determinism
        genome_code_pool: Pool for policy mutation
        mutation_rate: Rate of genome mutation (unused, kept for API compat)

    Returns:
        New population of genomes
    """
    next_gen: list[Genome] = []

    # Get available policies for mutation
    available_policies = genome_code_pool.get_components_by_kind("soccer_policy")

    # Elitism: keep best parent unchanged
    if parents:
        next_gen.append(parents[0])

    # Fill rest with mutated offspring
    while len(next_gen) < population_size:
        parent = rng.choice(parents) if parents else Genome.random(use_algorithm=False, rng=rng)

        # Clone with mutation using the correct API
        child = Genome.clone_with_mutation(
            parent,
            rng=rng,
            available_policies=available_policies or None,
        )
        next_gen.append(child)

    return next_gen[:population_size]


def run_generations(
    seed: int,
    generations: int = 10,
    population_size: int = 20,
    episode_frames: int = 300,
    top_k_selection: int = 5,
    goal_weight: float = 10.0,
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
        mutation_rate: Probability of mutation
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
                mutation_rate,
            )

    # Return result
    return EvolutionResult(
        generations=generation_stats,
        best_genome=best_overall_genome or Genome.random(use_algorithm=False, rng=rng),
        best_fitness=best_overall_fitness,
        final_seed=seed + (generations - 1) * 1000,
    )
