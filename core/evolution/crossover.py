"""Crossover operations for combining parent genomes.

Sexual reproduction in ALife: two successful organisms combine their genes.
The key insight is that BOTH parents survived and reproduced - that's the
only "selection" happening. There's no explicit fitness comparison.

Crossover Modes:
- AVERAGING: Blend parent values (smooth, conservative)
- RECOMBINATION: Pick genes from each parent (more variation)
- WEIGHTED: One parent contributes more (e.g., poker winner)

The weighted mode is particularly important for poker evolution:
when fish reproduce after poker, the winner contributes more DNA,
creating selection pressure for poker skill without explicit fitness.
"""

import random
from enum import Enum
from typing import Optional


class CrossoverMode(Enum):
    """Methods for combining parent genetic values."""
    
    AVERAGING = "averaging"
    """Simple average of parent values. Most conservative."""
    
    RECOMBINATION = "recombination"
    """Randomly select from each parent with some blending."""
    
    WEIGHTED = "weighted"
    """Weighted combination based on parent contributions."""


def blend_values(
    val1: float,
    val2: float,
    weight1: float = 0.5,
    mode: CrossoverMode = CrossoverMode.RECOMBINATION,
    rng: Optional[random.Random] = None,
) -> float:
    """Blend two parent values using the specified crossover mode.
    
    Args:
        val1: First parent's value
        val2: Second parent's value
        weight1: Weight for first parent (0.0-1.0), second gets (1-weight1)
        mode: Crossover mode to use
        rng: Random number generator
    
    Returns:
        Blended value
    """
    rng = rng or random
    weight2 = 1.0 - weight1
    
    if mode == CrossoverMode.AVERAGING:
        # Simple average (ignores weights)
        return (val1 + val2) * 0.5
    
    elif mode == CrossoverMode.RECOMBINATION:
        # Random selection with some blending
        if rng.random() < 0.5:
            # Pick one parent's value
            return val1 if rng.random() < 0.5 else val2
        else:
            # Blend with some randomness
            return val1 * 0.7 + val2 * 0.15 + (val1 + val2) * 0.075
    
    elif mode == CrossoverMode.WEIGHTED:
        # Weighted average based on parent contribution
        return val1 * weight1 + val2 * weight2
    
    # Default to averaging
    return (val1 + val2) * 0.5


def blend_discrete(
    val1: int,
    val2: int,
    weight1: float = 0.5,
    rng: Optional[random.Random] = None,
) -> int:
    """Blend two discrete parent values (probabilistic selection).
    
    For discrete traits like template_id, we can't average.
    Instead, we select one parent's value with probability
    proportional to their weight.
    
    Args:
        val1: First parent's value
        val2: Second parent's value
        weight1: Probability of selecting first parent's value
        rng: Random number generator
    
    Returns:
        Selected value (either val1 or val2)
    """
    rng = rng or random
    return val1 if rng.random() < weight1 else val2


def crossover_dict_values(
    dict1: dict[str, float],
    dict2: dict[str, float],
    weight1: float = 0.5,
    mode: CrossoverMode = CrossoverMode.WEIGHTED,
    rng: Optional[random.Random] = None,
) -> dict[str, float]:
    """Crossover two dictionaries of float values (e.g., algorithm parameters).
    
    Handles keys that exist in one parent but not the other.
    
    Args:
        dict1: First parent's dictionary
        dict2: Second parent's dictionary
        weight1: Weight for first parent
        mode: Crossover mode
        rng: Random number generator
    
    Returns:
        Blended dictionary
    """
    rng = rng or random
    result = {}
    
    # Get all keys from both parents
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        if key in dict1 and key in dict2:
            # Both parents have this key - blend
            result[key] = blend_values(dict1[key], dict2[key], weight1, mode, rng)
        elif key in dict1:
            # Only first parent has this key
            result[key] = dict1[key]
        else:
            # Only second parent has this key
            result[key] = dict2[key]
    
    return result


def crossover_genomes(
    parent1_genome: "Genome",
    parent2_genome: "Genome",
    mutation_rate: float = 0.1,
    mutation_strength: float = 0.1,
    population_stress: float = 0.0,
    mode: CrossoverMode = CrossoverMode.RECOMBINATION,
) -> "Genome":
    """Create offspring genome by crossing two parent genomes.
    
    This is a convenience wrapper that delegates to Genome.from_parents().
    
    Args:
        parent1_genome: First parent's genome
        parent2_genome: Second parent's genome
        mutation_rate: Base mutation rate
        mutation_strength: Base mutation strength
        population_stress: Environmental stress (0.0-1.0)
        mode: Crossover mode
    
    Returns:
        New offspring genome
    """
    # Import here to avoid circular dependency
    from core.genetics import Genome, GeneticCrossoverMode
    
    # Map our mode to genetics module mode
    genetics_mode = {
        CrossoverMode.AVERAGING: GeneticCrossoverMode.AVERAGING,
        CrossoverMode.RECOMBINATION: GeneticCrossoverMode.RECOMBINATION,
        CrossoverMode.WEIGHTED: GeneticCrossoverMode.AVERAGING,  # Weighted uses from_parents_weighted
    }.get(mode, GeneticCrossoverMode.RECOMBINATION)
    
    return Genome.from_parents(
        parent1_genome,
        parent2_genome,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        population_stress=population_stress,
        crossover_mode=genetics_mode,
    )


def crossover_genomes_weighted(
    parent1_genome: "Genome",
    parent2_genome: "Genome",
    parent1_weight: float = 0.5,
    mutation_rate: float = 0.1,
    mutation_strength: float = 0.1,
    population_stress: float = 0.0,
) -> "Genome":
    """Create offspring genome with weighted parent contributions.
    
    Used for post-poker reproduction where the winner contributes
    more genetic material.
    
    Args:
        parent1_genome: First parent's genome (e.g., poker winner)
        parent2_genome: Second parent's genome (e.g., poker loser)
        parent1_weight: How much parent1 contributes (0.0-1.0)
        mutation_rate: Base mutation rate
        mutation_strength: Base mutation strength
        population_stress: Environmental stress (0.0-1.0)
    
    Returns:
        New offspring genome with weighted inheritance
    """
    # Import here to avoid circular dependency
    from core.genetics import Genome
    
    return Genome.from_parents_weighted(
        parent1_genome,
        parent2_genome,
        parent1_weight=parent1_weight,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        population_stress=population_stress,
    )
