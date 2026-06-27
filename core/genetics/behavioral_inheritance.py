"""Inheritance logic for behavioral traits.

This module owns the two inheritance paths for BehavioralTraits — weighted
blending (``inherit_behavioral_traits``) and per-trait recombination
(``recombine_behavioral_traits``) — plus the helpers they share for
composable behaviors, poker strategies, and trait meta-values.

The trait *specs* stay declarative in core/genetics/behavioral.py and are
passed in, so this module holds only logic.

Extracted verbatim from core/genetics/behavioral.py (behavior-preserving
split): RNG call order is determinism-critical and must not change.
"""

import random as pyrandom
from typing import TYPE_CHECKING, Any, Optional

from core.genetics.mate_preferences import (
    DEFAULT_MATE_PREFERENCES,
    MATE_PREFERENCE_SPECS,
    default_preference_for_key,
    inherit_mate_preference_value,
    inherit_mate_preferences,
)
from core.genetics.policy_inheritance import inherit_single_policy
from core.genetics.reproduction import (
    DEFAULT_SUB_BEHAVIOR_SWITCH_RATE,
    ReproductionMutationContext,
)
from core.genetics.trait import (
    GeneticTrait,
    TraitSpec,
    inherit_traits_from_specs,
    inherit_traits_from_specs_recombination,
)

if TYPE_CHECKING:
    from core.algorithms.composable import ComposableBehavior
    from core.genetics.behavioral import BehavioralTraits
    from core.poker.strategy.implementations import PokerStrategyAlgorithm


def inherit_trait_meta(
    parent1_trait: GeneticTrait | None,
    parent2_trait: GeneticTrait | None,
    value: Any,
    rng: pyrandom.Random,
) -> GeneticTrait:
    """Create a GeneticTrait with inherited meta-values from parents.

    Blends mutation_rate, mutation_strength, and hgt_probability from both
    parent traits, then applies meta-mutation to allow evolution of evolvability.

    Args:
        parent1_trait: First parent's GeneticTrait (may be None)
        parent2_trait: Second parent's GeneticTrait (may be None)
        value: The value for the new trait
        rng: Random number generator for meta-mutation

    Returns:
        GeneticTrait with inherited and mutated meta-values
    """
    # Default meta values if parent trait is missing
    default_rate = 1.0
    default_strength = 1.0
    default_hgt = 0.1

    rate1 = parent1_trait.mutation_rate if parent1_trait else default_rate
    rate2 = parent2_trait.mutation_rate if parent2_trait else default_rate
    strength1 = parent1_trait.mutation_strength if parent1_trait else default_strength
    strength2 = parent2_trait.mutation_strength if parent2_trait else default_strength
    hgt1 = parent1_trait.hgt_probability if parent1_trait else default_hgt
    hgt2 = parent2_trait.hgt_probability if parent2_trait else default_hgt

    # Blend parent meta-values (same as TraitSpec.inherit)
    new_trait = GeneticTrait(
        value,
        mutation_rate=(rate1 + rate2) / 2,
        mutation_strength=(strength1 + strength2) / 2,
        hgt_probability=(hgt1 + hgt2) / 2,
    )
    # Allow meta-values to evolve
    new_trait.mutate_meta(rng)
    return new_trait


