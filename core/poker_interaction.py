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
    MixedPokerInteraction as PokerInteraction,
    MixedPokerResult as PokerResult,
    MultiplayerBettingRound as BettingRound,
    MultiplayerGameState as GameState,
    MultiplayerPlayerContext as PlayerContext,
)

# Also export utility types
from core.mixed_poker import Player

# Reproduction helpers (moved from fish_poker.py)
from core.constants import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD


def should_trigger_reproduction(player: Player, opponent: Player) -> bool:
    """Check if reproduction should be triggered after poker.
    
    Unified reproduction check for any PokerPlayer entities.
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


__all__ = [
    "PokerInteraction",
    "PokerResult", 
    "BettingRound",
    "GameState",
    "PlayerContext",
    "Player",
    "should_trigger_reproduction",
]
