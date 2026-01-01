"""Code policy traits for genome-code integration.

This module provides the bridge between the genetics system and the GenomeCodePool,
enabling:
1. Conversion between BehavioralTraits and GenomePolicySet
2. Pool-aware mutation that swaps to valid components
3. Pool-aware crossover that combines parent policies
4. Validation that ensures genomes reference valid components
"""

from __future__ import annotations

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.genetics.trait import GeneticTrait

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool, GenomePolicySet
    from core.genetics.behavioral import BehavioralTraits

# Policy kinds supported by the genome system
MOVEMENT_POLICY = "movement_policy"
POKER_POLICY = "poker_policy"
SOCCER_POLICY = "soccer_policy"

ALL_POLICY_KINDS = (MOVEMENT_POLICY, POKER_POLICY, SOCCER_POLICY)


@dataclass
class CodePolicyMutationConfig:
    """Configuration for code policy mutation."""

    # Probability of swapping to a different component of the same kind
    swap_probability: float = 0.1

    # Probability of dropping the policy entirely
    drop_probability: float = 0.02

    # Probability of mutating each parameter
    param_mutation_rate: float = 0.15

    # Gaussian sigma for parameter mutations
    param_mutation_strength: float = 0.1

    # Parameter value bounds
    param_min: float = -10.0
    param_max: float = 10.0


def extract_policy_set_from_behavioral(
    behavioral: "BehavioralTraits",
) -> "GenomePolicySet":
    """Extract a GenomePolicySet from BehavioralTraits.

    This bridges the current single-policy approach to the multi-policy GenomePolicySet.

    Args:
        behavioral: The BehavioralTraits to extract from

    Returns:
        A GenomePolicySet with the extracted policies
    """
    from core.code_pool import GenomePolicySet

    policy_set = GenomePolicySet()

    # Extract current code policy (if any)
    kind = _get_trait_value(behavioral.code_policy_kind)
    component_id = _get_trait_value(behavioral.code_policy_component_id)
    params = _get_trait_value(behavioral.code_policy_params)

    if kind and component_id:
        policy_set.set_policy(kind, component_id, params)

    return policy_set


def apply_policy_set_to_behavioral(
    behavioral: "BehavioralTraits",
    policy_set: "GenomePolicySet",
    rng: pyrandom.Random,
) -> None:
    """Apply a GenomePolicySet to BehavioralTraits.

    This updates the behavioral traits with the primary policy from the set.
    Currently, we only store one policy in behavioral traits (the movement policy).

    Args:
        behavioral: The BehavioralTraits to update
        policy_set: The policy set to apply
        rng: Random number generator for trait meta-values
    """
    # Find the primary policy (movement takes precedence)
    primary_kind = None
    primary_id = None
    primary_params = None

    for kind in [MOVEMENT_POLICY, POKER_POLICY, SOCCER_POLICY]:
        component_id = policy_set.get_component_id(kind)
        if component_id:
            primary_kind = kind
            primary_id = component_id
            primary_params = policy_set.get_params(kind)
            break

    # Update behavioral traits
    behavioral.code_policy_kind = GeneticTrait(primary_kind)
    behavioral.code_policy_component_id = GeneticTrait(primary_id)
    behavioral.code_policy_params = GeneticTrait(primary_params)


def mutate_code_policies(
    behavioral: "BehavioralTraits",
    pool: "GenomeCodePool",
    rng: pyrandom.Random,
    config: Optional[CodePolicyMutationConfig] = None,
) -> "BehavioralTraits":
    """Mutate code policy traits using the GenomeCodePool.

    This performs pool-aware mutation:
    1. May swap to a different component of the same kind
    2. May drop the policy entirely
    3. May mutate policy parameters

    Args:
        behavioral: The behavioral traits to mutate
        pool: The genome code pool for valid component lookup
        rng: Random number generator
        config: Mutation configuration (uses defaults if None)

    Returns:
        The mutated behavioral traits (modified in place)
    """
    config = config or CodePolicyMutationConfig()

    kind = _get_trait_value(behavioral.code_policy_kind)
    component_id = _get_trait_value(behavioral.code_policy_component_id)
    params = _get_trait_value(behavioral.code_policy_params)

    # Skip if no policy
    if not kind or not component_id:
        return behavioral

    # Chance to drop the policy
    if rng.random() < config.drop_probability:
        behavioral.code_policy_kind = GeneticTrait(None)
        behavioral.code_policy_component_id = GeneticTrait(None)
        behavioral.code_policy_params = GeneticTrait(None)
        return behavioral

    # Chance to swap to a different component
    if rng.random() < config.swap_probability:
        available = pool.get_components_by_kind(kind)
        if available:
            new_id = rng.choice(available)
            if new_id != component_id:
                behavioral.code_policy_component_id = GeneticTrait(new_id)
                component_id = new_id

    # Mutate parameters
    if params:
        mutated_params = _mutate_params(params, rng, config)
        behavioral.code_policy_params = GeneticTrait(mutated_params)

    return behavioral


