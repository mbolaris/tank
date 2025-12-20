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
POKER_COOLDOWN = 60
MAX_PLAYERS = 6


# Primary PokerInteraction class - works with any PokerPlayer entities
PokerInteraction = MixedPokerInteraction

# Reproduction helpers
from core.constants import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD


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
    if player.poker_cooldown > 0:
        return False
        
    # Check same species (fish can only reproduce with fish, plants with plants)
    if player.species != opponent.species:
        return False
        
    return True


def should_offer_post_poker_reproduction(
    fish, opponent, is_winner: bool, energy_gained: float = 0.0
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
    from core.entities.base import LifeStage
    
    min_energy_for_reproduction = fish.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    if fish.energy < min_energy_for_reproduction:
        return False

    if fish.reproduction_cooldown > 0:
        return False

    if fish.life_stage.value < LifeStage.ADULT.value:
        return False

    if fish.species != opponent.species:
        return False

    return True


def calculate_house_cut(winner_size: float, net_gain: float) -> float:
    """Calculate house cut based on winner's size.

    Larger winners pay more: Size 0.35: 8%, Size 1.0: ~20%, Size 1.3: ~25%
    
    Args:
        winner_size: Size of the winning player
        net_gain: Net energy gain from the pot
        
    Returns:
        House cut amount (energy taken by the house)
    """
    from core.constants import (
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
    "should_offer_post_poker_reproduction",
    "calculate_house_cut",
    "check_poker_proximity",
]