def inherit_composable_behavior(
    behavior1: Optional["ComposableBehavior"],
    behavior2: Optional["ComposableBehavior"],
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
    diversity_score: float | None = None,
    mutation_context: ReproductionMutationContext | None = None,
) -> "ComposableBehavior":
    """Inherit composable behavior from two parents.

    Uses ComposableBehavior.from_parents() which handles:
    - Mendelian inheritance for discrete sub-behaviors (threat, food, energy, social, poker)
    - Weighted blending for continuous parameters
    - Mutation of both sub-behavior selections and parameters
    """
    from core.algorithms.composable import ComposableBehavior

    context = mutation_context or ReproductionMutationContext.from_score(diversity_score)
    sub_behavior_switch_rate = context.sub_behavior_switch_rate(DEFAULT_SUB_BEHAVIOR_SWITCH_RATE)

    if behavior1 is None and behavior2 is None:
        return ComposableBehavior.create_random(rng=rng)
    elif behavior1 is None:
        assert behavior2 is not None
        child = ComposableBehavior.from_dict(behavior2.to_dict())
        child.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )
        return child
    elif behavior2 is None:
        assert behavior1 is not None
        child = ComposableBehavior.from_dict(behavior1.to_dict())
        child.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )
        return child

    return ComposableBehavior.from_parents(
        behavior1,
        behavior2,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        sub_behavior_switch_rate=sub_behavior_switch_rate,  # Increased from 0.03 for more behavioral diversity
        rng=rng,
    )


def inherit_poker_strategy(
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
            rng=rng,
        )
    else:
        # Default to composable poker strategy for new offspring
        from core.poker.strategy.composable import ComposablePokerStrategy

        return ComposablePokerStrategy.create_random(rng=rng)


def inherit_behavioral_traits(
    specs: list[TraitSpec],
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
) -> dict:
    """Build the inherited trait dict for BehavioralTraits.from_parents.

    Args:
        specs: Declarative numeric trait specs (BEHAVIORAL_TRAIT_SPECS)
        parent1: First parent's behavioral traits (winner in winner-biased mode)
        parent2: Second parent's behavioral traits (loser in winner-biased mode)
        weight1: How much parent1 contributes (0.0-1.0). In winner-biased mode,
                 this is typically 0.8 for the poker winner.
        mutation_rate: Base mutation probability
        mutation_strength: Mutation magnitude
        rng: Random number generator
        available_policies: Optional list of policy IDs to swap to during mutation

    Returns:
        Dict of field name -> GeneticTrait, ready for BehavioralTraits(**...).
    """

    # Inherit numeric traits using specs
    inherited = inherit_traits_from_specs(
        specs,
        parent1,
        parent2,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
    )

    # Inherit composable behavior
    behavior_val = inherit_composable_behavior(
        parent1.behavior.value if parent1.behavior else None,
        parent2.behavior.value if parent2.behavior else None,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
        diversity_score=diversity_score,
        mutation_context=mutation_context,
    )
    inherited["behavior"] = inherit_trait_meta(
        parent1.behavior, parent2.behavior, behavior_val, rng
    )

    # Inherit poker strategy with winner-biased weighting
    strat1 = parent1.poker_strategy.value if parent1.poker_strategy else None
    strat2 = parent2.poker_strategy.value if parent2.poker_strategy else None
    poker_strat_val = inherit_poker_strategy(
        strat1,
        strat2,
        mutation_rate=mutation_rate * 1.2,
        mutation_strength=mutation_strength * 1.2,
        winner_weight=weight1,
        rng=rng,
    )
    inherited["poker_strategy"] = inherit_trait_meta(
        parent1.poker_strategy, parent2.poker_strategy, poker_strat_val, rng
    )

    # Inherit mate preferences
    prefs1 = parent1.mate_preferences.value if parent1.mate_preferences else {}
    prefs2 = parent2.mate_preferences.value if parent2.mate_preferences else {}
    mate_prefs = inherit_mate_preferences(
        prefs1,
        prefs2,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
    )
    inherited["mate_preferences"] = inherit_trait_meta(
        parent1.mate_preferences, parent2.mate_preferences, mate_prefs, rng
    )

    # Inherit per-kind policy traits (new multi-policy system)
    for kind in ("movement_policy", "poker_policy", "soccer_policy"):
        id_attr = f"{kind}_id"
        params_attr = f"{kind}_params"
        policy_id, policy_params = inherit_single_policy(
            getattr(parent1, id_attr, None),
            getattr(parent2, id_attr, None),
            getattr(parent1, params_attr, None),
            getattr(parent2, params_attr, None),
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
        )
        inherited[id_attr] = inherit_trait_meta(
            getattr(parent1, id_attr, None),
            getattr(parent2, id_attr, None),
            policy_id,
            rng,
        )
        inherited[params_attr] = inherit_trait_meta(
            getattr(parent1, params_attr, None),
            getattr(parent2, params_attr, None),
            policy_params,
            rng,
        )

    return inherited


