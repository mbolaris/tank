"""Behavioral traits for fish genomes.

This module defines behavioral characteristics that affect how fish act,
including aggression, social tendencies, and algorithm selection.

The module is intentionally declarative: trait *specs* and the
BehavioralTraits dataclass live here, while the inheritance logic lives in
focused collaborators:

- core/genetics/behavioral_inheritance.py: blending/recombination inheritance
- core/genetics/mate_preferences.py: mate preference system
- core/genetics/policy_inheritance.py: code policy inheritance + validation

All previous public (and private helper) names remain importable from this
module for backwards compatibility.
"""

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core.genetics.behavioral_inheritance import (
    inherit_behavioral_traits,
    inherit_composable_behavior,
    inherit_poker_strategy,
    inherit_trait_meta,
    recombine_behavioral_traits,
)
from core.genetics.mate_preferences import (
    DEFAULT_MATE_PREFERENCES,
    MATE_PREFERENCE_SPECS,
    MATE_PREFERENCE_TRAIT_NAMES,
    coerce_preference_value,
    default_preference_for_key,
    default_preference_value,
    inherit_mate_preference_value,
    inherit_mate_preferences,
    normalize_mate_preferences,
)
from core.genetics.policy_inheritance import (
    CODE_POLICY_DROP_PROBABILITY,
    CODE_POLICY_PARAM_MAX,
    CODE_POLICY_PARAM_MIN,
    CODE_POLICY_PARAM_MUTATION_RATE,
    CODE_POLICY_PARAM_MUTATION_STRENGTH,
    inherit_single_policy,
    mutate_code_policy_params,
    validate_code_policy,
    validate_policy_fields,
)
from core.genetics.reproduction import ReproductionMutationContext
from core.genetics.trait import GeneticTrait, TraitSpec, random_genetic_trait

if TYPE_CHECKING:
    from core.algorithms.composable import ComposableBehavior
    from core.genetics.physical import PhysicalTraits
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

from core.code_pool.pool import BUILTIN_SEEK_NEAREST_FOOD_ID

__all__ = [
    "BEHAVIORAL_TRAIT_SPECS",
    "BehavioralTraits",
    "CODE_POLICY_DROP_PROBABILITY",
    "CODE_POLICY_PARAM_MAX",
    "CODE_POLICY_PARAM_MIN",
    "CODE_POLICY_PARAM_MUTATION_RATE",
    "CODE_POLICY_PARAM_MUTATION_STRENGTH",
    "DEFAULT_MATE_PREFERENCES",
    "MATE_BEHAVIORAL_PREFERENCE_NAMES",
    "MATE_BEHAVIORAL_PREFERENCE_SPECS",
    "MATE_PREFERENCE_SPECS",
    "MATE_PREFERENCE_TRAIT_NAMES",
    "PokerStrategyType",
    "inherit_behavioral_traits",
    "normalize_mate_preferences",
    "recombine_behavioral_traits",
    "validate_code_policy",
    "validate_policy_fields",
]

# Type alias for poker strategy (can be monolithic or composable)
PokerStrategyType = "PokerStrategyAlgorithm | ComposablePokerStrategy"


# Declarative specifications for behavioral traits (numeric only)
# Algorithms are handled separately since they're not simple values
BEHAVIORAL_TRAIT_SPECS: list[TraitSpec] = [
    TraitSpec("aggression", 0.0, 1.0),
    TraitSpec("social_tendency", 0.0, 1.0),
    TraitSpec("pursuit_aggression", 0.0, 1.0),
    TraitSpec("prediction_skill", 0.0, 1.0),
    TraitSpec("hunting_stamina", 0.0, 1.0),
    TraitSpec("asexual_reproduction_chance", 0.0, 1.0),
]

# Behavioral traits that can be selected for via mate preferences.
# These use the behavioral trait specs, not physical ones.
MATE_BEHAVIORAL_PREFERENCE_NAMES = (
    "aggression",
    "social_tendency",
)

# Add behavioral trait specs to mate preference specs
MATE_BEHAVIORAL_PREFERENCE_SPECS: dict[str, TraitSpec] = {
    spec.name: spec
    for spec in BEHAVIORAL_TRAIT_SPECS
    if spec.name in MATE_BEHAVIORAL_PREFERENCE_NAMES
}

# Backwards-compatible aliases for helpers that moved to focused modules.
# Kept so existing imports (including tests) keep working unchanged.
_inherit_trait_meta = inherit_trait_meta
_inherit_composable_behavior = inherit_composable_behavior
_inherit_poker_strategy = inherit_poker_strategy
_inherit_mate_preferences = inherit_mate_preferences
_inherit_mate_preference_value = inherit_mate_preference_value
_inherit_single_policy = inherit_single_policy
_mutate_code_policy_params = mutate_code_policy_params
_default_preference_value = default_preference_value
_default_preference_for_key = default_preference_for_key
_coerce_preference_value = coerce_preference_value


