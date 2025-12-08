"""Behavioral traits for fish genomes.

This module defines behavioral characteristics that affect how fish act,
including aggression, social tendencies, and algorithm selection.
"""

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from core.genetics.trait import GeneticTrait, TraitSpec, inherit_traits_from_specs
from core.evolution.inheritance import inherit_algorithm, inherit_trait as _inherit_trait

if TYPE_CHECKING:
    from core.algorithms import BehaviorAlgorithm
    from core.poker.strategy.implementations import PokerStrategyAlgorithm


# Declarative specifications for behavioral traits (numeric only)
# Algorithms are handled separately since they're not simple values
BEHAVIORAL_TRAIT_SPECS: List[TraitSpec] = [
    TraitSpec("aggression", 0.0, 1.0),
    TraitSpec("social_tendency", 0.0, 1.0),
    TraitSpec("pursuit_aggression", 0.0, 1.0),
    TraitSpec("prediction_skill", 0.0, 1.0),
    TraitSpec("hunting_stamina", 0.0, 1.0),
    TraitSpec("asexual_reproduction_chance", 0.0, 1.0),
]


@dataclass
class BehavioralTraits:
    """Behavioral attributes of a fish.

    These traits affect decision-making, social behavior, and AI strategies.
    """

    # Numeric behavioral traits
    aggression: GeneticTrait[float]
    social_tendency: GeneticTrait[float]
    pursuit_aggression: GeneticTrait[float]
    prediction_skill: GeneticTrait[float]
    hunting_stamina: GeneticTrait[float]
    asexual_reproduction_chance: GeneticTrait[float]

    # Algorithm traits (special handling for complex objects)
    behavior_algorithm: GeneticTrait[Optional["BehaviorAlgorithm"]]
    poker_algorithm: GeneticTrait[Optional["BehaviorAlgorithm"]]
    poker_strategy_algorithm: GeneticTrait[Optional["PokerStrategyAlgorithm"]]

    # Mate preferences (dictionary trait)
    mate_preferences: GeneticTrait[Dict[str, float]]

    @classmethod
    def random(
        cls, rng: pyrandom.Random, use_algorithm: bool = True
    ) -> "BehavioralTraits":
        """Generate random behavioral traits."""
        # Generate numeric traits from specs
        traits = {spec.name: spec.random_value(rng) for spec in BEHAVIORAL_TRAIT_SPECS}

        # Generate algorithms
        algorithm = None
        poker_algorithm = None
        poker_strategy_algorithm = None

        if use_algorithm:
            from core.algorithms import get_random_algorithm
            from core.poker.strategy.implementations import get_random_poker_strategy

            algorithm = get_random_algorithm(rng=rng)
            poker_algorithm = get_random_algorithm(rng=rng)
            poker_strategy_algorithm = get_random_poker_strategy(rng=rng)

        traits["behavior_algorithm"] = GeneticTrait(algorithm)
        traits["poker_algorithm"] = GeneticTrait(poker_algorithm)
        traits["poker_strategy_algorithm"] = GeneticTrait(poker_strategy_algorithm)
        traits["mate_preferences"] = GeneticTrait(
            {
                "prefer_similar_size": 0.5,
                "prefer_different_color": 0.5,
                "prefer_high_energy": 0.5,
            }
        )

        return cls(**traits)

    @classmethod
    def from_parents(
        cls,
        parent1: "BehavioralTraits",
        parent2: "BehavioralTraits",
        *,
        weight1: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: pyrandom.Random,
    ) -> "BehavioralTraits":
        """Inherit behavioral traits from two parents.

        Args:
            parent1: First parent's behavioral traits (winner in winner-biased mode)
            parent2: Second parent's behavioral traits (loser in winner-biased mode)
            weight1: How much parent1 contributes (0.0-1.0). In winner-biased mode,
                     this is typically 0.8 for the poker winner.
            mutation_rate: Base mutation probability
            mutation_strength: Mutation magnitude
            rng: Random number generator
        """
        # Inherit numeric traits using specs
        inherited = inherit_traits_from_specs(
            BEHAVIORAL_TRAIT_SPECS,
            parent1,
            parent2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )

        # Inherit algorithms with special handling
        algo_val = inherit_algorithm(
            parent1.behavior_algorithm.value,
            parent2.behavior_algorithm.value,
            weight1=weight1,
            mutation_rate=mutation_rate * 1.5,
            mutation_strength=mutation_strength * 1.5,
            algorithm_switch_rate=0.03,
            rng=rng,
        )
        inherited["behavior_algorithm"] = GeneticTrait(algo_val)

        # Inherit poker algorithms
        poker_algo_val = _inherit_poker_algorithm(
            parent1.poker_algorithm.value,
            parent2.poker_algorithm.value,
            mutation_rate=mutation_rate * 1.2,
            mutation_strength=mutation_strength * 1.2,
            rng=rng,
        )
        inherited["poker_algorithm"] = GeneticTrait(poker_algo_val)

        # Inherit poker strategy with winner-biased weighting
        # Pass weight1 as winner_weight so winner's strategy is favored
        poker_strat_val = _inherit_poker_strategy(
            parent1.poker_strategy_algorithm.value,
            parent2.poker_strategy_algorithm.value,
            mutation_rate=mutation_rate * 1.2,
            mutation_strength=mutation_strength * 1.2,
            winner_weight=weight1,  # NEW: Pass winner bias to poker strategy
            rng=rng,
        )
        inherited["poker_strategy_algorithm"] = GeneticTrait(poker_strat_val)

        # Inherit mate preferences
        mate_prefs = _inherit_mate_preferences(
            parent1.mate_preferences.value,
            parent2.mate_preferences.value,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        inherited["mate_preferences"] = GeneticTrait(mate_prefs)

        return cls(**inherited)


def _inherit_poker_algorithm(
    alg1: Optional["BehaviorAlgorithm"],
    alg2: Optional["BehaviorAlgorithm"],
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> Optional["BehaviorAlgorithm"]:
    """Inherit poker algorithm from parents."""
    if alg1 is not None or alg2 is not None:
        from core.algorithms import crossover_poker_algorithms

        return crossover_poker_algorithms(
            alg1,
            alg2,
            parent1_poker_wins=0,
            parent2_poker_wins=0,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )
    else:
        from core.algorithms import get_random_algorithm

        return get_random_algorithm(rng=rng)


def _inherit_poker_strategy(
    strat1: Optional["PokerStrategyAlgorithm"],
    strat2: Optional["PokerStrategyAlgorithm"],
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
    winner_weight: float = 0.5,
) -> Optional["PokerStrategyAlgorithm"]:
    """Inherit poker strategy from parents with winner-biased inheritance.

    Args:
        strat1: First parent's poker strategy (winner in winner-biased mode)
        strat2: Second parent's poker strategy (loser in winner-biased mode)
        mutation_rate: Probability of mutating each parameter
        mutation_strength: Magnitude of mutations
        rng: Random number generator
        winner_weight: How much strat1 (winner) contributes (0.0-1.0, default 0.5)
            When used with from_winner_choice(), this is typically 0.8.

    Returns:
        Inherited poker strategy algorithm
    """
    if strat1 is not None or strat2 is not None:
        from core.poker.strategy.implementations import crossover_poker_strategies

        return crossover_poker_strategies(
            strat1,
            strat2,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            winner_weight=winner_weight,  # Pass winner bias to crossover
        )
    else:
        from core.poker.strategy.implementations import get_random_poker_strategy

        return get_random_poker_strategy(rng=rng)


def _inherit_mate_preferences(
    prefs1: Dict[str, float],
    prefs2: Dict[str, float],
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> Dict[str, float]:
    """Inherit mate preferences from parents."""
    result = {}
    for pref_key in prefs1:
        p1_val = prefs1.get(pref_key, 0.5)
        p2_val = prefs2.get(pref_key, 0.5)
        result[pref_key] = _inherit_trait(
            p1_val,
            p2_val,
            0.0,
            1.0,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
    return result
