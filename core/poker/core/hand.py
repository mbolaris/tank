"""
Poker hand representation and ranking for Texas Hold'em.

This module defines poker hand types and provides hand comparison logic.
"""

from dataclasses import dataclass, field
from enum import IntEnum

from core.poker.core.cards import Card


class HandRank(IntEnum):
    """Poker hand rankings from weakest to strongest."""

    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


@dataclass
class PokerHand:
    """Represents a poker hand and its rank with kickers."""

    hand_type: str
    rank_value: HandRank
    description: str
    cards: list[Card] = field(default_factory=list)
    primary_ranks: list[int] = field(default_factory=list)
    kickers: list[int] = field(default_factory=list)

    def beats(self, other: "PokerHand") -> bool:
        """Check if this hand beats another hand, including kicker comparison."""
        if self.rank_value != other.rank_value:
            return self.rank_value > other.rank_value

        for my_rank, their_rank in zip(self.primary_ranks, other.primary_ranks):
            if my_rank != their_rank:
                return my_rank > their_rank

        for my_kicker, their_kicker in zip(self.kickers, other.kickers):
            if my_kicker != their_kicker:
                return my_kicker > their_kicker

        return False

    def ties(self, other: "PokerHand") -> bool:
        """Check if this hand ties with another hand."""
        if self.rank_value != other.rank_value:
            return False
        if self.primary_ranks != other.primary_ranks:
            return False
        return self.kickers == other.kickers

    def __str__(self) -> str:
        return f"{self.description} (rank {self.rank_value})"
