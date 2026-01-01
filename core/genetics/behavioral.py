"""Behavioral traits for fish genomes.

This module defines behavioral characteristics that affect how fish act,
including aggression, social tendencies, and algorithm selection.
"""

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.evolution.inheritance import inherit_discrete_trait as _inherit_discrete_trait
from core.evolution.inheritance import inherit_trait as _inherit_trait
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait import (
    GeneticTrait,
    TraitSpec,
    inherit_traits_from_specs,
    inherit_traits_from_specs_recombination,
    random_genetic_trait,
)

if TYPE_CHECKING:
    from core.algorithms.composable import ComposableBehavior
    from core.genetics.physical import PhysicalTraits
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

from core.code_pool.pool import BUILTIN_SEEK_NEAREST_FOOD_ID

# Type alias for poker strategy (can be monolithic or composable)
PokerStrategyType = "PokerStrategyAlgorithm | ComposablePokerStrategy"


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

# Default mate preferences keep keys stable across versions and inheritance.
DEFAULT_MATE_PREFERENCES: Dict[str, float] = {
    "prefer_similar_size": 0.5,
    "prefer_different_color": 0.5,
    "prefer_high_energy": 0.5,
    "prefer_high_pattern_intensity": 0.5,
}

MATE_PREFERENCE_TRAIT_NAMES = (
    "size_modifier",
    "color_hue",
    "template_id",
    "fin_size",
    "tail_size",
    "body_aspect",
    "eye_size",
    "pattern_type",
)

MATE_PREFERENCE_SPECS: Dict[str, TraitSpec] = {
    spec.name: spec for spec in PHYSICAL_TRAIT_SPECS if spec.name in MATE_PREFERENCE_TRAIT_NAMES
}


