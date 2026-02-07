"""Mixed Fish-Plant poker interaction system.

This package handles poker games between any combination of fish and plants.
Supports 2-6 players with a mix of species.
"""

from core.mixed_poker.interaction import MixedPokerInteraction
from core.mixed_poker.state import (MultiplayerGameState,
                                    MultiplayerPlayerContext)
from core.mixed_poker.types import (MixedPokerResult, MultiplayerBettingRound,
                                    Player)
from core.mixed_poker.utils import (
    check_poker_proximity, should_trigger_plant_poker_asexual_reproduction)

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
