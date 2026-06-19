"""Inheritance and validation for per-kind code policy traits.

This module owns the genome fields that reference CodePool components
(movement/poker/soccer policy id + params): inheritance of a single policy
kind from two parents, parameter mutation, and field validation.

Extracted verbatim from core/genetics/behavioral.py (behavior-preserving
split). The behavioral module re-exports these names for backwards
compatibility.
"""

import random as pyrandom

from core.genetics.trait import GeneticTrait

# =============================================================================
# Code Policy Inheritance Constants
# =============================================================================
# Probability thresholds for code policy inheritance and mutation.

CODE_POLICY_DROP_PROBABILITY: float = 0.02  # 2% chance to drop code policy
CODE_POLICY_PARAM_MUTATION_RATE: float = 0.15  # 15% chance to mutate each param
CODE_POLICY_PARAM_MUTATION_STRENGTH: float = 0.1  # Gaussian sigma for param changes
CODE_POLICY_PARAM_MIN: float = -10.0  # Minimum allowed param value
CODE_POLICY_PARAM_MAX: float = 10.0  # Maximum allowed param value


def mutate_code_policy_params(
    params: dict[str, float] | None,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> dict[str, float] | None:
    """Mutate code policy parameters slightly.

    Each parameter has a chance to be mutated using Gaussian noise.
    Values are clamped to [CODE_POLICY_PARAM_MIN, CODE_POLICY_PARAM_MAX].
    """
    if params is None:
        return None

    mutated = dict(params)
    eff_mutation_rate = CODE_POLICY_PARAM_MUTATION_RATE * mutation_rate
    eff_strength = CODE_POLICY_PARAM_MUTATION_STRENGTH * mutation_strength

    # Iterate in sorted key order so RNG is consumed deterministically,
    # independent of dict insertion order (which can be hash-seed dependent
    # upstream). Same rationale as ComposableBehavior.mutate. See ADR-012.
    for key in sorted(mutated):
        if rng.random() < eff_mutation_rate:
            old_val = mutated[key]
            delta = rng.gauss(0, eff_strength)
            new_val = old_val + delta
            # Clamp to valid range
            new_val = max(CODE_POLICY_PARAM_MIN, min(CODE_POLICY_PARAM_MAX, new_val))
            mutated[key] = new_val

    return mutated


def inherit_single_policy(
    id_trait1: GeneticTrait[str | None] | None,
    id_trait2: GeneticTrait[str | None] | None,
    params_trait1: GeneticTrait[dict[str, float] | None] | None,
    params_trait2: GeneticTrait[dict[str, float] | None] | None,
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
    available_policies: list[str] | None = None,
) -> tuple[str | None, dict[str, float] | None]:
    """Inherit a single policy kind (id and params) from two parents.

    Args:
        id_trait1: First parent's policy ID trait
        id_trait2: Second parent's policy ID trait
        params_trait1: First parent's policy params trait
        params_trait2: Second parent's policy params trait
        weight1: How much parent1 contributes (0.0-1.0)
        mutation_rate: Base mutation probability
        mutation_strength: Mutation magnitude
        rng: Random number generator
        available_policies: Optional list of policy IDs to swap to during mutation

    Returns:
        Tuple of (component_id, params) for offspring
    """
    # Extract values
    id1 = id_trait1.value if id_trait1 and id_trait1.value else None
    id2 = id_trait2.value if id_trait2 and id_trait2.value else None
    params1 = params_trait1.value if params_trait1 and params_trait1.value else None
    params2 = params_trait2.value if params_trait2 and params_trait2.value else None

    # Both empty
    if id1 is None and id2 is None:
        return None, None

    # Choose parent's policy based on weight
    if id1 is not None and id2 is not None:
        if rng.random() < weight1:
            chosen_id, chosen_params = id1, params1
        else:
            chosen_id, chosen_params = id2, params2
    elif id1 is not None:
        # Only parent1 has this policy kind
        if rng.random() < weight1 or rng.random() < 0.3:  # Gene flow
            chosen_id, chosen_params = id1, params1
        else:
            return None, None
    else:
        # Only parent2 has this policy kind
        assert id2 is not None
        if rng.random() < (1 - weight1) or rng.random() < 0.3:  # Gene flow
            chosen_id, chosen_params = id2, params2
        else:
            return None, None

    # Chance to drop
    if rng.random() < CODE_POLICY_DROP_PROBABILITY * mutation_rate:
        return None, None

    # Mutation: chance to swap to a different available policy
    if available_policies and rng.random() < mutation_rate * 0.1:  # 10% of mutation rate
        # Pick a random policy from available ones
        new_id = rng.choice(available_policies)
        # Reset params for fresh start with new policy
        return new_id, None

    # Mutate params if present
    mutated_params = mutate_code_policy_params(chosen_params, mutation_rate, mutation_strength, rng)

    return chosen_id, mutated_params


def validate_policy_fields(
    policy_id: str | None,
    params: dict[str, float] | None,
    policy_kind: str = "policy",
) -> list[str]:
    """Validate policy id/params fields and return a list of issues.

    Validation rules:
    - params must have finite numbers, bounded in [CODE_POLICY_PARAM_MIN, CODE_POLICY_PARAM_MAX].

    Returns:
        List of issue strings (empty if valid).
    """
    import math

    issues: list[str] = []

    # Validate params if present
    if params is not None:
        if not isinstance(params, dict):
            issues.append(f"{policy_kind}_params must be a dict, got {type(params).__name__}")
        else:
            for key, val in params.items():
                if not isinstance(key, str):
                    issues.append(f"{policy_kind}_params key must be str, got {type(key).__name__}")
                if not isinstance(val, (int, float)):
                    issues.append(
                        f"{policy_kind}_params[{key!r}] must be numeric, got {type(val).__name__}"
                    )
                elif math.isnan(val) or math.isinf(val):
                    issues.append(f"{policy_kind}_params[{key!r}] must be finite, got {val}")
                elif val < CODE_POLICY_PARAM_MIN or val > CODE_POLICY_PARAM_MAX:
                    issues.append(
                        f"{policy_kind}_params[{key!r}]={val} out of range "
                        f"[{CODE_POLICY_PARAM_MIN}, {CODE_POLICY_PARAM_MAX}]"
                    )

    return issues


# Alias for migration support during transition
def validate_code_policy(
    kind: str | None,
    component_id: str | None,
    params: dict[str, float] | None,
) -> list[str]:
    """Validate code policy fields - migration alias for validate_policy_fields."""
    return validate_policy_fields(component_id, params, policy_kind=kind or "code_policy")
