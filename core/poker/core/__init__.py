"""
Core poker components for Texas Hold'em.

This package contains the fundamental poker building blocks: cards, hands,
and game state.
"""

from core.poker.core.cards import Card, Deck, Rank, Suit, get_card
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import HandRank, PokerHand

# Re-export from betting and simulation for convenience
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import (
    AGGRESSION_HIGH,
    AGGRESSION_LOW,
    AGGRESSION_MEDIUM,
    decide_action,
)
from core.poker.evaluation.hand_evaluator import evaluate_hand, _evaluate_five_cards
from core.poker.simulation.engine import (
    finalize_pot,
    resolve_bet,
    simulate_game,
    simulate_multi_round_game,
)

__all__ = [
    # Cards
    "Card",
    "Deck",
    "Rank",
    "Suit",
    "get_card",
    # Hands
    "HandRank",
    "PokerHand",
    # Game State
    "PokerGameState",
    # Betting
    "BettingAction",
    "BettingRound",
    "AGGRESSION_HIGH",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
    "decide_action",
    # Evaluation
    "evaluate_hand",
    "_evaluate_five_cards",
    # Simulation
    "finalize_pot",
    "resolve_bet",
    "simulate_game",
    "simulate_multi_round_game",
]
