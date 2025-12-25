"""Unified poker interaction system.

This module provides a single entry point for poker games between any entities
that implement the PokerPlayer protocol (Fish, Plant, or future entity types).

The implementation is based on MixedPokerInteraction which handles 2-6 players
of any type using full Texas Hold'em with betting rounds.

Usage:
    from core.poker_interaction import PokerInteraction, PokerResult
    
    players = [fish1, fish2, plant1]  # Any PokerPlayer entities
    poker = PokerInteraction(players)
    if poker.can_play_poker():
        poker.play_poker()
        if poker.result:
            print(f"Winner: {poker.result.winner_id}")
"""

from typing import Optional

# Re-export the unified poker classes
from core.mixed_poker import (
    MixedPokerInteraction,
    MixedPokerResult as PokerResult,
    MultiplayerBettingRound as BettingRound,
    MultiplayerGameState as GameState,
    MultiplayerPlayerContext as PlayerContext,
)

# Also export utility types
from core.mixed_poker import Player

# Re-export participant manager for get_ready_players
from core.poker_participant_manager import get_ready_players

# Constants for poker games
MIN_ENERGY_TO_PLAY = 10.0
DEFAULT_BET_AMOUNT = 5.0
POKER_COOLDOWN = 30  # Reduced from 60 for faster poker turnaround
MAX_PLAYERS = 6


# Primary PokerInteraction class - works with any PokerPlayer entities
PokerInteraction = MixedPokerInteraction

# Reproduction helpers
import random

from core.config.fish import (
    POST_POKER_REPRODUCTION_ENERGY_THRESHOLD,
    POST_POKER_REPRODUCTION_LOSER_PROB,
    POST_POKER_REPRODUCTION_WINNER_PROB,
)


def _get_reproduction_cooldown(player: Player) -> int:
    component = getattr(player, "_reproduction_component", None)
    if component is not None:
        return component.reproduction_cooldown
    return getattr(player, "reproduction_cooldown", 0)


def should_trigger_reproduction(player: Player, opponent: Player) -> bool:
    """Check if reproduction should be triggered after poker.
    
    Both players must:
    - Have energy >= POST_POKER_REPRODUCTION_ENERGY_THRESHOLD of max
    - Be off cooldown (reproduction_cooldown <= 0)
    - Be same species
    
    Args:
        player: First player
        opponent: Second player
        
    Returns:
        True if reproduction conditions are met
    """
    # Check energy threshold
    if player.energy < player.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD:
        return False
    if opponent.energy < opponent.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD:
        return False
    
    # Check cooldown
    if _get_reproduction_cooldown(player) > 0:
        return False
    if _get_reproduction_cooldown(opponent) > 0:
        return False
        
    # Check same species (fish can only reproduce with fish, plants with plants)
    if player.species != opponent.species:
        return False
        
    return True


def is_post_poker_reproduction_eligible(fish, opponent) -> bool:
    """Check whether a fish can BE THE PARENT in post-poker reproduction.
    
    The parent (winner) must:
    - Have enough energy to produce offspring
    - Be off reproduction cooldown
    - Be an adult
    - Be same species as mate
    
    Note: This is for the fish that will actually produce the child and pay
    the energy cost. Use is_valid_reproduction_mate() for the other fish.
    """
    from core.entities.base import LifeStage

    min_energy_for_reproduction = fish.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    if fish.energy < min_energy_for_reproduction:
        return False

    if fish._reproduction_component.reproduction_cooldown > 0:
        return False

    if fish._lifecycle_component.life_stage.value < LifeStage.ADULT.value:
        return False

    if fish.species != opponent.species:
        return False

    return True


def is_valid_reproduction_mate(fish, parent) -> bool:
    """Check whether a fish can be a MATE (DNA donor) in reproduction.
    
    The mate only needs to:
    - Be an adult (capable of reproduction)
    - Be same species as parent
    
    The mate does NOT need:
    - High energy (they're just contributing DNA, not producing offspring)
    - To be off cooldown (only the parent goes on cooldown)
    """
    from core.entities.base import LifeStage

    if fish._lifecycle_component.life_stage.value < LifeStage.ADULT.value:
        return False

    if fish.species != parent.species:
        return False

    return True


def should_offer_post_poker_reproduction(
    fish,
    opponent,
    is_winner: bool,
    energy_gained: float = 0.0,
    rng: Optional[random.Random] = None,
) -> bool:
    """Check if fish should reproduce after poker (legacy signature).
    
    Args:
        fish: The fish to check
        opponent: The opponent fish
        is_winner: Whether fish won (unused, kept for compatibility)
        energy_gained: Energy gained (unused, kept for compatibility)
        
    Returns:
        True if reproduction conditions are met
    """
    if not is_post_poker_reproduction_eligible(fish, opponent):
        return False

    offer_prob = (
        POST_POKER_REPRODUCTION_WINNER_PROB
        if is_winner
        else POST_POKER_REPRODUCTION_LOSER_PROB
    )
    rng = rng if rng is not None else random
    return rng.random() < offer_prob


