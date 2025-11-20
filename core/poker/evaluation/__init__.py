"""
Poker hand strength evaluation and decision support.

This package provides tools for evaluating hand strength, calculating pot odds,
and recommending actions based on poker theory.
"""

from core.poker.evaluation.strength import (
    calculate_pot_odds,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)

__all__ = [
    "calculate_pot_odds",
    "evaluate_starting_hand_strength",
    "get_action_recommendation",
]
