"""Poker game types and result dataclasses.

This module contains the data structures used by the mixed poker system.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant
    from core.poker.betting.actions import BettingAction
    from core.poker_interaction import PokerHand

Player = Union["Fish", "Plant"]


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
    total_pot: float
    house_cut: float
    is_tie: bool
    tied_player_ids: List[int]
    player_count: int
    fish_count: int
    plant_count: int
    won_by_fold: bool = False
    total_rounds: int = 4
    players_folded: List[bool] = field(default_factory=list)
    betting_history: List[Tuple[int, "BettingAction", float]] = field(default_factory=list)
