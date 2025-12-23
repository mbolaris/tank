"""Poker game types and result dataclasses.

This module contains the data structures used by the mixed poker system.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.poker_interaction import PokerHand
    from core.poker.betting.actions import BettingAction


class MultiplayerBettingRound(IntEnum):
    """Betting rounds in Texas Hold'em."""
    PRE_FLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4


@dataclass
class MixedPokerResult:
    """Result of a mixed poker game."""
    winner_id: int
    winner_type: str  # "fish" or "plant"
    winner_hand: Optional["PokerHand"]
    loser_ids: List[int]
    loser_types: List[str]
    loser_hands: List[Optional["PokerHand"]]
    energy_transferred: float
    message: str
    is_tie: bool
    fish_count: int
    plant_count: int
    won_by_fold: bool = False
    total_rounds: int = 4
    players_folded: List[bool] = field(default_factory=list)
    betting_history: List[Tuple[int, "BettingAction", float]] = field(default_factory=list)
    house_cut: float = 0.0
