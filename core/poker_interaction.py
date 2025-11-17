"""
Poker game engine for fish interactions.

This module implements a simplified Texas Hold'em poker system for determining
outcomes of fish-to-fish encounters. When two fish collide, they play a hand
of poker to determine energy transfer.

Updated to support multiple betting rounds and folding.
"""

import random
from dataclasses import dataclass
from typing import Tuple, Optional, List
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


@dataclass
class PokerGameState:
    """Tracks the state of a multi-round poker game."""
    current_round: BettingRound
    pot: float
    player1_total_bet: float
    player2_total_bet: float
    player1_current_bet: float  # Bet in current round
    player2_current_bet: float  # Bet in current round
    player1_folded: bool
    player2_folded: bool
    player1_hand: Optional[PokerHand]
    player2_hand: Optional[PokerHand]
    betting_history: List[Tuple[int, BettingAction, float]]  # (player, action, amount)

    def __init__(self):
        self.current_round = BettingRound.PRE_FLOP
        self.pot = 0.0
        self.player1_total_bet = 0.0
        self.player2_total_bet = 0.0
        self.player1_current_bet = 0.0
        self.player2_current_bet = 0.0
        self.player1_folded = False
        self.player2_folded = False
        self.player1_hand = None
        self.player2_hand = None
        self.betting_history = []

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

    def advance_round(self):
        """Move to the next betting round."""
        if self.current_round < BettingRound.SHOWDOWN:
            self.current_round = BettingRound(self.current_round + 1)
            # Reset current round bets
            self.player1_current_bet = 0.0
            self.player2_current_bet = 0.0

    def is_betting_complete(self) -> bool:
        """Check if betting is complete for current round."""
        # Betting is complete if bets are equal and both players have acted
        return (self.player1_current_bet == self.player2_current_bet and
                len([h for h in self.betting_history
                     if h[0] in [1, 2]]) >= 2)

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if someone folded, None otherwise."""
        if self.player1_folded:
            return 2
        elif self.player2_folded:
            return 1
        return None


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

    # Aggression factors for betting decisions
    # Higher values = more aggressive (more likely to raise/call)
    AGGRESSION_LOW = 0.3
    AGGRESSION_MEDIUM = 0.6
    AGGRESSION_HIGH = 0.9

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
    def decide_action(
        hand: PokerHand,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        aggression: float = AGGRESSION_MEDIUM
    ) -> Tuple[BettingAction, float]:
        """
        Decide what action to take based on hand strength and game state.

        Args:
            hand: Player's poker hand
            current_bet: Player's current bet this round
            opponent_bet: Opponent's current bet this round
            pot: Current pot size
            player_energy: Player's available energy
            aggression: Aggression factor (0-1, higher = more aggressive)

        Returns:
            Tuple of (action, bet_amount)
        """
        # Calculate how much needs to be called
        call_amount = opponent_bet - current_bet

        # Can't bet more than available energy
        if call_amount > player_energy:
            # Must fold if can't afford to call
            return (BettingAction.FOLD, 0.0)

        # Determine hand strength category
        hand_strength = hand.rank_value

        # Strong hands (flush or better)
        if hand_strength >= HandRank.FLUSH:
            if call_amount == 0:
                # No bet to call - raise most of the time
                if random.random() < 0.8:
                    raise_amount = min(pot * 0.5, player_energy * 0.3)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - call or raise
                if random.random() < aggression:
                    # Raise
                    raise_amount = min(call_amount * 2, player_energy * 0.4)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    # Call
                    return (BettingAction.CALL, call_amount)

        # Medium hands (pair through straight)
        elif hand_strength >= HandRank.PAIR:
            if call_amount == 0:
                # No bet - check or small raise
                if random.random() < aggression * 0.6:
                    raise_amount = min(pot * 0.3, player_energy * 0.2)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - fold, call, or raise based on bet size and aggression
                pot_odds = call_amount / (pot + call_amount) if pot > 0 else 1.0

                # More likely to fold if bet is large relative to pot
                if pot_odds > 0.5 and random.random() > aggression:
                    return (BettingAction.FOLD, 0.0)
                elif random.random() < aggression * 0.4:
                    # Sometimes raise with medium hands
                    raise_amount = min(call_amount * 1.5, player_energy * 0.25)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    # Usually call
                    return (BettingAction.CALL, call_amount)

        # Weak hands (high card)
        else:
            if call_amount == 0:
                # No bet - usually check, rarely bluff
                if random.random() < aggression * 0.2:
                    # Bluff
                    raise_amount = min(pot * 0.4, player_energy * 0.15)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - usually fold, rarely bluff call
                if random.random() < aggression * 0.15:
                    # Bluff call
                    return (BettingAction.CALL, call_amount)
                else:
                    return (BettingAction.FOLD, 0.0)

    @staticmethod
    def simulate_multi_round_game(
        initial_bet: float,
        player1_energy: float,
        player2_energy: float,
        player1_aggression: float = AGGRESSION_MEDIUM,
        player2_aggression: float = AGGRESSION_MEDIUM
    ) -> PokerGameState:
        """
        Simulate a complete multi-round poker game with folding.

        Args:
            initial_bet: Starting bet amount (ante)
            player1_energy: Player 1's available energy
            player2_energy: Player 2's available energy
            player1_aggression: Player 1's aggression factor
            player2_aggression: Player 2's aggression factor

        Returns:
            PokerGameState with final game results
        """
        game_state = PokerGameState()

        # Generate hands at the start
        game_state.player1_hand = PokerEngine.generate_hand()
        game_state.player2_hand = PokerEngine.generate_hand()

        # Place initial antes
        ante = min(initial_bet, player1_energy, player2_energy)
        game_state.player_bet(1, ante)
        game_state.player_bet(2, ante)
        player1_remaining = player1_energy - ante
        player2_remaining = player2_energy - ante

        # Play through betting rounds
        for round_num in range(4):  # Pre-flop, Flop, Turn, River
            if game_state.get_winner_by_fold() is not None:
                break

            # Reset current round bets for new round
            if round_num > 0:
                game_state.advance_round()

            # Simulate betting for this round
            # Players alternate actions until both have matched bets or someone folds
            max_actions_per_round = 10  # Prevent infinite loops
            actions_this_round = 0

            # Start with player 1
            current_player = 1

            while actions_this_round < max_actions_per_round:
                # Determine which player is acting
                if current_player == 1:
                    hand = game_state.player1_hand
                    current_bet = game_state.player1_current_bet
                    opponent_bet = game_state.player2_current_bet
                    remaining_energy = player1_remaining
                    aggression = player1_aggression
                else:
                    hand = game_state.player2_hand
                    current_bet = game_state.player2_current_bet
                    opponent_bet = game_state.player1_current_bet
                    remaining_energy = player2_remaining
                    aggression = player2_aggression

                # Decide action
                action, bet_amount = PokerEngine.decide_action(
                    hand=hand,
                    current_bet=current_bet,
                    opponent_bet=opponent_bet,
                    pot=game_state.pot,
                    player_energy=remaining_energy,
                    aggression=aggression
                )

                # Record action
                game_state.betting_history.append((current_player, action, bet_amount))

                # Process action
                if action == BettingAction.FOLD:
                    if current_player == 1:
                        game_state.player1_folded = True
                    else:
                        game_state.player2_folded = True
                    break

                elif action == BettingAction.CHECK:
                    # Check - no bet
                    pass

                elif action == BettingAction.CALL:
                    # Call - match opponent's bet
                    game_state.player_bet(current_player, bet_amount)
                    if current_player == 1:
                        player1_remaining -= bet_amount
                    else:
                        player2_remaining -= bet_amount

                elif action == BettingAction.RAISE:
                    # Raise - increase bet
                    # First call to match, then add raise amount
                    call_amount = opponent_bet - current_bet
                    total_bet = call_amount + bet_amount
                    game_state.player_bet(current_player, total_bet)
                    if current_player == 1:
                        player1_remaining -= total_bet
                    else:
                        player2_remaining -= total_bet

                actions_this_round += 1

                # Check if betting is complete for this round
                # Complete if both players have equal bets and at least one has acted
                if (game_state.player1_current_bet == game_state.player2_current_bet and
                    actions_this_round >= 2):
                    break

                # Switch to other player
                current_player = 2 if current_player == 1 else 1

        # Game is over - determine final result
        game_state.current_round = BettingRound.SHOWDOWN
        return game_state

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
