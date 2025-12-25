"""Factory and registry for poker strategies."""

import random
from typing import List, Optional, Type

from core.poker.strategy.implementations.base import PokerStrategyAlgorithm
from core.poker.strategy.implementations.standard import (
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    TightPassiveStrategy,
    BalancedStrategy,
    ManiacStrategy,
    LoosePassiveStrategy,
)
from core.poker.strategy.implementations.advanced import (
    AdaptiveStrategy,
    PositionalExploiter,
    TrapSetterStrategy,
    MathematicalStrategy,
)
from core.poker.strategy.implementations.expert import GTOExpertStrategy
from core.poker.strategy.implementations.baseline import (
    AlwaysFoldStrategy,
    RandomStrategy,
)

# Registry of all EVOLVING strategy classes
ALL_POKER_STRATEGIES: List[Type[PokerStrategyAlgorithm]] = [
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    TightPassiveStrategy,
    LoosePassiveStrategy,
    BalancedStrategy,
    ManiacStrategy,
    # Advanced strategies for more diversity
    AdaptiveStrategy,
    PositionalExploiter,
    TrapSetterStrategy,
    MathematicalStrategy,
]

# Baseline strategies for benchmarking (not included in evolution pool)
BASELINE_STRATEGIES: List[Type[PokerStrategyAlgorithm]] = [
    AlwaysFoldStrategy,
    RandomStrategy,
    TightPassiveStrategy,  # "Rock" - also useful as baseline
    LoosePassiveStrategy,  # "Calling Station" - also useful as baseline
    GTOExpertStrategy,     # Expert baseline
]

def get_all_poker_strategies() -> List[Type[PokerStrategyAlgorithm]]:
    """Get list of all evolving poker strategy classes."""
    return ALL_POKER_STRATEGIES

def get_random_poker_strategy(rng: Optional[random.Random] = None) -> PokerStrategyAlgorithm:
    """Get random poker strategy.
    
    Args:
        rng: Random number generator. If None, creates a new Random() instance.
    """
    _rng = rng if rng is not None else random
    cls = _rng.choice(ALL_POKER_STRATEGIES)
    try:
        return cls.random_instance(rng=_rng)
    except TypeError:
        return cls.random_instance()


# Configuration flags for poker evolution tuning
POKER_EVOLUTION_CONFIG = {
    # Novelty injection rate: chance of completely random strategy
    # Lower = more exploitation of evolved strategies, Higher = more exploration
    # Set very low to preserve evolved adaptations across generations
    "novelty_injection_rate": 0.005,  # REDUCED from 0.02 to minimize genetic drift
    # Rate when parents have different strategy types
    "different_type_novelty_rate": 0.01,  # REDUCED from 0.05 to preserve winning types
    # Default mutation parameters - reduced for more stable evolution
    "default_mutation_rate": 0.08,  # REDUCED from 0.12 for stability
    "default_mutation_strength": 0.10,  # REDUCED from 0.15 for stability
    # Enable winner-biased inheritance (parent1 = winner when True)
    "winner_biased_inheritance": True,
    # Default winner weight when winner_biased_inheritance is True
    "default_winner_weight": 0.85,  # INCREASED from 0.80 - winner contributes 85%
}


