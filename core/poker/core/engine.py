"""
Poker game engine - re-exports for backward compatibility.

This module re-exports symbols from their canonical locations for any
legacy imports. New code should import directly from:
- core.poker.betting: BettingAction, BettingRound, decide_action, AGGRESSION_*
- core.poker.evaluation: evaluate_hand, evaluate_hand_cached
- core.poker.simulation: simulate_multi_round_game, simulate_game, finalize_pot, resolve_bet
- core.poker.core.game_state: PokerGameState
- core.poker.core.hand: PokerHand, HandRank
- core.poker.core.cards: Card, Deck, Rank, Suit
"""

# Re-export all public symbols for backward compatibility
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import (
    AGGRESSION_HIGH,
    AGGRESSION_LOW,
    AGGRESSION_MEDIUM,
    decide_action,
)
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import HandRank, PokerHand
from core.poker.evaluation.hand_evaluator import (
    _evaluate_five_cards,
    evaluate_hand,
    evaluate_hand_cached,
)
from core.poker.simulation.engine import (
    finalize_pot,
    resolve_bet,
    simulate_game,
    simulate_multi_round_game,
)

__all__ = [
    # Enums
    "BettingAction",
    "BettingRound",
    "HandRank",
    # Classes
    "PokerGameState",
    "PokerHand",
    # Functions
    "decide_action",
    "evaluate_hand",
    "evaluate_hand_cached",
    "finalize_pot",
    "resolve_bet",
    "simulate_game",
    "simulate_multi_round_game",
    "_evaluate_five_cards",
    # Constants
    "AGGRESSION_HIGH",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
]
