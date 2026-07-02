"""Niche-based reproduction cost calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Fish

# Bounds of the multiplier returned by get_niche_cost_multiplier. Callers may
# use MIN_NICHE_COST_MULTIPLIER to rule out reproduction without paying for
# the population scan (a bank below base_cost * MIN can never be sufficient).
MIN_NICHE_COST_MULTIPLIER = 0.6
MAX_NICHE_COST_MULTIPLIER = 1.8


def get_niche_cost_multiplier(fish: Fish) -> float:
    """Calculate the reproduction energy cost multiplier based on behavioral phenotype frequency.

    Fish with rare behavioral combinations are subsidized (lower cost, down to 0.6x),
    while fish with dominant/over-represented behavioral combinations are taxed (higher cost, up to 1.8x).
    Only scales when the active fish population is at least 10.
    """
    from core.entities import Fish

    environment = getattr(fish, "environment", None)
    if environment is None:
        return 1.0

    agents = getattr(environment, "agents", None)
    if not agents:
        return 1.0

    # Get all active fish in the environment
    fish_list = [a for a in agents if isinstance(a, Fish)]
    N_total = len(fish_list)
    if N_total < 10:
        return 1.0

    # Get this fish's behavioral phenotype profile
    genome = getattr(fish, "genome", None)
    if genome is None:
        return 1.0
    behavioral = getattr(genome, "behavioral", None)
    if behavioral is None:
        return 1.0
    behavior_trait = getattr(behavioral, "behavior", None)
    if behavior_trait is None:
        return 1.0
    behavior = getattr(behavior_trait, "value", None)
    if behavior is None:
        return 1.0

    parent_tuple = (
        getattr(behavior, "threat_response", None),
        getattr(behavior, "food_approach", None),
        getattr(behavior, "social_mode", None),
        getattr(behavior, "poker_engagement", None),
    )

    N_same = 0
    for f in fish_list:
        f_genome = getattr(f, "genome", None)
        if f_genome is None:
            continue
        f_behavioral = getattr(f_genome, "behavioral", None)
        if f_behavioral is None:
            continue
        f_behavior_trait = getattr(f_behavioral, "behavior", None)
        if f_behavior_trait is None:
            continue
        f_behavior = getattr(f_behavior_trait, "value", None)
        if f_behavior is not None:
            f_tuple = (
                getattr(f_behavior, "threat_response", None),
                getattr(f_behavior, "food_approach", None),
                getattr(f_behavior, "social_mode", None),
                getattr(f_behavior, "poker_engagement", None),
            )
            if f_tuple == parent_tuple:
                N_same += 1

    if N_same == 0:
        return 1.0

    p = N_same / N_total
    # Cost scales from 0.6x (unique) to 1.8x (dominant)
    return float(max(MIN_NICHE_COST_MULTIPLIER, min(MAX_NICHE_COST_MULTIPLIER, 0.6 + 1.2 * p)))