def calculate_house_cut(winner_size: float, net_gain: float) -> float:
    """Calculate house cut based on winner's size.

    Larger winners pay more: Size 0.35: 8%, Size 1.0: ~20%, Size 1.3: ~25%
    
    Args:
        winner_size: Size of the winning player
        net_gain: Net energy gain from the pot
        
    Returns:
        House cut amount (energy taken by the house)
    """
    from core.config.poker import (
        POKER_BET_MIN_SIZE,
        POKER_HOUSE_CUT_MIN_PERCENTAGE,
        POKER_HOUSE_CUT_SIZE_MULTIPLIER,
    )

    house_cut_percentage = POKER_HOUSE_CUT_MIN_PERCENTAGE + max(
        0, (winner_size - POKER_BET_MIN_SIZE) * POKER_HOUSE_CUT_SIZE_MULTIPLIER
    )
    # Clamp to 8-25% range
    house_cut_percentage = min(house_cut_percentage, 0.25)
    # Never exceed the winner's profit
    return min(net_gain * house_cut_percentage, net_gain)


def check_poker_proximity(
    entity1, entity2, min_distance: float = 40.0, max_distance: float = 80.0
) -> bool:
    """Check if two entities are close enough for poker but not touching.

    Poker triggers when entities are near each other but not overlapping.

    Args:
        entity1: First entity (any with pos, width, height)
        entity2: Second entity
        min_distance: Minimum center-to-center distance
        max_distance: Maximum center-to-center distance for poker trigger

    Returns:
        True if they are in the poker proximity zone
    """
    # Calculate centers
    e1_cx = entity1.pos.x + entity1.width / 2
    e1_cy = entity1.pos.y + entity1.height / 2
    e2_cx = entity2.pos.x + entity2.width / 2
    e2_cy = entity2.pos.y + entity2.height / 2

    dx = e1_cx - e2_cx
    dy = e1_cy - e2_cy
    distance_sq = dx * dx + dy * dy

    return min_distance * min_distance < distance_sq <= max_distance * max_distance


def filter_mutually_proximate(
    entities: list,
    max_distance: float,
) -> list:
    """Filter entities to only those where ALL are within max_distance of each other.

    This prevents chain-connected entities (A near B, B near C, but A far from C)
    from ending up in the same poker game.

    The algorithm finds the largest subset of entities where every pair is within
    max_distance of each other. Uses a greedy approach that works well for the
    small group sizes typical in poker games.

    PERFORMANCE OPTIMIZATIONS:
    - Use squared distances throughout (avoid sqrt)
    - Use 2D list instead of dict (no hash/get overhead)
    - Pre-cache entity positions
    - Early exit when best possible group is found
    - Inline distance calculations

    Args:
        entities: List of entities with pos, width, and height attributes
        max_distance: Maximum distance between any two entities

    Returns:
        Largest subset where all entities are mutually within max_distance
    """
    n = len(entities)
    if n <= 2:
        # For 2 or fewer, they were already verified as proximate
        return list(entities)

    # Pre-compute squared max distance (avoid sqrt entirely)
    max_dist_sq = max_distance * max_distance

    # Pre-cache entity center positions for faster access
    positions = [
        (e.pos.x + e.width * 0.5, e.pos.y + e.height * 0.5)
        for e in entities
    ]

    # OPTIMIZATION: Use 2D list instead of dict for O(1) access without hash overhead
    # Build adjacency matrix as boolean: True = within distance
    adjacent = [[False] * n for _ in range(n)]

    for i in range(n):
        x1, y1 = positions[i]
        for j in range(i + 1, n):
            x2, y2 = positions[j]
            dx = x1 - x2
            dy = y1 - y2
            if dx * dx + dy * dy <= max_dist_sq:
                adjacent[i][j] = True
                adjacent[j][i] = True  # Symmetric

    # Simple greedy approach: start with each entity, build largest valid group
    best_group: list = []
    best_size = 0

    for start_idx in range(n):
        # Early exit: can't beat current best if remaining entities aren't enough
        if n - start_idx <= best_size:
            break

        group = [start_idx]
        adj_row = adjacent[start_idx]  # Cache row for start entity

        for candidate_idx in range(start_idx + 1, n):
            # Quick check: must be adjacent to start entity
            if not adj_row[candidate_idx]:
                continue

            # Check if candidate is within distance of ALL current group members
            can_add = True
            for member_idx in group:
                if not adjacent[member_idx][candidate_idx]:
                    can_add = False
                    break
            if can_add:
                group.append(candidate_idx)

        if len(group) > best_size:
            best_group = group
            best_size = len(group)
            # Early exit if we found a group with all remaining entities
            if best_size == n - start_idx:
                break

    return [entities[i] for i in best_group]


__all__ = [
    "PokerInteraction",
    "PokerResult", 
    "BettingRound",
    "GameState",
    "PlayerContext",
    "Player",
    "MIN_ENERGY_TO_PLAY",
    "DEFAULT_BET_AMOUNT",
    "POKER_COOLDOWN",
    "MAX_PLAYERS",
    "get_ready_players",
    "should_trigger_reproduction",
    "is_post_poker_reproduction_eligible",
    "is_valid_reproduction_mate",
    "should_offer_post_poker_reproduction",
    "calculate_house_cut",
    "check_poker_proximity",
    "filter_mutually_proximate",
]
