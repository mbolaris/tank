"""Inheritance utilities for passing traits between generations.

This module provides low-level trait inheritance functions used by
the crossover operations. These handle the mechanics of combining
parent values for different trait types.

Inheritance in ALife follows biological principles:
- Continuous traits: Blend or select from parents
- Discrete traits: Mendelian-style selection
- Algorithms: Copy structure, blend parameters

The inheritance system does NOT include fitness-based selection.
Selection pressure comes from the environment - fish that inherit
good poker genes win more energy and reproduce more.
"""

import random
from typing import TYPE_CHECKING, Optional

from core.evolution.mutation import mutate_continuous_trait, mutate_discrete_trait

if TYPE_CHECKING:
    from core.algorithms.base import BehaviorAlgorithm
    from core.genetics import Genome


def inherit_trait(
    val1: float,
    val2: float,
    min_val: float,
    max_val: float,
    weight1: float = 0.5,
    mutation_rate: float = 0.1,
    mutation_strength: float = 0.1,
    rng: Optional[random.Random] = None,
) -> float:
    """Inherit a continuous trait from two parents.

    Combines weighted blending with mutation.

    Args:
        val1: First parent's value
        val2: Second parent's value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        weight1: Weight for first parent (0.0-1.0)
        mutation_rate: Probability of mutation
        mutation_strength: Magnitude of mutation
        rng: Random number generator

    Returns:
        Inherited value with possible mutation
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    weight2 = 1.0 - weight1

    # Weighted blend
    inherited = val1 * weight1 + val2 * weight2

    # Apply mutation
    inherited = mutate_continuous_trait(
        inherited, min_val, max_val, mutation_rate, mutation_strength, rng
    )

    return inherited


def inherit_discrete_trait(
    val1: int,
    val2: int,
    min_val: int,
    max_val: int,
    weight1: float = 0.5,
    mutation_rate: float = 0.1,
    rng: Optional[random.Random] = None,
) -> int:
    """Inherit a discrete trait from two parents.

    Selects one parent's value probabilistically, then may mutate.

    Args:
        val1: First parent's value
        val2: Second parent's value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        weight1: Probability of selecting first parent's value
        mutation_rate: Probability of mutation
        rng: Random number generator

    Returns:
        Inherited value with possible mutation
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    inherited = val1 if rng.random() < weight1 else val2

    # Apply mutation
    inherited = mutate_discrete_trait(inherited, min_val, max_val, mutation_rate, rng)

    return inherited


def inherit_algorithm(
    alg1: Optional["BehaviorAlgorithm"],
    alg2: Optional["BehaviorAlgorithm"],
    weight1: float = 0.5,
    mutation_rate: float = 0.15,
    mutation_strength: float = 0.2,
    algorithm_switch_rate: float = 0.05,
    rng: Optional[random.Random] = None,
) -> Optional["BehaviorAlgorithm"]:
    """Inherit a behavior algorithm from two parents.

    Algorithm inheritance is more complex than simple traits:
    1. If parents have same algorithm type: blend parameters
    2. If parents have different types: select one probabilistically
    3. Small chance of completely random new algorithm (novelty)

    Args:
        alg1: First parent's algorithm (can be None)
        alg2: Second parent's algorithm (can be None)
        weight1: Weight for first parent
        mutation_rate: Parameter mutation rate
        mutation_strength: Parameter mutation strength
        algorithm_switch_rate: Chance of random new algorithm
        rng: Random number generator

    Returns:
        Inherited algorithm with mutated parameters
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    from core.algorithms.registry import (
        crossover_algorithms_weighted,
        get_random_algorithm,
    )

    # Handle None cases
    if alg1 is None and alg2 is None:
        return get_random_algorithm(rng)

    # Check for random algorithm switch (novelty injection)
    if rng.random() < algorithm_switch_rate:
        return get_random_algorithm(rng)

    # Use the algorithms module's crossover
    return crossover_algorithms_weighted(
        alg1,
        alg2,
        parent1_weight=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        algorithm_switch_rate=algorithm_switch_rate,
        rng=rng,
    )
