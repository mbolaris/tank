"""Utility functions for mixed poker interactions."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Fish
    from core.mixed_poker.types import Player


def check_poker_proximity(
    entity1: "Player", entity2: "Player", min_distance: float, max_distance: float
) -> bool:
    """Check if two entities are in poker proximity (close but not touching).

    Args:
        entity1: First entity (Fish or Plant)
        entity2: Second entity (Fish or Plant)
        min_distance: Minimum center-to-center distance
        max_distance: Maximum center-to-center distance

    Returns:
        True if entities are in the poker proximity zone
    """
    # Calculate centers
    e1_cx = entity1.pos.x + entity1.width / 2
    e1_cy = entity1.pos.y + entity1.height / 2
    e2_cx = entity2.pos.x + entity2.width / 2
    e2_cy = entity2.pos.y + entity2.height / 2

    dx = e1_cx - e2_cx
    dy = e1_cy - e2_cy
    distance_sq = dx * dx + dy * dy

    min_dist_sq = min_distance * min_distance
    max_dist_sq = max_distance * max_distance

    return min_dist_sq < distance_sq <= max_dist_sq


def should_trigger_plant_poker_asexual_reproduction(fish: "Fish") -> bool:
    """Check if a fish should trigger asexual reproduction after winning against plants.

    When a fish wins a poker hand against only plant opponents (no other fish),
    they get the opportunity to reproduce asexually. This rewards fish that
    successfully "eat" plants through poker.

    Conditions:
    - Fish must have ≥40% of max energy (POST_POKER_REPRODUCTION_ENERGY_THRESHOLD)
    - Fish must not be pregnant
    - Fish must be off reproduction cooldown
    - Fish must be adult life stage

    Args:
        fish: The fish that won the poker game

    Returns:
        True if asexual reproduction should be triggered
    """
    from core.config.fish import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    from core.entities.base import LifeStage

    # Check energy threshold
    min_energy_for_reproduction = fish.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    if fish.energy < min_energy_for_reproduction:
        return False

    # Check off cooldown
    if fish._reproduction_component.reproduction_cooldown > 0:
        return False

    # Check adult life stage (only adults can reproduce)
    if fish._lifecycle_component.life_stage != LifeStage.ADULT:
        return False

    return True
