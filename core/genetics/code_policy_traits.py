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
from typing import TYPE_CHECKING, Any

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
    behavioral: BehavioralTraits,
) -> GenomePolicySet:
    """Extract a GenomePolicySet from BehavioralTraits.

    Extracts ALL policy kinds (movement, poker, soccer) from the per-kind fields.

    Args:
        behavioral: The BehavioralTraits to extract from

    Returns:
        A GenomePolicySet with all extracted policies
    """
    from core.code_pool import GenomePolicySet

    policy_set = GenomePolicySet()

    # Extract from per-kind policy fields
    for kind, id_attr, params_attr in [
        (MOVEMENT_POLICY, "movement_policy_id", "movement_policy_params"),
        (POKER_POLICY, "poker_policy_id", "poker_policy_params"),
        (SOCCER_POLICY, "soccer_policy_id", "soccer_policy_params"),
    ]:
        component_id = _get_trait_value(getattr(behavioral, id_attr, None))
        params = _get_trait_value(getattr(behavioral, params_attr, None))
        if component_id:
            policy_set.set_policy(kind, component_id, params)

    return policy_set


def apply_policy_set_to_behavioral(
    behavioral: BehavioralTraits,
    policy_set: GenomePolicySet,
    rng: pyrandom.Random,
) -> None:
    """Apply a GenomePolicySet to BehavioralTraits.

    Writes ALL policy kinds (movement, poker, soccer) to their respective per-kind fields.

    Args:
        behavioral: The BehavioralTraits to update
        policy_set: The policy set to apply
        rng: Random number generator for trait meta-values
    """
    # Write to per-kind policy fields
    for kind, id_attr, params_attr in [
        (MOVEMENT_POLICY, "movement_policy_id", "movement_policy_params"),
        (POKER_POLICY, "poker_policy_id", "poker_policy_params"),
        (SOCCER_POLICY, "soccer_policy_id", "soccer_policy_params"),
    ]:
        component_id = policy_set.get_component_id(kind)
        params = policy_set.get_params(kind)
        setattr(behavioral, id_attr, GeneticTrait(component_id))
        setattr(behavioral, params_attr, GeneticTrait(params))