def recombine_behavioral_traits(
    specs: list[TraitSpec],
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
) -> dict:
    """Build the inherited trait dict for BehavioralTraits.from_parents_recombination.

    Chooses a parent per trait (recombination) instead of blending.

    Returns:
        Dict of field name -> GeneticTrait, ready for BehavioralTraits(**...).
    """
    inherited = inherit_traits_from_specs_recombination(
        specs,
        parent1,
        parent2,
        parent1_probability=parent1_probability,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
    )

    # Inherit composable behavior with recombination-style weighting
    behavior_val = inherit_composable_behavior(
        parent1.behavior.value if parent1.behavior else None,
        parent2.behavior.value if parent2.behavior else None,
        weight1=1.0 if rng.random() < parent1_probability else 0.0,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
        diversity_score=diversity_score,
        mutation_context=mutation_context,
    )
    inherited["behavior"] = inherit_trait_meta(
        parent1.behavior, parent2.behavior, behavior_val, rng
    )

    strat1 = parent1.poker_strategy.value if parent1.poker_strategy else None
    strat2 = parent2.poker_strategy.value if parent2.poker_strategy else None
    poker_strat_val = inherit_poker_strategy(
        strat1,
        strat2,
        mutation_rate=mutation_rate * 1.2,
        mutation_strength=mutation_strength * 1.2,
        winner_weight=1.0 if rng.random() < parent1_probability else 0.0,
        rng=rng,
    )
    inherited["poker_strategy"] = inherit_trait_meta(
        parent1.poker_strategy, parent2.poker_strategy, poker_strat_val, rng
    )

    prefs1 = parent1.mate_preferences.value if parent1.mate_preferences else {}
    prefs2 = parent2.mate_preferences.value if parent2.mate_preferences else {}
    mate_prefs = {}
    keys = set(DEFAULT_MATE_PREFERENCES) | set(MATE_PREFERENCE_SPECS) | set(prefs1) | set(prefs2)
    for pref_key in sorted(keys):
        pref_weight1 = 1.0 if rng.random() < parent1_probability else 0.0
        default_val = default_preference_for_key(pref_key)
        p1_val = prefs1.get(pref_key, default_val)
        p2_val = prefs2.get(pref_key, default_val)
        mate_prefs[pref_key] = inherit_mate_preference_value(
            pref_key,
            p1_val,
            p2_val,
            weight1=pref_weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
    inherited["mate_preferences"] = inherit_trait_meta(
        parent1.mate_preferences, parent2.mate_preferences, mate_prefs, rng
    )

    # Inherit per-kind policy traits (new multi-policy system)
    for kind in ("movement_policy", "poker_policy", "soccer_policy"):
        id_attr = f"{kind}_id"
        params_attr = f"{kind}_params"
        # Each policy kind gets its own recombination weight
        kind_recomb_weight = 1.0 if rng.random() < parent1_probability else 0.0
        policy_id, policy_params = inherit_single_policy(
            getattr(parent1, id_attr, None),
            getattr(parent2, id_attr, None),
            getattr(parent1, params_attr, None),
            getattr(parent2, params_attr, None),
            weight1=kind_recomb_weight,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
        )
        inherited[id_attr] = inherit_trait_meta(
            getattr(parent1, id_attr, None),
            getattr(parent2, id_attr, None),
            policy_id,
            rng,
        )
        inherited[params_attr] = inherit_trait_meta(
            getattr(parent1, params_attr, None),
            getattr(parent2, params_attr, None),
            policy_params,
            rng,
        )

    return inherited