def crossover_poker_strategies(
    parent1: Optional["PokerStrategyAlgorithm"],
    parent2: Optional["PokerStrategyAlgorithm"],
    mutation_rate: float = None,
    mutation_strength: float = None,
    winner_weight: float = None,
) -> "PokerStrategyAlgorithm":
    """Crossover two poker strategies with winner-biased inheritance.

    This function creates offspring poker strategies by combining two parent
    strategies. When winner_weight is provided (or winner_biased_inheritance
    is enabled), parent1 is assumed to be the winner and contributes more
    genetic material.

    Supports both monolithic strategies (TAG, LAG, etc.) and ComposablePokerStrategy.

    Args:
        parent1: First parent strategy (winner in winner-biased mode)
        parent2: Second parent strategy (loser in winner-biased mode)
        mutation_rate: Probability of mutating each parameter (0.0-1.0)
        mutation_strength: Standard deviation of Gaussian mutation
        winner_weight: How much parent1 (winner) contributes (0.0-1.0, default 0.8)

    Returns:
        New offspring poker strategy
    """
    # Handle ComposablePokerStrategy crossover
    from core.poker.strategy.composable import ComposablePokerStrategy

    if isinstance(parent1, ComposablePokerStrategy) and isinstance(parent2, ComposablePokerStrategy):
        cfg = POKER_EVOLUTION_CONFIG
        if mutation_rate is None:
            mutation_rate = cfg["default_mutation_rate"]
        if mutation_strength is None:
            mutation_strength = cfg["default_mutation_strength"]
        if winner_weight is None:
            winner_weight = cfg["default_winner_weight"] if cfg["winner_biased_inheritance"] else 0.5
        return ComposablePokerStrategy.from_parents(
            parent1, parent2,
            weight1=winner_weight,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )

    # If one is composable and other is not, prefer composable offspring
    if isinstance(parent1, ComposablePokerStrategy):
        return parent1.clone_with_mutation(mutation_rate or 0.10, mutation_strength or 0.12)
    if isinstance(parent2, ComposablePokerStrategy):
        return parent2.clone_with_mutation(mutation_rate or 0.10, mutation_strength or 0.12)

    # Legacy crossover for monolithic strategies
    cfg = POKER_EVOLUTION_CONFIG

    # Use config defaults if not provided
    if mutation_rate is None:
        mutation_rate = cfg["default_mutation_rate"]
    if mutation_strength is None:
        mutation_strength = cfg["default_mutation_strength"]
    if winner_weight is None:
        winner_weight = cfg["default_winner_weight"] if cfg["winner_biased_inheritance"] else 0.5

    # Clamp winner_weight to valid range
    winner_weight = max(0.0, min(1.0, winner_weight))

    # Novelty injection: small chance of completely random strategy
    # This maintains diversity but at a lower rate to preserve adaptations
    # Note: Use parent RNG if available, otherwise use global random
    crossover_rng = parent1._rng if parent1 is not None else (
        parent2._rng if parent2 is not None else random
    )
    
    if crossover_rng.random() < cfg["novelty_injection_rate"]:
        return get_random_poker_strategy(rng=crossover_rng)

    if parent1 is None and parent2 is None:
        return get_random_poker_strategy(rng=crossover_rng)
    elif parent1 is None:
        offspring = parent2.__class__(rng=parent2._rng)
        offspring.parameters = parent2.parameters.copy()
    elif parent2 is None:
        offspring = parent1.__class__(rng=parent1._rng)
        offspring.parameters = parent1.parameters.copy()
    else:
        same_type = type(parent1) is type(parent2)
        if same_type:
            # Same strategy type: blend parameters with winner-biased weighting
            offspring = parent1.__class__(rng=parent1._rng)
            for param_key in parent1.parameters:
                if param_key in parent2.parameters:
                    # Use winner-biased weighted average
                    # winner_weight determines parent1's contribution
                    offspring.parameters[param_key] = (
                        parent1.parameters[param_key] * winner_weight +
                        parent2.parameters[param_key] * (1.0 - winner_weight)
                    )
                else:
                    offspring.parameters[param_key] = parent1.parameters[param_key]
        else:
            # Different strategy types: prefer winner's type
            if crossover_rng.random() < cfg["different_type_novelty_rate"]:
                # Reduced novelty injection for different types
                offspring = get_random_poker_strategy(rng=crossover_rng)
            elif crossover_rng.random() < winner_weight:
                # Winner-biased selection: prefer winner's (parent1) strategy type
                offspring = parent1.__class__()
                offspring.parameters = parent1.parameters.copy()
            else:
                # Loser's strategy type selected
                offspring = parent2.__class__()
                offspring.parameters = parent2.parameters.copy()

    offspring.mutate_parameters(mutation_rate, mutation_strength)
    return offspring
