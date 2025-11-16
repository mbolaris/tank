"""
Poker game engine for fish interactions.

This module implements a simplified Texas Hold'em poker system for determining
outcomes of fish-to-fish encounters. When two fish collide, they play a hand
of poker to determine energy transfer.
"""

import random
from dataclasses import dataclass
from typing import Tuple
from enum import IntEnum


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
    """Represents a poker hand and its rank."""
    hand_type: str
    rank_value: HandRank
    description: str

    def beats(self, other: 'PokerHand') -> bool:
        """Check if this hand beats another hand."""
        return self.rank_value > other.rank_value

    def __str__(self) -> str:
        return f"{self.description} (rank {self.rank_value})"


class PokerEngine:
    """Core poker game logic for fish interactions."""

    # Probability distribution for poker hands (approximating Texas Hold'em)
    # Format: (cumulative_probability, HandRank, description_template)
    HAND_PROBABILITIES = [
        (0.501, HandRank.HIGH_CARD, "High Card"),
        (0.924, HandRank.PAIR, "Pair"),
        (0.971, HandRank.TWO_PAIR, "Two Pair"),
        (0.993, HandRank.THREE_OF_KIND, "Three of a Kind"),
        (0.997, HandRank.STRAIGHT, "Straight"),
        (0.9985, HandRank.FLUSH, "Flush"),
        (0.9997, HandRank.FULL_HOUSE, "Full House"),
        (0.99994, HandRank.FOUR_OF_KIND, "Four of a Kind"),
        (0.999985, HandRank.STRAIGHT_FLUSH, "Straight Flush"),
        (1.0, HandRank.ROYAL_FLUSH, "Royal Flush"),
    ]

    @staticmethod
    def generate_hand() -> PokerHand:
        """
        Generate a random poker hand using realistic probabilities.

        Returns:
            PokerHand with appropriate rank and description
        """
        roll = random.random()

        for prob, rank, description in PokerEngine.HAND_PROBABILITIES:
            if roll < prob:
                return PokerHand(
                    hand_type=rank.name.lower(),
                    rank_value=rank,
                    description=description
                )

        # Fallback (should never reach here)
        return PokerHand(
            hand_type="high_card",
            rank_value=HandRank.HIGH_CARD,
            description="High Card"
        )

    @staticmethod
    def resolve_bet(
        hand1: PokerHand,
        hand2: PokerHand,
        bet1_amount: float,
        bet2_amount: float
    ) -> Tuple[float, float]:
        """
        Resolve a poker bet between two hands.

        Args:
            hand1: First player's hand
            hand2: Second player's hand
            bet1_amount: Amount wagered by first player
            bet2_amount: Amount wagered by second player

        Returns:
            Tuple of (player1_winnings, player2_winnings)
            This is a zero-sum game, so winnings sum to 0
        """
        # Determine winner
        if hand1.beats(hand2):
            # Player 1 wins, takes both bets
            return (bet2_amount, -bet2_amount)
        elif hand2.beats(hand1):
            # Player 2 wins, takes both bets
            return (-bet1_amount, bet1_amount)
        else:
            # Tie - no money changes hands
            return (0.0, 0.0)

    @staticmethod
    def simulate_game(bet_amount: float = 10.0) -> Tuple[PokerHand, PokerHand, float, float]:
        """
        Simulate a complete poker game between two players.

        Args:
            bet_amount: Amount each player bets (assumes equal bets)

        Returns:
            Tuple of (hand1, hand2, player1_winnings, player2_winnings)
        """
        hand1 = PokerEngine.generate_hand()
        hand2 = PokerEngine.generate_hand()
        winnings1, winnings2 = PokerEngine.resolve_bet(
            hand1, hand2, bet_amount, bet_amount
        )
        return hand1, hand2, winnings1, winnings2


# Example usage and testing
if __name__ == "__main__":
    print("Poker Engine Test")
    print("=" * 50)

    # Test hand generation distribution
    print("\nGenerating 1000 hands to test distribution:")
    hand_counts = {rank: 0 for rank in HandRank}
    for _ in range(1000):
        hand = PokerEngine.generate_hand()
        hand_counts[hand.rank_value] += 1

    for rank in HandRank:
        count = hand_counts[rank]
        print(f"{rank.name:20s}: {count:4d} ({count/10:.1f}%)")

    # Test a few games
    print("\n" + "=" * 50)
    print("Simulating 5 poker games:")
    print("=" * 50)
    for i in range(5):
        hand1, hand2, win1, win2 = PokerEngine.simulate_game(bet_amount=10.0)
        print(f"\nGame {i+1}:")
        print(f"  Player 1: {hand1}")
        print(f"  Player 2: {hand2}")
        if win1 > 0:
            print(f"  Winner: Player 1 (+{win1} energy)")
        elif win2 > 0:
            print(f"  Winner: Player 2 (+{win2} energy)")
        else:
            print(f"  Result: Tie (no energy transfer)")
