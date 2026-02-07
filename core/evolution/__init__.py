"""Evolution module for artificial life simulation.

This module provides genetic operations for the ALife simulation. Unlike genetic
algorithms, there is NO explicit fitness function - selection pressure emerges
naturally from the environment:

- Fish that find food survive longer
- Fish that win poker games gain energy and reproduce more
- Fish with good genes pass them to offspring
- Poor performers die and their genes leave the population

**Canonical API** (use these in production code):
- `Genome.from_parents()` - standard crossover between two parents
- `Genome.from_parents_weighted()` - weighted crossover (e.g., poker winner)
- `Genome.from_parents_weighted_params()` - weighted crossover with params object

Submodules:
- mutation: Random variations in offspring (adaptive bounds, continuous/discrete)
- crossover: Value blending utilities (internal/testing use)
- inheritance: Trait passing between generations

Design Philosophy (ALife vs GA):
- NO fitness function evaluation
- NO tournament selection
- NO explicit optimization target
- Selection emerges from survival and reproduction success
"""

from core.evolution.crossover import CrossoverMode
from core.evolution.inheritance import (inherit_algorithm,
                                        inherit_discrete_trait, inherit_trait)
from core.evolution.mutation import (DEFAULT_MUTATION_CONFIG, MutationConfig,
                                     calculate_adaptive_mutation_rate,
                                     mutate_continuous_trait,
                                     mutate_discrete_trait)

__all__ = [
    # Crossover
    "CrossoverMode",
    # Mutation
    "mutate_continuous_trait",
    "mutate_discrete_trait",
    "calculate_adaptive_mutation_rate",
    "MutationConfig",
    "DEFAULT_MUTATION_CONFIG",
    # Inheritance
    "inherit_trait",
    "inherit_discrete_trait",
    "inherit_algorithm",
]