def _inherit_trait_meta(
    parent1_trait: Optional[GeneticTrait],
    parent2_trait: Optional[GeneticTrait],
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


def _default_preference_value(spec: TraitSpec) -> float:
    midpoint = (spec.min_val + spec.max_val) / 2.0
    if spec.discrete:
        return float(int(round(midpoint)))
    return float(midpoint)


def _coerce_preference_value(value: object, spec: TraitSpec) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = _default_preference_value(spec)
    if spec.discrete:
        numeric = int(round(numeric))
        numeric = max(int(spec.min_val), min(int(spec.max_val), numeric))
        return float(numeric)
    numeric = max(spec.min_val, min(spec.max_val, numeric))
    return float(numeric)


def _default_preference_for_key(pref_key: str) -> float:
    spec = MATE_PREFERENCE_SPECS.get(pref_key)
    if spec is not None:
        return _default_preference_value(spec)
    return DEFAULT_MATE_PREFERENCES.get(pref_key, 0.5)


def normalize_mate_preferences(
    prefs: Dict[str, float],
    *,
    physical: Optional["PhysicalTraits"] = None,
    rng: Optional[pyrandom.Random] = None,
) -> Dict[str, float]:
    """Normalize mate preferences by filling defaults and clamping to valid ranges."""
    normalized: Dict[str, float] = {str(k): v for k, v in (prefs or {}).items()}

    for pref_key, default_val in DEFAULT_MATE_PREFERENCES.items():
        normalized.setdefault(pref_key, default_val)
        if pref_key not in MATE_PREFERENCE_SPECS:
            try:
                numeric = float(normalized[pref_key])
            except (TypeError, ValueError):
                numeric = default_val
            normalized[pref_key] = max(0.0, min(1.0, numeric))

    for name, spec in MATE_PREFERENCE_SPECS.items():
        if name not in normalized:
            if physical is not None:
                normalized[name] = getattr(physical, name).value
            elif rng is not None:
                normalized[name] = spec.random_value(rng).value
            else:
                normalized[name] = _default_preference_value(spec)
        normalized[name] = _coerce_preference_value(normalized[name], spec)

    return normalized


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
    behavior: Optional[GeneticTrait[Optional["ComposableBehavior"]]] = None

    # Poker strategy for in-game betting decisions (separate from movement)
    poker_strategy: Optional[GeneticTrait[Optional["PokerStrategyAlgorithm"]]] = None

    # Mate preferences (dictionary trait; preferred mate trait values + legacy weights)
    mate_preferences: Optional[GeneticTrait[Dict[str, float]]] = None

    # ==========================================================================
    # Code Policy Traits (for linking to CodePool components)
    # ==========================================================================
    # These traits allow a genome to carry references into the CodePool,
    # enabling fish to use evolved code policies. This is purely data plumbing;
    # the actual code execution happens elsewhere.

    # The kind of policy this genome references (e.g. "movement_policy", "foraging_policy")
    # Must be set if code_policy_component_id is set.
    code_policy_kind: Optional[GeneticTrait[Optional[str]]] = None

    # The component ID from the CodePool. This references an existing component;
    # genetics does NOT generate new component IDs (that's CodePool's job).
    code_policy_component_id: Optional[GeneticTrait[Optional[str]]] = None

    # Optional tuning parameters for the code policy.
    # Keys are parameter names, values are floats in [-10.0, 10.0] range.
    code_policy_params: Optional[GeneticTrait[Optional[Dict[str, float]]]] = None

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

        traits["code_policy_kind"] = random_genetic_trait("movement_policy", rng)
        traits["code_policy_component_id"] = random_genetic_trait(BUILTIN_SEEK_NEAREST_FOOD_ID, rng)
        traits["code_policy_params"] = random_genetic_trait(None, rng)

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
        available_policies: Optional[List[str]] = None,
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

        # Inherit composable behavior
        behavior_val = _inherit_composable_behavior(
            parent1.behavior.value if parent1.behavior else None,
            parent2.behavior.value if parent2.behavior else None,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        inherited["behavior"] = _inherit_trait_meta(
            parent1.behavior, parent2.behavior, behavior_val, rng
        )

        # Inherit poker strategy with winner-biased weighting
        strat1 = parent1.poker_strategy.value if parent1.poker_strategy else None
        strat2 = parent2.poker_strategy.value if parent2.poker_strategy else None
        poker_strat_val = _inherit_poker_strategy(
            strat1,
            strat2,
            mutation_rate=mutation_rate * 1.2,
            mutation_strength=mutation_strength * 1.2,
            winner_weight=weight1,
            rng=rng,
        )
        inherited["poker_strategy"] = _inherit_trait_meta(
            parent1.poker_strategy, parent2.poker_strategy, poker_strat_val, rng
        )

        # Inherit mate preferences
        prefs1 = parent1.mate_preferences.value if parent1.mate_preferences else {}
        prefs2 = parent2.mate_preferences.value if parent2.mate_preferences else {}
        mate_prefs = _inherit_mate_preferences(
            prefs1,
            prefs2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        inherited["mate_preferences"] = _inherit_trait_meta(
            parent1.mate_preferences, parent2.mate_preferences, mate_prefs, rng
        )

        # Inherit code policy traits
        cp_kind, cp_id, cp_params = _inherit_code_policy(
            parent1,
            parent2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
        )
        inherited["code_policy_kind"] = _inherit_trait_meta(
            parent1.code_policy_kind, parent2.code_policy_kind, cp_kind, rng
        )
        inherited["code_policy_component_id"] = _inherit_trait_meta(
            parent1.code_policy_component_id, parent2.code_policy_component_id, cp_id, rng
        )
        inherited["code_policy_params"] = _inherit_trait_meta(
            parent1.code_policy_params, parent2.code_policy_params, cp_params, rng
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
        available_policies: Optional[List[str]] = None,
    ) -> "BehavioralTraits":
        """Inherit behavioral traits by choosing a parent per trait (recombination)."""
        inherited = inherit_traits_from_specs_recombination(
            BEHAVIORAL_TRAIT_SPECS,
            parent1,
            parent2,
            parent1_probability=parent1_probability,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )

        # Inherit composable behavior with recombination-style weighting
        behavior_val = _inherit_composable_behavior(
            parent1.behavior.value if parent1.behavior else None,
            parent2.behavior.value if parent2.behavior else None,
            weight1=1.0 if rng.random() < parent1_probability else 0.0,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        inherited["behavior"] = _inherit_trait_meta(
            parent1.behavior, parent2.behavior, behavior_val, rng
        )

        strat1 = parent1.poker_strategy.value if parent1.poker_strategy else None
        strat2 = parent2.poker_strategy.value if parent2.poker_strategy else None
        poker_strat_val = _inherit_poker_strategy(
            strat1,
            strat2,
            mutation_rate=mutation_rate * 1.2,
            mutation_strength=mutation_strength * 1.2,
            winner_weight=1.0 if rng.random() < parent1_probability else 0.0,
            rng=rng,
        )
        inherited["poker_strategy"] = _inherit_trait_meta(
            parent1.poker_strategy, parent2.poker_strategy, poker_strat_val, rng
        )

        prefs1 = parent1.mate_preferences.value if parent1.mate_preferences else {}
        prefs2 = parent2.mate_preferences.value if parent2.mate_preferences else {}
        mate_prefs = {}
        keys = (
            set(DEFAULT_MATE_PREFERENCES) | set(MATE_PREFERENCE_SPECS) | set(prefs1) | set(prefs2)
        )
        for pref_key in sorted(keys):
            pref_weight1 = 1.0 if rng.random() < parent1_probability else 0.0
            default_val = _default_preference_for_key(pref_key)
            p1_val = prefs1.get(pref_key, default_val)
            p2_val = prefs2.get(pref_key, default_val)
            mate_prefs[pref_key] = _inherit_mate_preference_value(
                pref_key,
                p1_val,
                p2_val,
                weight1=pref_weight1,
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                rng=rng,
            )
        inherited["mate_preferences"] = _inherit_trait_meta(
            parent1.mate_preferences, parent2.mate_preferences, mate_prefs, rng
        )

        # Inherit code policy traits (using recombination weight)
        recomb_weight = 1.0 if rng.random() < parent1_probability else 0.0
        cp_kind, cp_id, cp_params = _inherit_code_policy(
            parent1,
            parent2,
            weight1=recomb_weight,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
            available_policies=available_policies,
        )
        inherited["code_policy_kind"] = _inherit_trait_meta(
            parent1.code_policy_kind, parent2.code_policy_kind, cp_kind, rng
        )
        inherited["code_policy_component_id"] = _inherit_trait_meta(
            parent1.code_policy_component_id, parent2.code_policy_component_id, cp_id, rng
        )
        inherited["code_policy_params"] = _inherit_trait_meta(
            parent1.code_policy_params, parent2.code_policy_params, cp_params, rng
        )

        return cls(**inherited)


def _inherit_composable_behavior(
    behavior1: Optional["ComposableBehavior"],
    behavior2: Optional["ComposableBehavior"],
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> "ComposableBehavior":
    """Inherit composable behavior from two parents.

    Uses ComposableBehavior.from_parents() which handles:
    - Mendelian inheritance for discrete sub-behaviors (threat, food, energy, social, poker)
    - Weighted blending for continuous parameters
    - Mutation of both sub-behavior selections and parameters
    """
    from core.algorithms.composable import ComposableBehavior

    if behavior1 is None and behavior2 is None:
        return ComposableBehavior.create_random(rng=rng)
    elif behavior1 is None:
        return behavior2.clone_with_mutation(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
    elif behavior2 is None:
        return behavior1.clone_with_mutation(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )

    return ComposableBehavior.from_parents(
        behavior1,
        behavior2,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        sub_behavior_switch_rate=0.08,  # Increased from 0.03 for more behavioral diversity
        rng=rng,
    )


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
            rng=rng,
        )
    else:
        # Default to composable poker strategy for new offspring
        from core.poker.strategy.composable import ComposablePokerStrategy

        return ComposablePokerStrategy.create_random(rng=rng)


def _inherit_mate_preference_value(
    pref_key: str,
    p1_val: float,
    p2_val: float,
    *,
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> float:
    spec = MATE_PREFERENCE_SPECS.get(pref_key)
    if spec is None:
        legacy_spec = TraitSpec(pref_key, 0.0, 1.0)
        p1_val = _coerce_preference_value(p1_val, legacy_spec)
        p2_val = _coerce_preference_value(p2_val, legacy_spec)
        return _inherit_trait(
            float(p1_val),
            float(p2_val),
            0.0,
            1.0,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )

    p1_val = _coerce_preference_value(p1_val, spec)
    p2_val = _coerce_preference_value(p2_val, spec)
    if spec.discrete:
        return float(
            _inherit_discrete_trait(
                int(round(p1_val)),
                int(round(p2_val)),
                int(spec.min_val),
                int(spec.max_val),
                weight1=weight1,
                mutation_rate=mutation_rate,
                rng=rng,
            )
        )
    return _inherit_trait(
        float(p1_val),
        float(p2_val),
        spec.min_val,
        spec.max_val,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
    )


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
    keys = sorted(
        set(DEFAULT_MATE_PREFERENCES) | set(MATE_PREFERENCE_SPECS) | set(prefs1) | set(prefs2)
    )
    for pref_key in keys:
        default_val = _default_preference_for_key(pref_key)
        p1_val = prefs1.get(pref_key, default_val)
        p2_val = prefs2.get(pref_key, default_val)
        result[pref_key] = _inherit_mate_preference_value(
            pref_key,
            p1_val,
            p2_val,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
    return result


# =============================================================================
# Code Policy Inheritance Constants
# =============================================================================
# Probability thresholds for code policy inheritance and mutation.

CODE_POLICY_DROP_PROBABILITY: float = 0.02  # 2% chance to drop code policy
CODE_POLICY_PARAM_MUTATION_RATE: float = 0.15  # 15% chance to mutate each param
CODE_POLICY_PARAM_MUTATION_STRENGTH: float = 0.1  # Gaussian sigma for param changes
CODE_POLICY_PARAM_MIN: float = -10.0  # Minimum allowed param value
CODE_POLICY_PARAM_MAX: float = 10.0  # Maximum allowed param value


def _inherit_code_policy(
    parent1: "BehavioralTraits",
    parent2: "BehavioralTraits",
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
    available_policies: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, float]]]:
    """Inherit code policy traits from parents.

    Rules:
    - If both parents have code policies, inherit one based on weight1 probability.
    - If only one parent has a code policy, child may inherit it with probability.
    - Mutation can drop the code policy (set to None) with small probability.
    - Mutation can duplicate params if not swapping policy.
    - If available_policies is provided, small chance to swap to a random policy from the list.

    Returns:
        Tuple of (code_policy_kind, code_policy_component_id, code_policy_params)
    """
    # Extract parent values
    p1_kind = (
        parent1.code_policy_kind.value
        if parent1.code_policy_kind and parent1.code_policy_kind.value
        else None
    )
    p1_id = (
        parent1.code_policy_component_id.value
        if parent1.code_policy_component_id and parent1.code_policy_component_id.value
        else None
    )
    p1_params = (
        parent1.code_policy_params.value
        if parent1.code_policy_params and parent1.code_policy_params.value
        else None
    )

    p2_kind = (
        parent2.code_policy_kind.value
        if parent2.code_policy_kind and parent2.code_policy_kind.value
        else None
    )
    p2_id = (
        parent2.code_policy_component_id.value
        if parent2.code_policy_component_id and parent2.code_policy_component_id.value
        else None
    )
    p2_params = (
        parent2.code_policy_params.value
        if parent2.code_policy_params and parent2.code_policy_params.value
        else None
    )

    # Both parents have no code policy
    if p1_id is None and p2_id is None:
        return None, None, None

    # Determine which parent's code policy to inherit
    if p1_id is not None and p2_id is not None:
        # Both have code policies - use weighted selection
        if rng.random() < weight1:
            kind, component_id, params = p1_kind, p1_id, p1_params
        else:
            kind, component_id, params = p2_kind, p2_id, p2_params
    elif p1_id is not None:
        # Only parent1 has a code policy
        # Inherit with probability proportional to weight1
        if rng.random() < weight1:
            kind, component_id, params = p1_kind, p1_id, p1_params
        else:
            # Small chance to inherit anyway (gene flow)
            if rng.random() < 0.3:
                kind, component_id, params = p1_kind, p1_id, p1_params
            else:
                return None, None, None
    else:
        # Only parent2 has a code policy
        weight2 = 1.0 - weight1
        if rng.random() < weight2:
            kind, component_id, params = p2_kind, p2_id, p2_params
        else:
            # Small chance to inherit anyway
            if rng.random() < 0.3:
                kind, component_id, params = p2_kind, p2_id, p2_params
            else:
                return None, None, None

    # Mutation: chance to drop the code policy entirely
    if rng.random() < CODE_POLICY_DROP_PROBABILITY * mutation_rate:
        return None, None, None

    # Mutation: chance to swap to a different available policy
    if available_policies and rng.random() < mutation_rate * 0.1:  # 10% of mutation rate
        # Pick a random policy from available ones
        new_id = rng.choice(available_policies)
        # If we swapped, reset params or keep? Let's reset to None for fresh start
        return "movement_policy", new_id, None

    # Mutation: mutate params if present
    mutated_params = _mutate_code_policy_params(params, mutation_rate, mutation_strength, rng)

    return kind, component_id, mutated_params


def _mutate_code_policy_params(
    params: Optional[Dict[str, float]],
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> Optional[Dict[str, float]]:
    """Mutate code policy parameters slightly.

    Each parameter has a chance to be mutated using Gaussian noise.
    Values are clamped to [CODE_POLICY_PARAM_MIN, CODE_POLICY_PARAM_MAX].
    """
    if params is None:
        return None

    mutated = dict(params)
    eff_mutation_rate = CODE_POLICY_PARAM_MUTATION_RATE * mutation_rate
    eff_strength = CODE_POLICY_PARAM_MUTATION_STRENGTH * mutation_strength

    for key in mutated:
        if rng.random() < eff_mutation_rate:
            old_val = mutated[key]
            delta = rng.gauss(0, eff_strength)
            new_val = old_val + delta
            # Clamp to valid range
            new_val = max(CODE_POLICY_PARAM_MIN, min(CODE_POLICY_PARAM_MAX, new_val))
            mutated[key] = new_val

    return mutated


def validate_code_policy(
    kind: Optional[str],
    component_id: Optional[str],
    params: Optional[Dict[str, float]],
) -> List[str]:
    """Validate code policy fields and return a list of issues.

    Validation rules:
    - If code_policy_component_id is set, code_policy_kind must be set.
    - params must have finite numbers, bounded in [CODE_POLICY_PARAM_MIN, CODE_POLICY_PARAM_MAX].

    Returns:
        List of issue strings (empty if valid).
    """
    import math

    issues: List[str] = []

    # If component_id is set, kind must also be set
    if component_id is not None and kind is None:
        issues.append("code_policy_component_id is set but code_policy_kind is not set")

    # Validate params if present
    if params is not None:
        if not isinstance(params, dict):
            issues.append(f"code_policy_params must be a dict, got {type(params).__name__}")
        else:
            for key, val in params.items():
                if not isinstance(key, str):
                    issues.append(f"code_policy_params key must be str, got {type(key).__name__}")
                if not isinstance(val, (int, float)):
                    issues.append(
                        f"code_policy_params[{key!r}] must be numeric, got {type(val).__name__}"
                    )
                elif math.isnan(val) or math.isinf(val):
                    issues.append(f"code_policy_params[{key!r}] must be finite, got {val}")
                elif val < CODE_POLICY_PARAM_MIN or val > CODE_POLICY_PARAM_MAX:
                    issues.append(
                        f"code_policy_params[{key!r}]={val} out of range "
                        f"[{CODE_POLICY_PARAM_MIN}, {CODE_POLICY_PARAM_MAX}]"
                    )

    return issues