@dataclass
class BehavioralTraits:
    """Behavioral attributes of a fish.

    These traits affect decision-making, social behavior, and AI strategies.

    The behavior field replaces the old behavior_algorithm and
    poker_algorithm fields, providing a more evolvable system with 1,152+
    possible behavior combinations instead of 48 monolithic algorithms.
    """

    # Numeric behavioral traits
    aggression: GeneticTrait[float]
    social_tendency: GeneticTrait[float]
    pursuit_aggression: GeneticTrait[float]
    prediction_skill: GeneticTrait[float]
    hunting_stamina: GeneticTrait[float]
    asexual_reproduction_chance: GeneticTrait[float]

    # Composable behavior (replaces behavior_algorithm + poker_algorithm)
    # This single field encodes: threat response, food approach, energy style,
    # social mode, and poker engagement - each with tunable parameters.
    # Optional; None means no algorithm assigned.
    behavior: GeneticTrait[Optional["ComposableBehavior"]] | None = None

    # Poker strategy for in-game betting decisions (separate from movement)
    poker_strategy: GeneticTrait[Optional["PokerStrategyAlgorithm"]] | None = None

    # Mate preferences (dictionary trait; preferred mate trait values + legacy weights)
    mate_preferences: GeneticTrait[dict[str, float]] | None = None

    # ==========================================================================
    # Multi-Policy Traits (for linking to CodePool components by kind)
    # ==========================================================================
    # These traits allow a genome to carry references into the CodePool for
    # multiple policy kinds simultaneously. Each kind (movement, poker, soccer)
    # has its own component_id and params fields.

    # Movement policy (tank fish navigation, foraging behavior)
    movement_policy_id: GeneticTrait[str | None] | None = None
    movement_policy_params: GeneticTrait[dict[str, float] | None] | None = None

    # Poker policy (in-game poker decisions, betting behavior)
    poker_policy_id: GeneticTrait[str | None] | None = None
    poker_policy_params: GeneticTrait[dict[str, float] | None] | None = None

    # Soccer policy (soccer training world behavior)
    soccer_policy_id: GeneticTrait[str | None] | None = None
    soccer_policy_params: GeneticTrait[dict[str, float] | None] | None = None

    @classmethod
    def random(
        cls,
        rng: pyrandom.Random,
        use_algorithm: bool = True,
        physical: Optional["PhysicalTraits"] = None,
    ) -> "BehavioralTraits":
        """Generate random behavioral traits."""
        # Generate numeric traits from specs
        traits = {spec.name: spec.random_value(rng) for spec in BEHAVIORAL_TRAIT_SPECS}

        # Generate composable behavior and poker strategy
        behavior = None
        poker_strategy = None

        if use_algorithm:
            from core.algorithms.composable import ComposableBehavior
            from core.poker.strategy.composable import ComposablePokerStrategy

            behavior = ComposableBehavior.create_random(rng=rng)
            # Use ComposablePokerStrategy for new fish (576 strategy combinations)
            poker_strategy = ComposablePokerStrategy.create_random(rng=rng)

        traits["behavior"] = random_genetic_trait(behavior, rng)
        traits["poker_strategy"] = random_genetic_trait(poker_strategy, rng)
        mate_preferences = normalize_mate_preferences({}, physical=physical, rng=rng)
        traits["mate_preferences"] = random_genetic_trait(mate_preferences, rng)

        # New per-kind policy fields: only movement policy is set by default
        traits["movement_policy_id"] = random_genetic_trait(BUILTIN_SEEK_NEAREST_FOOD_ID, rng)
        traits["movement_policy_params"] = random_genetic_trait(None, rng)
        traits["poker_policy_id"] = random_genetic_trait(None, rng)
        traits["poker_policy_params"] = random_genetic_trait(None, rng)
        traits["soccer_policy_id"] = random_genetic_trait(None, rng)
        traits["soccer_policy_params"] = random_genetic_trait(None, rng)

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
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
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
        inherited = inherit_behavioral_traits(
            BEHAVIORAL_TRAIT_SPECS,
            parent1,
            parent2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
            diversity_score=diversity_score,
            mutation_context=mutation_context,
        )
        return cls(**inherited)

    @classmethod
    def from_parents_recombination(
        cls,
        parent1: "BehavioralTraits",
        parent2: "BehavioralTraits",
        *,
        parent1_probability: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: pyrandom.Random,
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
        parent1_dominant: bool | None = None,
    ) -> "BehavioralTraits":
        """Inherit behavioral traits by choosing a parent per trait (recombination)."""
        inherited = recombine_behavioral_traits(
            BEHAVIORAL_TRAIT_SPECS,
            parent1,
            parent2,
            parent1_probability=parent1_probability,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
            diversity_score=diversity_score,
            mutation_context=mutation_context,
            parent1_dominant=parent1_dominant,
        )
        return cls(**inherited)
