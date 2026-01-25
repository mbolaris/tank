"""
Poker game state tracking for Texas Hold'em.

This module contains the PokerGameState class which tracks the complete
state of a multi-round Texas Hold'em poker game.
"""

import random
from typing import List, Optional, Tuple

from core.poker.betting.actions import BettingRound
from core.poker.core.cards import Card, Deck
from core.poker.core.hand import PokerHand


class PokerGameState:
    """Tracks the state of a multi-round Texas Hold'em poker game."""

    current_round: int = 1  # BettingRound enum value
    pot: float = 0.0
    player1_total_bet: float = 0.0
    player2_total_bet: float = 0.0
    player1_current_bet: float = 0.0
    player2_current_bet: float = 0.0
    player1_folded: bool = False
    player2_folded: bool = False
    player1_hole_cards: List[Card] = []
    player2_hole_cards: List[Card] = []
    community_cards: List[Card] = []  # 0 pre-flop, 3 after flop, 4 after turn, 5 after river
    player1_hand: Optional[PokerHand] = None  # Evaluated at showdown
    player2_hand: Optional[PokerHand] = None  # Evaluated at showdown
    betting_history: List[Tuple[int, int, float]] = []  # (player, action, amount)
    button_position: int = 1  # Which player is on the button (1 or 2)
    small_blind: float = 0.0
    big_blind: float = 0.0
    deck: Deck
    min_raise: float = 0.0  # Minimum raise amount (Texas Hold'em rule)
    last_raise_amount: float = 0.0  # Size of the last raise (to calculate next min raise)

    def __init__(
        self,
        small_blind: float = 2.5,
        big_blind: float = 5.0,
        button_position: int = 1,
        rng: Optional[random.Random] = None,
    ):
        self.current_round = BettingRound.PRE_FLOP
        self.pot = 0.0
        self.player1_total_bet = 0.0
        self.player2_total_bet = 0.0
        self.player1_current_bet = 0.0
        self.player2_current_bet = 0.0
        self.player1_folded = False
        self.player2_folded = False
        self.player1_hole_cards = []
        self.player2_hole_cards = []
        self.community_cards = []
        self.player1_hand = None
        self.player2_hand = None
        self.betting_history = []
        self.button_position = button_position
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck(rng=rng)
        # Min raise starts at big blind and updates with each raise
        self.min_raise = big_blind
        self.last_raise_amount = big_blind  # BB counts as the first "raise" pre-flop

    def add_to_pot(self, amount: float):
        """Add money to the pot."""
        self.pot += amount

    def player_bet(self, player: int, amount: float):
        """Record a player's bet."""
        if player == 1:
            self.player1_current_bet += amount
            self.player1_total_bet += amount
        else:
            self.player2_current_bet += amount
            self.player2_total_bet += amount
        self.add_to_pot(amount)

    def deal_cards(self):
        """Deal hole cards alternating between players (P1, P2, P1, P2)."""
        self.player1_hole_cards = []
        self.player2_hole_cards = []

        # Card 1 to each player
        self.player1_hole_cards.append(self.deck.deal_one())
        self.player2_hole_cards.append(self.deck.deal_one())
        # Card 2 to each player
        self.player1_hole_cards.append(self.deck.deal_one())
        self.player2_hole_cards.append(self.deck.deal_one())

    def deal_flop(self):
        """Deal the flop (3 community cards)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.extend(self.deck.deal(3))

    def deal_turn(self):
        """Deal the turn (4th community card)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.append(self.deck.deal_one())

    def deal_river(self):
        """Deal the river (5th community card)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.append(self.deck.deal_one())

    def advance_round(self):
        """Move to the next betting round and deal appropriate community cards."""

        if self.current_round < BettingRound.SHOWDOWN:
            self.current_round = BettingRound(self.current_round + 1)

            # Deal community cards based on new round
            if self.current_round == BettingRound.FLOP:
                self.deal_flop()
            elif self.current_round == BettingRound.TURN:
                self.deal_turn()
            elif self.current_round == BettingRound.RIVER:
                self.deal_river()

            # Reset current round bets
            self.player1_current_bet = 0.0
            self.player2_current_bet = 0.0

            # Reset minimum raise to big blind for the new round
            self.min_raise = self.big_blind
            self.last_raise_amount = self.big_blind

    def is_betting_complete(self) -> bool:
        """Check if betting is complete for current round.

        Only consider the current round's state: if both players have
        matched bets then betting for the round is complete. The
        simulation loop handles the requirement that players must have
        had an opportunity to act (e.g. `actions_this_round >= 2`).
        """
        # If bets aren't equal, betting is not complete
        if self.player1_current_bet != self.player2_current_bet:
            return False

        # Bets are equal — consider the round complete. The engine's
        # outer loop enforces the "both have acted" rule.
        return True

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if someone folded, None otherwise."""
        if self.player1_folded:
            return 2
        elif self.player2_folded:
            return 1
        return None