def mutate_code_policies(
    behavioral: BehavioralTraits,
    pool: GenomeCodePool,
    rng: pyrandom.Random,
    config: CodePolicyMutationConfig | None = None,
) -> BehavioralTraits:
    """Mutate code policy traits using the GenomeCodePool.

    This performs pool-aware mutation on ALL per-kind policy fields:
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

    # Mutate each policy kind independently
    for kind, id_attr, params_attr in [
        (MOVEMENT_POLICY, "movement_policy_id", "movement_policy_params"),
        (POKER_POLICY, "poker_policy_id", "poker_policy_params"),
        (SOCCER_POLICY, "soccer_policy_id", "soccer_policy_params"),
    ]:
        component_id = _get_trait_value(getattr(behavioral, id_attr, None))
        params = _get_trait_value(getattr(behavioral, params_attr, None))

        # Skip if no policy for this kind
        if not component_id:
            continue

        # Chance to drop the policy
        if rng.random() < config.drop_probability:
            setattr(behavioral, id_attr, GeneticTrait(None))
            setattr(behavioral, params_attr, GeneticTrait(None))
            continue

        # Chance to swap to a different component
        if rng.random() < config.swap_probability:
            available = pool.get_components_by_kind(kind)
            if available:
                new_id = rng.choice(available)
                if new_id != component_id:
                    setattr(behavioral, id_attr, GeneticTrait(new_id))
                    component_id = new_id

        # Mutate parameters
        if params:
            mutated_params = _mutate_params(params, rng, config)
            setattr(behavioral, params_attr, GeneticTrait(mutated_params))

    return behavioral


def crossover_code_policies(
    parent1: BehavioralTraits,
    parent2: BehavioralTraits,
    pool: GenomeCodePool,
    rng: pyrandom.Random,
    weight1: float = 0.5,
) -> dict[str, tuple[str | None, dict[str, float] | None]]:
    """Crossover code policy traits from two parents for ALL policy kinds.

    Args:
        parent1: First parent's behavioral traits
        parent2: Second parent's behavioral traits
        pool: The genome code pool for validation
        rng: Random number generator
        weight1: Probability of inheriting from parent1

    Returns:
        Dict mapping policy kind to (component_id, params) tuple
    """
    result: dict[str, tuple[str | None, dict[str, float] | None]] = {}

    for kind, id_attr, params_attr in [
        (MOVEMENT_POLICY, "movement_policy_id", "movement_policy_params"),
        (POKER_POLICY, "poker_policy_id", "poker_policy_params"),
        (SOCCER_POLICY, "soccer_policy_id", "soccer_policy_params"),
    ]:
        p1_id = _get_trait_value(getattr(parent1, id_attr, None))
        p1_params = _get_trait_value(getattr(parent1, params_attr, None))
        p2_id = _get_trait_value(getattr(parent2, id_attr, None))
        p2_params = _get_trait_value(getattr(parent2, params_attr, None))

        # Both have no policy for this kind
        if not p1_id and not p2_id:
            result[kind] = (None, None)
            continue

        # Choose which parent's policy to inherit
        if p1_id and p2_id:
            # Both have policies - weighted selection
            if rng.random() < weight1:
                component_id = p1_id
            else:
                component_id = p2_id
        elif p1_id:
            # Only parent1 has policy
            if rng.random() < weight1 or rng.random() < 0.3:  # Gene flow
                component_id = p1_id
            else:
                result[kind] = (None, None)
                continue
        else:
            # Only parent2 has policy
            if rng.random() < (1 - weight1) or rng.random() < 0.3:  # Gene flow
                component_id = p2_id
            else:
                result[kind] = (None, None)
                continue

        # Validate component still exists
        if component_id and not pool.has_component(component_id):
            # Component no longer exists - try to find a replacement
            available = pool.get_components_by_kind(kind)
            if available:
                component_id = rng.choice(available)
            else:
                result[kind] = (None, None)
                continue

        # Blend parameters from both parents
        blended_params = _blend_params(p1_params, p2_params, weight1)
        result[kind] = (component_id, blended_params)

    return result


def validate_code_policy_ids(
    behavioral: BehavioralTraits,
    pool: GenomeCodePool,
    rng: pyrandom.Random,
) -> list[str]:
    """Validate that per-kind policy IDs reference valid components.

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

    for kind, id_attr, params_attr in [
        (MOVEMENT_POLICY, "movement_policy_id", "movement_policy_params"),
        (POKER_POLICY, "poker_policy_id", "poker_policy_params"),
        (SOCCER_POLICY, "soccer_policy_id", "soccer_policy_params"),
    ]:
        component_id = _get_trait_value(getattr(behavioral, id_attr, None))

        if not component_id:
            continue  # No policy for this kind is valid

        if not pool.has_component(component_id):
            issues.append(f"{id_attr} {component_id} not found in pool")

            # Try to fix
            default_id = pool.get_default(kind)
            if default_id:
                setattr(behavioral, id_attr, GeneticTrait(default_id))
            else:
                available = pool.get_components_by_kind(kind)
                if available:
                    setattr(behavioral, id_attr, GeneticTrait(rng.choice(available)))
                else:
                    setattr(behavioral, id_attr, GeneticTrait(None))
                    setattr(behavioral, params_attr, GeneticTrait(None))

    return issues


def assign_random_policy(
    behavioral: BehavioralTraits,
    pool: GenomeCodePool,
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

    # Map kind to the appropriate per-kind field
    kind_to_attr = {
        MOVEMENT_POLICY: ("movement_policy_id", "movement_policy_params"),
        POKER_POLICY: ("poker_policy_id", "poker_policy_params"),
        SOCCER_POLICY: ("soccer_policy_id", "soccer_policy_params"),
    }
    id_attr, params_attr = kind_to_attr.get(kind, (None, None))
    if id_attr is None or params_attr is None:
        return False

    setattr(behavioral, id_attr, GeneticTrait(component_id))
    setattr(behavioral, params_attr, GeneticTrait({}))
    return True


# =============================================================================
# Helper Functions
# =============================================================================


def _get_trait_value(trait: GeneticTrait | None) -> Any:
    """Safely get the value from a GeneticTrait."""
    if trait is None:
        return None
    return trait.value


def _mutate_params(
    params: dict[str, float],
    rng: pyrandom.Random,
    config: CodePolicyMutationConfig,
) -> dict[str, float]:
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
    params1: dict[str, float] | None,
    params2: dict[str, float] | None,
    weight1: float,
) -> dict[str, float] | None:
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
