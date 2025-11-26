"""
Betting actions and rounds for Texas Hold'em poker.

This module defines the betting round phases and possible player actions.
"""

from enum import IntEnum


class BettingRound(IntEnum):
    """Betting rounds in Texas Hold'em."""

    PRE_FLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4


class BettingAction(IntEnum):
    """Possible betting actions."""

    FOLD = 0
    CHECK = 1
    CALL = 2
    RAISE = 3
