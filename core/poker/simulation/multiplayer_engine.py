"""
Multiplayer poker game simulation for Texas Hold'em (3+ players).

This module is a thin wrapper over hand_engine to preserve the legacy API.
"""

import random
from typing import TYPE_CHECKING, List, Optional

from core.poker.simulation.hand_engine import (MultiplayerGameState,
                                               MultiplayerPlayerContext,
                                               simulate_hand)

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm


def simulate_multiplayer_game(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: Optional[List[float]] = None,
    player_strategies: Optional[List[Optional["PokerStrategyAlgorithm"]]] = None,
    button_position: int = 0,
    rng: Optional[random.Random] = None,
) -> MultiplayerGameState:
    """Simulate a complete multiplayer Texas Hold'em poker game with blinds."""
    if num_players < 3:
        raise ValueError("Multiplayer game requires at least 3 players")

    return simulate_hand(
        num_players=num_players,
        initial_bet=initial_bet,
        player_energies=player_energies,
        player_aggressions=player_aggressions,
        player_strategies=player_strategies,
        button_position=button_position,
        rng=rng,
    )


__all__ = [
    "MultiplayerGameState",
    "MultiplayerPlayerContext",
    "simulate_multiplayer_game",
]
