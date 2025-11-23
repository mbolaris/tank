"""
Card and deck classes for Texas Hold'em poker.

This module provides the fundamental card structures and deck operations
needed for poker games.
"""

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import List


class Suit(IntEnum):
    """Card suits."""

    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


class Rank(IntEnum):
    """Card ranks (2-14, where 14 is Ace)."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass(frozen=True)
class Card:
    """Represents a single playing card."""

    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        rank_names = {
            2: "2",
            3: "3",
            4: "4",
            5: "5",
            6: "6",
            7: "7",
            8: "8",
            9: "9",
            10: "T",
            11: "J",
            12: "Q",
            13: "K",
            14: "A",
        }
        suit_names = {0: "♣", 1: "♦", 2: "♥", 3: "♠"}
        return f"{rank_names[self.rank]}{suit_names[self.suit]}"

    def __lt__(self, other: "Card") -> bool:
        return self.rank < other.rank


# Pre-create all 52 cards once at module load - shared card cache
# Maps (rank_int, suit_int) -> Card to avoid repeated Enum/Card construction
_CARD_CACHE: dict = {(r, s): Card(Rank(r), Suit(s)) for r in range(2, 15) for s in range(4)}


def get_card(rank: int, suit: int) -> Card:
    """Get a pre-cached Card object for the given rank and suit integers."""
    return _CARD_CACHE[(rank, suit)]


class Deck:
    """52-card deck for Texas Hold'em."""

    # Pre-create all 52 cards once at module load to avoid repeated Enum construction
    _TEMPLATE_DECK: List[Card] = list(_CARD_CACHE.values())

    def __init__(self):
        """Initialize and shuffle a standard 52-card deck."""
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """Reset and shuffle the deck."""
        # Copy from pre-created template instead of constructing new Cards
        self.cards = self._TEMPLATE_DECK.copy()
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> List[Card]:
        """Deal cards from the deck."""
        if count > len(self.cards):
            raise ValueError("Not enough cards in deck")
        dealt = self.cards[:count]
        self.cards = self.cards[count:]
        return dealt

    def deal_one(self) -> Card:
        """Deal a single card."""
        return self.deal(1)[0]
