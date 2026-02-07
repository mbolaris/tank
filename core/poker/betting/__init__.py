"""
Betting module for Texas Hold'em poker.

This package provides betting-related components including actions,
rounds, and decision-making logic.
"""

from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import (
    AGGRESSION_HIGH,
    AGGRESSION_LOW,
    AGGRESSION_MEDIUM,
    decide_action,
)

__all__ = [
    "AGGRESSION_HIGH",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
    "BettingAction",
    "BettingRound",
    "decide_action",
]
