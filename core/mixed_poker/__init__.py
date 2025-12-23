"""Mixed poker interaction package.

This package handles poker games between any combination of fish and plants.
Supports 2-6 players with a mix of species.

For backward compatibility, this module re-exports all public symbols
from the original implementation.
"""

# Re-export everything from the implementation file for backward compatibility
from core.mixed_poker_impl import (
    MixedPokerInteraction,
    MixedPokerResult,
    MultiplayerBettingRound,
    MultiplayerGameState,
    MultiplayerPlayerContext,
    Player,
    check_poker_proximity,
    should_trigger_plant_poker_asexual_reproduction,
)

__all__ = [
    "MixedPokerInteraction",
    "MixedPokerResult",
    "MultiplayerBettingRound",
    "MultiplayerGameState",
    "MultiplayerPlayerContext",
    "Player",
    "check_poker_proximity",
    "should_trigger_plant_poker_asexual_reproduction",
]
