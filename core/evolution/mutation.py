"""Mutation operations for genetic variation.

Mutations introduce random variation into offspring, enabling exploration of
the trait space. In ALife, mutations are the source of novelty - the environment
then naturally selects which variations survive.

Mutation Types:
- Continuous traits: Gaussian perturbation (speed, size, aggression)
- Discrete traits: Random shift (template_id, pattern_type)
- Algorithms: Parameter mutation or complete algorithm switch

Adaptive Mutation:
- Population stress increases mutation rate (more exploration when struggling)
- This is NOT fitness-based - it's environmental pressure response
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MutationConfig:
    """Configuration for mutation operations.

    These values can be tuned to control the pace of evolution.
    Higher rates = faster change, potentially less stable.
    Lower rates = slower adaptation, more stable populations.

    TUNED FOR FASTER EVOLUTION: Increased base rates and algorithm switch rate
    to accelerate adaptation, especially for food hunting and poker skills.
    """

    # Base mutation rates (INCREASED for faster evolution)
    # Base mutation rates (reduced for more stability)
    base_rate: float = 0.08  # 8% chance per trait
    base_strength: float = 0.06  # Gaussian std dev as fraction of range

    # Adaptive mutation bounds (narrower for stability)
    min_rate: float = 0.04  # Never mutate less than 4%
    max_rate: float = 0.25  # Never mutate more than 25%
    min_strength: float = 0.03
    max_strength: float = 0.15

    # Population stress multipliers (reduced to limit adaptive spikes)
    stress_rate_multiplier: float = 1.5
    stress_strength_multiplier: float = 1.3

    # Algorithm mutation (INCREASED for more behavioral diversity)
    algorithm_switch_rate: float = 0.04  # 4% chance of completely new algorithm


# Default configuration
DEFAULT_MUTATION_CONFIG = MutationConfig()


def calculate_adaptive_mutation_rate(
    base_rate: float,
    base_strength: float,
    population_stress: float = 0.0,
    config: Optional[MutationConfig] = None,
) -> Tuple[float, float]:
    """Calculate mutation rate and strength based on population stress.

    Population stress is NOT fitness - it's environmental pressure:
    - Low population relative to carrying capacity
    - High recent death rate
    - Resource scarcity

    When stressed, populations need more variation to adapt.

    Args:
        base_rate: Base mutation rate (0.0-1.0)
        base_strength: Base mutation strength (0.0-1.0)
        population_stress: Environmental stress level (0.0-1.0)
        config: Mutation configuration (uses default if None)

    Returns:
        Tuple of (adaptive_rate, adaptive_strength)
    """
    cfg = config or DEFAULT_MUTATION_CONFIG

    # Calculate stress factor (1.0 = no change, higher = more mutation)
    stress_factor = 1.0 + population_stress * cfg.stress_rate_multiplier
    strength_factor = 1.0 + population_stress * cfg.stress_strength_multiplier

    # Apply factors and clamp to bounds
    adaptive_rate = base_rate * stress_factor
    adaptive_rate = max(cfg.min_rate, min(cfg.max_rate, adaptive_rate))

    adaptive_strength = base_strength * strength_factor
    adaptive_strength = max(cfg.min_strength, min(cfg.max_strength, adaptive_strength))

    return adaptive_rate, adaptive_strength


def mutate_continuous_trait(
    value: float,
    min_val: float,
    max_val: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: Optional[random.Random] = None,
) -> float:
    """Mutate a continuous trait value with Gaussian noise.

    Args:
        value: Current trait value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        mutation_rate: Probability of mutation (0.0-1.0)
        mutation_strength: Standard deviation of Gaussian noise
        rng: Random number generator (uses global if None)

    Returns:
        Mutated value, clamped to [min_val, max_val]
    """
    rng = rng or random

    if rng.random() < mutation_rate:
        # Apply Gaussian mutation
        value += rng.gauss(0, mutation_strength)

    # Clamp to valid range
    return max(min_val, min(max_val, value))


def mutate_discrete_trait(
    value: int,
    min_val: int,
    max_val: int,
    mutation_rate: float,
    rng: Optional[random.Random] = None,
) -> int:
    """Mutate a discrete trait value by random shift.

    Args:
        value: Current trait value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        mutation_rate: Probability of mutation (0.0-1.0)
        rng: Random number generator (uses global if None)

    Returns:
        Mutated value, clamped to [min_val, max_val]
    """
    rng = rng or random

    if rng.random() < mutation_rate:
        # Shift by -1, 0, or +1
        value += rng.choice([-1, 0, 1])

    return max(min_val, min(max_val, value))


def should_switch_algorithm(
    mutation_rate: float,
    config: Optional[MutationConfig] = None,
    rng: Optional[random.Random] = None,
) -> bool:
    """Determine if an algorithm should be completely replaced.

    Occasionally, offspring get a completely random algorithm instead
    of inheriting from parents. This maintains diversity.

    Args:
        mutation_rate: Current adaptive mutation rate
        config: Mutation configuration
        rng: Random number generator

    Returns:
        True if algorithm should be replaced with random one
    """
    cfg = config or DEFAULT_MUTATION_CONFIG
    rng = rng or random

    # Higher base mutation rate slightly increases switch chance
    effective_rate = cfg.algorithm_switch_rate * (1 + mutation_rate)

    return rng.random() < effective_rate