def crossover_code_policies(
    parent1: "BehavioralTraits",
    parent2: "BehavioralTraits",
    pool: "GenomeCodePool",
    rng: pyrandom.Random,
    weight1: float = 0.5,
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, float]]]:
    """Crossover code policy traits from two parents.

    Args:
        parent1: First parent's behavioral traits
        parent2: Second parent's behavioral traits
        pool: The genome code pool for validation
        rng: Random number generator
        weight1: Probability of inheriting from parent1

    Returns:
        Tuple of (kind, component_id, params) for the offspring
    """
    p1_kind = _get_trait_value(parent1.code_policy_kind)
    p1_id = _get_trait_value(parent1.code_policy_component_id)
    p1_params = _get_trait_value(parent1.code_policy_params)

    p2_kind = _get_trait_value(parent2.code_policy_kind)
    p2_id = _get_trait_value(parent2.code_policy_component_id)
    p2_params = _get_trait_value(parent2.code_policy_params)

    # Both have no policy
    if not p1_id and not p2_id:
        return None, None, None

    # Choose which parent's policy to inherit
    if p1_id and p2_id:
        # Both have policies - weighted selection
        if rng.random() < weight1:
            kind, component_id = p1_kind, p1_id
        else:
            kind, component_id = p2_kind, p2_id
    elif p1_id:
        # Only parent1 has policy
        if rng.random() < weight1 or rng.random() < 0.3:  # Gene flow
            kind, component_id = p1_kind, p1_id
        else:
            return None, None, None
    else:
        # Only parent2 has policy
        if rng.random() < (1 - weight1) or rng.random() < 0.3:  # Gene flow
            kind, component_id = p2_kind, p2_id
        else:
            return None, None, None

    # Validate component still exists
    if component_id and not pool.has_component(component_id):
        # Component no longer exists - try to find a replacement
        available = pool.get_components_by_kind(kind) if kind else []
        if available:
            component_id = rng.choice(available)
        else:
            return None, None, None

    # Blend parameters from both parents
    blended_params = _blend_params(p1_params, p2_params, weight1)

    return kind, component_id, blended_params


def validate_code_policy_ids(
    behavioral: "BehavioralTraits",
    pool: "GenomeCodePool",
    rng: pyrandom.Random,
) -> List[str]:
    """Validate that code policy IDs reference valid components.

    If invalid, attempts to fix by:
    1. Using the pool's default for the kind
    2. Picking a random valid component
    3. Clearing the policy

    Args:
        behavioral: The behavioral traits to validate
        pool: The genome code pool
        rng: Random number generator

    Returns:
        List of issues found (empty if valid)
    """
    issues = []

    kind = _get_trait_value(behavioral.code_policy_kind)
    component_id = _get_trait_value(behavioral.code_policy_component_id)

    if not component_id:
        return issues  # No policy is valid

    if not kind:
        issues.append("code_policy_component_id set but code_policy_kind is not")
        behavioral.code_policy_kind = GeneticTrait(None)
        behavioral.code_policy_component_id = GeneticTrait(None)
        behavioral.code_policy_params = GeneticTrait(None)
        return issues

    if not pool.has_component(component_id):
        issues.append(f"code_policy_component_id {component_id} not found in pool")

        # Try to fix
        default_id = pool.get_default(kind)
        if default_id:
            behavioral.code_policy_component_id = GeneticTrait(default_id)
        else:
            available = pool.get_components_by_kind(kind)
            if available:
                behavioral.code_policy_component_id = GeneticTrait(rng.choice(available))
            else:
                behavioral.code_policy_kind = GeneticTrait(None)
                behavioral.code_policy_component_id = GeneticTrait(None)
                behavioral.code_policy_params = GeneticTrait(None)

    return issues


def assign_random_policy(
    behavioral: "BehavioralTraits",
    pool: "GenomeCodePool",
    kind: str,
    rng: pyrandom.Random,
) -> bool:
    """Assign a random policy of the given kind from the pool.

    Args:
        behavioral: The behavioral traits to update
        pool: The genome code pool
        kind: The policy kind (e.g., "movement_policy")
        rng: Random number generator

    Returns:
        True if a policy was assigned, False if none available
    """
    available = pool.get_components_by_kind(kind)
    if not available:
        # Try default
        default_id = pool.get_default(kind)
        if not default_id:
            return False
        available = [default_id]

    component_id = rng.choice(available)
    behavioral.code_policy_kind = GeneticTrait(kind)
    behavioral.code_policy_component_id = GeneticTrait(component_id)
    behavioral.code_policy_params = GeneticTrait({})
    return True


# =============================================================================
# Helper Functions
# =============================================================================


def _get_trait_value(trait: Optional[GeneticTrait]) -> Any:
    """Safely get the value from a GeneticTrait."""
    if trait is None:
        return None
    return trait.value


def _mutate_params(
    params: Dict[str, float],
    rng: pyrandom.Random,
    config: CodePolicyMutationConfig,
) -> Dict[str, float]:
    """Mutate policy parameters."""
    result = {}
    for key, value in params.items():
        if rng.random() < config.param_mutation_rate:
            delta = rng.gauss(0, config.param_mutation_strength)
            new_value = value + delta
            new_value = max(config.param_min, min(config.param_max, new_value))
            result[key] = new_value
        else:
            result[key] = value
    return result


def _blend_params(
    params1: Optional[Dict[str, float]],
    params2: Optional[Dict[str, float]],
    weight1: float,
) -> Optional[Dict[str, float]]:
    """Blend parameters from two parents."""
    if not params1 and not params2:
        return None

    p1 = params1 or {}
    p2 = params2 or {}
    all_keys = set(p1.keys()) | set(p2.keys())

    if not all_keys:
        return None

    result = {}
    for key in all_keys:
        v1 = p1.get(key, 0.0)
        v2 = p2.get(key, 0.0)
        result[key] = weight1 * v1 + (1 - weight1) * v2

    return result
