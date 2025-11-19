"""
Auto-evaluation poker game for testing fish poker skills.

This module manages automated poker games where a fish plays against
a standard poker evaluation algorithm for 100 hands or until one player
runs out of money.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.poker_interaction import (
    BettingAction,
    BettingRound,
    Card,
    Deck,
    PokerEngine,
    PokerHand,
)
from core.poker_strategy_algorithms import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class EvalPlayerState:
    """Represents the state of a player in an auto-evaluation game."""

    player_id: str
    name: str
    energy: float
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: float = 0.0
    total_bet: float = 0.0
    folded: bool = False
    # For fish player
    poker_strategy: Optional[PokerStrategyAlgorithm] = None
    # Stats tracking
    hands_won: int = 0
    hands_lost: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0


@dataclass
class AutoEvaluateStats:
    """Statistics for the auto-evaluation game."""

    hands_played: int = 0
    hands_remaining: int = 100
    fish_energy: float = 0.0
    standard_energy: float = 0.0
    fish_wins: int = 0
    standard_wins: int = 0
    fish_total_won: float = 0.0
    fish_total_lost: float = 0.0
    standard_total_won: float = 0.0
    standard_total_lost: float = 0.0
    game_over: bool = False
    winner: Optional[str] = None
    reason: str = ""


class AutoEvaluatePokerGame:
    """Manages an automated poker evaluation game between a fish and standard algorithm."""

    def __init__(
        self,
        game_id: str,
        fish_name: str,
        fish_energy: float,
        fish_poker_strategy: PokerStrategyAlgorithm,
        standard_energy: float = 500.0,
        max_hands: int = 100,
        small_blind: float = 5.0,
        big_blind: float = 10.0,
    ):
        """Initialize a new auto-evaluation poker game.

        Args:
            game_id: Unique identifier for this game
            fish_name: Name of the fish being evaluated
            fish_energy: Starting energy for fish player
            fish_poker_strategy: The fish's poker strategy algorithm
            standard_energy: Starting energy for standard algorithm player
            max_hands: Maximum number of hands to play (default 100)
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.game_id = game_id
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_hands = max_hands
        self.hands_played = 0

        # Create players
        self.fish_player = EvalPlayerState(
            player_id="fish",
            name=fish_name,
            energy=fish_energy,
            poker_strategy=fish_poker_strategy,
        )

        self.standard_player = EvalPlayerState(
            player_id="standard",
            name="Standard Algorithm",
            energy=standard_energy,
        )

        # Game state
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.button_position = 0  # 0 = fish, 1 = standard
        self.current_player = 0  # 0 = fish, 1 = standard
        self.game_over = False
        self.winner: Optional[str] = None
        self.last_hand_message = ""

    def get_players(self) -> List[EvalPlayerState]:
        """Get list of players."""
        return [self.fish_player, self.standard_player]

    def _start_hand(self):
        """Start a new hand: deal cards and post blinds."""
        # Reset deck and deal hole cards
        self.deck.reset()
        self.fish_player.hole_cards = self.deck.deal(2)
        self.standard_player.hole_cards = self.deck.deal(2)

        # Reset hand state
        for player in self.get_players():
            player.current_bet = 0.0
            player.total_bet = 0.0
            player.folded = False

        self.community_cards = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP

        # Rotate button
        self.button_position = (self.button_position + 1) % 2

        # Post blinds
        small_blind_index = (self.button_position + 1) % 2
        big_blind_index = self.button_position

        players = self.get_players()
        self._player_bet(small_blind_index, self.small_blind)
        self._player_bet(big_blind_index, self.big_blind)

        # First to act pre-flop is player after big blind (button)
        self.current_player = (self.button_position + 1) % 2

        self.hands_played += 1
        logger.info(
            f"Auto-eval {self.game_id}: Started hand {self.hands_played}. "
            f"Button at {players[self.button_position].name}"
        )

    def _player_bet(self, player_index: int, amount: float):
        """Record a player's bet."""
        players = self.get_players()
        player = players[player_index]
        # Ensure we don't bet more than available energy
        actual_amount = min(amount, player.energy)
        player.current_bet += actual_amount
        player.total_bet += actual_amount
        player.energy -= actual_amount
        self.pot += actual_amount

    def _get_call_amount(self, player_index: int) -> float:
        """Get the amount a player needs to call."""
        players = self.get_players()
        player = players[player_index]
        other_player = players[1 - player_index]
        return other_player.current_bet - player.current_bet

    def _advance_round(self):
        """Move to the next betting round and deal community cards."""
        if self.current_round == BettingRound.PRE_FLOP:
            self.deck.deal(1)  # Burn card
            self.community_cards.extend(self.deck.deal(3))
            self.current_round = BettingRound.FLOP
        elif self.current_round == BettingRound.FLOP:
            self.deck.deal(1)  # Burn card
            self.community_cards.append(self.deck.deal_one())
            self.current_round = BettingRound.TURN
        elif self.current_round == BettingRound.TURN:
            self.deck.deal(1)  # Burn card
            self.community_cards.append(self.deck.deal_one())
            self.current_round = BettingRound.RIVER
        elif self.current_round == BettingRound.RIVER:
            self.current_round = BettingRound.SHOWDOWN
            self._showdown()
            return

        # Reset current bets for new round
        for player in self.get_players():
            player.current_bet = 0.0

        # First to act post-flop is player not on button
        self.current_player = (self.button_position + 1) % 2

    def _showdown(self):
        """Determine winner at showdown."""
        players = self.get_players()

        # If one player folded, other wins
        if self.fish_player.folded:
            self._award_pot(1)  # Standard wins
            return
        if self.standard_player.folded:
            self._award_pot(0)  # Fish wins
            return

        # Evaluate hands
        fish_hand = PokerEngine.evaluate_hand(self.fish_player.hole_cards, self.community_cards)
        standard_hand = PokerEngine.evaluate_hand(
            self.standard_player.hole_cards, self.community_cards
        )

        logger.info(
            f"Auto-eval {self.game_id}: Showdown - Fish: {fish_hand}, Standard: {standard_hand}"
        )

        if fish_hand.beats(standard_hand):
            self._award_pot(0)  # Fish wins
            self.last_hand_message = f"Fish wins with {fish_hand}!"
        elif standard_hand.beats(fish_hand):
            self._award_pot(1)  # Standard wins
            self.last_hand_message = f"Standard wins with {standard_hand}!"
        else:
            # Tie - split pot
            self._split_pot()
            self.last_hand_message = "Tie! Pot split."

    def _award_pot(self, winner_index: int):
        """Award the pot to the winner."""
        players = self.get_players()
        winner = players[winner_index]
        loser = players[1 - winner_index]

        winner.energy += self.pot
        winner.hands_won += 1
        winner.total_energy_won += self.pot

        loser.hands_lost += 1
        loser.total_energy_lost += loser.total_bet

        logger.info(
            f"Auto-eval {self.game_id}: {winner.name} wins {self.pot:.1f} energy. "
            f"Fish: {self.fish_player.energy:.1f}, Standard: {self.standard_player.energy:.1f}"
        )

    def _split_pot(self):
        """Split the pot in case of a tie."""
        half_pot = self.pot / 2.0
        self.fish_player.energy += half_pot
        self.standard_player.energy += half_pot

    def _process_player_action(self, player_index: int):
        """Process a player's action."""
        players = self.get_players()
        player = players[player_index]

        if player.folded:
            return

        call_amount = self._get_call_amount(player_index)

        # Can't call - must fold
        if call_amount > player.energy:
            player.folded = True
            logger.info(f"Auto-eval {self.game_id}: {player.name} folds (insufficient energy)")
            return

        # Determine action based on player type
        if player_index == 0:  # Fish player
            # Use fish's poker strategy
            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
            hand_strength = hand.rank_value / 10.0  # Normalize to 0-1

            action, amount = player.poker_strategy.decide_action(
                hand_strength=hand_strength,
                current_bet=player.current_bet,
                opponent_bet=players[1 - player_index].current_bet,
                pot=self.pot,
                player_energy=player.energy,
                position_on_button=(player_index == self.button_position),
            )

        else:  # Standard player
            # Use PokerEngine.decide_action (standard algorithm)
            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)

            action, amount = PokerEngine.decide_action(
                hand=hand,
                current_bet=player.current_bet,
                opponent_bet=players[1 - player_index].current_bet,
                pot=self.pot,
                player_energy=player.energy,
                aggression=0.5,  # Medium aggression
                hole_cards=player.hole_cards,
                community_cards=self.community_cards if self.community_cards else None,
                position_on_button=(player_index == self.button_position),
            )

        # Execute action
        if action == BettingAction.FOLD:
            player.folded = True
            logger.info(f"Auto-eval {self.game_id}: {player.name} folds")

        elif action == BettingAction.CHECK:
            logger.info(f"Auto-eval {self.game_id}: {player.name} checks")

        elif action == BettingAction.CALL:
            if call_amount > player.energy:
                call_amount = player.energy
            self._player_bet(player_index, call_amount)
            logger.info(f"Auto-eval {self.game_id}: {player.name} calls {call_amount:.1f}")

        elif action == BettingAction.RAISE:
            total_amount = call_amount + amount
            if total_amount > player.energy:
                total_amount = player.energy
            self._player_bet(player_index, total_amount)
            logger.info(
                f"Auto-eval {self.game_id}: {player.name} raises {total_amount:.1f}"
            )

    def _play_betting_round(self):
        """Play one betting round."""
        max_actions = 20  # Prevent infinite loops
        actions_taken = 0

        while actions_taken < max_actions:
            players = self.get_players()
            current = players[self.current_player]

            # If current player folded, round is over
            if current.folded:
                break

            # Process action
            self._process_player_action(self.current_player)

            # Check if someone folded
            if self.fish_player.folded or self.standard_player.folded:
                break

            # Check if betting is complete
            if self._is_betting_complete():
                break

            # Switch to other player
            self.current_player = 1 - self.current_player
            actions_taken += 1

    def _is_betting_complete(self) -> bool:
        """Check if betting is complete for the current round."""
        # If either player folded, betting is done
        if self.fish_player.folded or self.standard_player.folded:
            return True

        # If bets match and both players have acted, betting is done
        if self.fish_player.current_bet == self.standard_player.current_bet:
            return True

        return False

    def play_hand(self):
        """Play one complete hand of poker."""
        self._start_hand()

        # Play pre-flop
        self._play_betting_round()

        # Continue through remaining rounds if no one folded
        while (
            self.current_round != BettingRound.SHOWDOWN
            and not self.fish_player.folded
            and not self.standard_player.folded
        ):
            self._advance_round()
            if self.current_round != BettingRound.SHOWDOWN:
                self._play_betting_round()

        # If we haven't had a showdown yet, trigger it
        if self.current_round != BettingRound.SHOWDOWN:
            self._showdown()

    def run_evaluation(self) -> AutoEvaluateStats:
        """Run the full evaluation (100 hands or until one player runs out of money).

        Returns:
            Final evaluation statistics
        """
        logger.info(
            f"Auto-eval {self.game_id}: Starting evaluation - "
            f"Fish: {self.fish_player.energy:.1f}, Standard: {self.standard_player.energy:.1f}"
        )

        while self.hands_played < self.max_hands:
            # Check if either player ran out of money
            if self.fish_player.energy < self.big_blind:
                self.game_over = True
                self.winner = "Standard Algorithm"
                logger.info(
                    f"Auto-eval {self.game_id}: Fish ran out of energy after {self.hands_played} hands"
                )
                break

            if self.standard_player.energy < self.big_blind:
                self.game_over = True
                self.winner = self.fish_player.name
                logger.info(
                    f"Auto-eval {self.game_id}: Standard ran out of energy after {self.hands_played} hands"
                )
                break

            # Play one hand
            self.play_hand()

        # If we completed all hands, determine winner by energy
        if not self.game_over:
            self.game_over = True
            if self.fish_player.energy > self.standard_player.energy:
                self.winner = self.fish_player.name
            elif self.standard_player.energy > self.fish_player.energy:
                self.winner = "Standard Algorithm"
            else:
                self.winner = "Tie"

        return self.get_stats()

    def get_stats(self) -> AutoEvaluateStats:
        """Get current evaluation statistics."""
        return AutoEvaluateStats(
            hands_played=self.hands_played,
            hands_remaining=max(0, self.max_hands - self.hands_played),
            fish_energy=self.fish_player.energy,
            standard_energy=self.standard_player.energy,
            fish_wins=self.fish_player.hands_won,
            standard_wins=self.standard_player.hands_won,
            fish_total_won=self.fish_player.total_energy_won,
            fish_total_lost=self.fish_player.total_energy_lost,
            standard_total_won=self.standard_player.total_energy_won,
            standard_total_lost=self.standard_player.total_energy_lost,
            game_over=self.game_over,
            winner=self.winner,
            reason=(
                f"Completed {self.hands_played} hands"
                if self.hands_played >= self.max_hands
                else f"Game ended after {self.hands_played} hands"
            ),
        )
