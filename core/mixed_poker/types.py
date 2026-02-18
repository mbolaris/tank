"""Poker game types and result dataclasses.

This module contains the data structures used by the mixed poker system.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant
    from core.poker.betting.actions import BettingAction
    from core.poker.core.hand import PokerHand

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
    loser_ids: list[int]
    loser_types: list[str]
    loser_hands: list[Optional["PokerHand"]]
    energy_transferred: float
    total_pot: float
    house_cut: float
    is_tie: bool
    tied_player_ids: list[int]
    player_count: int
    fish_count: int
    plant_count: int
    won_by_fold: bool = False
    total_rounds: int = 4
    players_folded: list[bool] = field(default_factory=list)
    betting_history: list[tuple[int, "BettingAction", float]] = field(default_factory=list)
    # Dealer/button position (0-indexed) from the game state.
    button_position: int = 0

    @property
    def final_pot(self) -> float:
        return self.total_pot

    @property
    def player1_folded(self) -> bool:
        return bool(self.players_folded[0]) if len(self.players_folded) > 0 else False

    @property
    def player2_folded(self) -> bool:
        return bool(self.players_folded[1]) if len(self.players_folded) > 1 else False
