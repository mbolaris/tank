"""
Jellyfish-Fish poker interaction system.

This module handles poker games between fish and the static jellyfish evaluator.
The jellyfish uses a fixed conservative strategy and serves as a benchmark for
evaluating fish poker performance.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core.poker.core import PokerEngine, PokerHand

if TYPE_CHECKING:
    from core.entities import Fish, Jellyfish


@dataclass
class JellyfishPokerResult:
    """Result of a poker game between a fish and jellyfish."""

    fish_hand: PokerHand
    jellyfish_hand: PokerHand
    energy_transferred: float
    fish_won: bool
    won_by_fold: bool
    total_rounds: int
    final_pot: float
    button_position: int
    fish_folded: bool
    jellyfish_folded: bool
    reached_showdown: bool
    fish_id: int  # Track which fish played


class JellyfishPokerInteraction:
    """Handles poker encounters between fish and jellyfish."""

    # Minimum energy required to play poker
    MIN_ENERGY_TO_PLAY = 10.0

    # Default bet amount
    DEFAULT_BET_AMOUNT = 5.0

    # Cooldown between poker games (in frames)
    POKER_COOLDOWN = 60  # 2 seconds at 30fps

    def __init__(self, fish: "Fish", jellyfish: "Jellyfish"):
        """
        Initialize a poker interaction between a fish and jellyfish.

        Args:
            fish: The fish player
            jellyfish: The jellyfish player
        """
        self.fish = fish
        self.jellyfish = jellyfish
        self.fish_hand: Optional[PokerHand] = None
        self.jellyfish_hand: Optional[PokerHand] = None
        self.result: Optional[JellyfishPokerResult] = None

        # Add poker cooldown tracking to fish if not present
        if not hasattr(fish, "poker_cooldown"):
            fish.poker_cooldown = 0

        # Add button position tracking
        if not hasattr(fish, "last_button_position"):
            fish.last_button_position = 2

    def can_play_poker(self) -> bool:
        """
        Check if fish and jellyfish can play poker.

        Returns:
            True if poker game can proceed
        """
        # Both must exist
        if self.fish is None or self.jellyfish is None:
            return False

        # Jellyfish must be alive
        if self.jellyfish.is_dead():
            return False

        # Both must have minimum energy
        if self.fish.energy < self.MIN_ENERGY_TO_PLAY:
            return False
        if self.jellyfish.energy < self.MIN_ENERGY_TO_PLAY:
            return False

        # Both must be off cooldown
        if self.fish.poker_cooldown > 0:
            return False
        if self.jellyfish.poker_cooldown > 0:
            return False

        # Don't interrupt pregnant fish
        return not (hasattr(self.fish, "is_pregnant") and self.fish.is_pregnant)

    def calculate_bet_amount(self, base_bet: float = DEFAULT_BET_AMOUNT) -> float:
        """
        Calculate the bet amount based on fish and jellyfish energies.

        Args:
            base_bet: Base bet amount

        Returns:
            Actual bet amount to use
        """
        max_bet_fish = self.fish.energy * 0.2
        max_bet_jellyfish = self.jellyfish.energy * 0.2
        return min(base_bet, max_bet_fish, max_bet_jellyfish)

    def play_poker(self, bet_amount: Optional[float] = None) -> bool:
        """
        Play a multi-round poker game between fish and jellyfish.

        Args:
            bet_amount: Amount to wager (uses calculated amount if None)

        Returns:
            True if game completed successfully, False otherwise
        """
        # Check if poker can be played
        if not self.can_play_poker():
            return False

        # Calculate bet amount if not provided
        if bet_amount is None:
            bet_amount = self.calculate_bet_amount()
        else:
            bet_amount = self.calculate_bet_amount(bet_amount)

        # Fish uses genome-based aggression
        fish_aggression = PokerEngine.AGGRESSION_LOW + (
            self.fish.genome.aggression * (PokerEngine.AGGRESSION_HIGH - PokerEngine.AGGRESSION_LOW)
        )

        # Jellyfish uses fixed conservative strategy
        from core.entities import Jellyfish

        jellyfish_aggression = Jellyfish.POKER_AGGRESSION

        # Rotate button position
        button_position = 1 if self.fish.last_button_position == 2 else 2
        self.fish.last_button_position = button_position

        # Play the poker game using static method
        game_state = PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=self.fish.energy,
            player2_energy=self.jellyfish.energy,
            player1_aggression=fish_aggression,
            player2_aggression=jellyfish_aggression,
            button_position=button_position,
        )

        # Assign hands based on button position
        if button_position == 1:
            # Fish is player1
            self.fish_hand = game_state.player1_hand
            self.jellyfish_hand = game_state.player2_hand
        else:
            # Jellyfish is player1
            self.fish_hand = game_state.player2_hand
            self.jellyfish_hand = game_state.player1_hand

        # Determine winner
        if game_state.player1_folded:
            fish_won = button_position != 1  # If fish is player1 and folded, fish lost
            won_by_fold = True
        elif game_state.player2_folded:
            fish_won = button_position == 1  # If fish is player1 and opponent folded, fish won
            won_by_fold = True
        else:
            # Showdown - compare hands
            won_by_fold = False
            if button_position == 1:
                # Fish is player1
                fish_won = game_state.player1_hand.beats(game_state.player2_hand) or (
                    not game_state.player2_hand.beats(game_state.player1_hand)
                )
            else:
                # Jellyfish is player1
                fish_won = game_state.player2_hand.beats(game_state.player1_hand) or (
                    not game_state.player1_hand.beats(game_state.player2_hand)
                )

        # Calculate energy transfer properly using game state bets
        # NO house cut for fish vs jellyfish games - fish keep 100% of winnings
        total_pot = game_state.pot

        # Get each player's total bets from the game state
        if button_position == 1:
            # Fish is player1
            fish_bet = game_state.player1_total_bet
            jellyfish_bet = game_state.player2_total_bet
        else:
            # Jellyfish is player1
            fish_bet = game_state.player2_total_bet
            jellyfish_bet = game_state.player1_total_bet

        # First, deduct bets from both players
        self.fish.energy -= fish_bet
        self.jellyfish.energy -= jellyfish_bet

        # Then, award pot to winner (or split on tie)
        if won_by_fold:
            # Winner takes pot
            if fish_won:
                self.fish.energy += total_pot
                energy_transferred = total_pot - fish_bet  # Net gain for fish
            else:
                self.jellyfish.energy += total_pot
                energy_transferred = -fish_bet  # Net loss for fish
        else:
            # Showdown - check for tie
            if button_position == 1:
                p1_hand = game_state.player1_hand
                p2_hand = game_state.player2_hand
            else:
                p1_hand = game_state.player2_hand
                p2_hand = game_state.player1_hand

            fish_hand = p1_hand if button_position == 1 else p2_hand
            jelly_hand = p2_hand if button_position == 1 else p1_hand

            if fish_hand.ties(jelly_hand):
                # Tie - split pot
                self.fish.energy += total_pot / 2
                self.jellyfish.energy += total_pot / 2
                energy_transferred = (total_pot / 2) - fish_bet
                fish_won = False  # No clear winner on tie
            elif fish_won:
                self.fish.energy += total_pot
                energy_transferred = total_pot - fish_bet
            else:
                self.jellyfish.energy += total_pot
                energy_transferred = -fish_bet

        # Set poker cooldown for both
        self.fish.poker_cooldown = self.POKER_COOLDOWN
        self.jellyfish.poker_cooldown = self.POKER_COOLDOWN

        # Store result
        self.result = JellyfishPokerResult(
            fish_hand=self.fish_hand,
            jellyfish_hand=self.jellyfish_hand,
            energy_transferred=energy_transferred if fish_won else -energy_transferred,
            fish_won=fish_won,
            won_by_fold=won_by_fold,
            total_rounds=game_state.current_round.value,
            final_pot=total_pot,
            button_position=button_position,
            fish_folded=(
                game_state.player1_folded if button_position == 1 else game_state.player2_folded
            ),
            jellyfish_folded=(
                game_state.player2_folded if button_position == 1 else game_state.player1_folded
            ),
            reached_showdown=not won_by_fold,
            fish_id=self.fish.fish_id,
        )

        # Record in ecosystem if available
        if self.fish.ecosystem is not None:
            self.fish.ecosystem.record_jellyfish_poker_game(
                fish_id=self.fish.fish_id,
                fish_won=fish_won,
                energy_transferred=abs(energy_transferred),
                fish_hand_rank=self.result.fish_hand.rank_value,
                won_by_fold=won_by_fold,
            )

        return True
