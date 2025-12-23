"""
Human poker game manager for interactive poker games.

This module manages poker games between a human player and AI fish opponents.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.poker.core import (
    BettingAction,
    BettingRound,
    Card,
    Deck,
    PokerHand,
    decide_action,
    evaluate_hand,
)

logger = logging.getLogger(__name__)


@dataclass
class PlayerState:
    """Represents the state of a player in a poker game."""

    player_id: str
    name: str
    energy: float
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: float = 0.0
    total_bet: float = 0.0
    folded: bool = False
    is_human: bool = False
    # For AI players
    fish_id: Optional[int] = None
    generation: Optional[int] = None
    algorithm: Optional[str] = None
    genome_data: Optional[Dict[str, Any]] = None
    aggression: float = 0.5
    last_action: Optional[str] = None  # Track last action (fold, check, call, raise, bet)


@dataclass
class HumanPokerGameState:
    """Tracks the state of a multi-player poker game with human and AI players."""

    game_id: str
    players: List[PlayerState]
    current_round: BettingRound
    pot: float
    community_cards: List[Card]
    current_player_index: int
    button_index: int
    small_blind: float
    big_blind: float
    deck: Deck
    betting_history: List[Dict[str, Any]] = field(default_factory=list)
    winner_index: Optional[int] = None
    game_over: bool = False  # Current hand is over
    session_over: bool = False  # Entire session is over (quit or 1 player left)
    message: str = ""
    actions_this_round: int = 0  # Track actions per betting round
    hands_played: int = 0  # Track total hands played in session


class HumanPokerGame:
    """Manages a poker game between a human player and AI fish opponents."""

    STARTING_ENERGY = 100.0  # All players start with 100 energy

    def __init__(
        self,
        game_id: str,
        human_energy: float,
        ai_fish: List[Dict[str, Any]],
        small_blind: float = 5.0,
        big_blind: float = 10.0,
    ):
        """Initialize a new poker game.

        Args:
            game_id: Unique identifier for this game
            human_energy: Starting energy for human player (ignored, all start with 100)
            ai_fish: List of AI fish dictionaries with keys: fish_id, name, energy, algorithm, aggression
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.game_id = game_id
        self.small_blind = small_blind
        self.big_blind = big_blind

        # Create players list (human + 3 AI) - all start with 100 energy
        self.players: List[PlayerState] = []

        # Add human player
        self.players.append(
            PlayerState(
                player_id="human",
                name="You",
                energy=self.STARTING_ENERGY,
                is_human=True,
            )
        )

        # Add AI fish players - all start with 100 energy
        for i, fish in enumerate(ai_fish[:3]):  # Limit to 3 AI opponents
            self.players.append(
                PlayerState(
                    player_id=f"ai_{i}",
                    name=fish.get("name", f"Fish {i+1}"),
                    energy=self.STARTING_ENERGY,
                    fish_id=fish.get("fish_id"),
                    generation=fish.get("generation"),
                    algorithm=fish.get("algorithm", "Unknown"),
                    genome_data=fish.get("genome_data"),
                    aggression=fish.get("aggression", 0.5),
                    is_human=False,
                )
            )

        # Initialize game state
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.button_index = 0  # Dealer button position
        self.current_player_index = 0
        self.betting_history: List[Dict[str, Any]] = []
        self.winner_index: Optional[int] = None
        self.game_over = False
        self.session_over = False
        self.hands_played = 0
        self.message = ""
        self.actions_this_round = 0  # Track actions per betting round
        self.big_blind_index = 0  # Track big blind position for BB option
        self.big_blind_has_option = False  # BB gets option to raise if no raises pre-flop
        self.last_move: Optional[Dict[str, str]] = None  # Track the single most recent move
        
        # Decision RNG for deterministic AI decisions (unseeded for human game variation)
        self._decision_rng = random.Random()

        # Deal cards and post blinds
        self._start_hand()

    def _start_hand(self):
        """Start a new hand: deal cards and post blinds."""
        # Reset deck and deal hole cards
        self.deck.reset()
        for player in self.players:
            player.current_bet = 0.0
            player.total_bet = 0.0
            player.last_action = None  # Reset last action for new hand
            # Players with no energy are eliminated - mark them as folded
            if player.energy <= 0:
                player.hole_cards = []
                player.folded = True
            else:
                player.hole_cards = self.deck.deal(2)
                player.folded = False

        self.community_cards = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.betting_history = []
        self.winner_index = None
        self.game_over = False
        self.actions_this_round = 0
        self.hands_played += 1

        # Post blinds - skip players with no energy
        small_blind_index = self._get_next_active_player(self.button_index)
        self.big_blind_index = self._get_next_active_player(small_blind_index)
        self.big_blind_has_option = True  # BB gets option to raise if no raises pre-flop

        self._player_bet(small_blind_index, self.small_blind)
        self._player_bet(self.big_blind_index, self.big_blind)

        # First to act is player after big blind
        self.current_player_index = self._get_next_active_player(self.big_blind_index)

        self.message = f"Hand #{self.hands_played} - Blinds: {self.small_blind}/{self.big_blind}"
        logger.info(
            f"Game {self.game_id}: Started hand #{self.hands_played}. Button at index {self.button_index}, "
            f"current player: {self.current_player_index}"
        )

        # Don't process AI actions automatically - let frontend poll for each one
        # This allows the UI to show the highlight on each AI player's turn

    def _get_next_active_player(self, from_index: int) -> int:
        """Get the next player with energy > 0 after the given index."""
        next_index = (from_index + 1) % len(self.players)
        attempts = 0
        while self.players[next_index].energy <= 0 and attempts < len(self.players):
            next_index = (next_index + 1) % len(self.players)
            attempts += 1
        return next_index

    def _count_players_with_energy(self) -> int:
        """Count how many players have energy > 0."""
        return sum(1 for p in self.players if p.energy > 0)

    def _check_session_over(self):
        """Check if the session should end (only 1 player with energy)."""
        players_with_energy = self._count_players_with_energy()
        if players_with_energy <= 1:
            self.session_over = True
            # Find the winner (the one with energy)
            for i, player in enumerate(self.players):
                if player.energy > 0:
                    self.message = f"{player.name} wins the session with {player.energy:.0f} energy after {self.hands_played} hands!"
                    break
            else:
                self.message = f"Session ended after {self.hands_played} hands - all players are out!"

    def _player_bet(self, player_index: int, amount: float):
        """Record a player's bet.

        Args:
            player_index: Index of the player
            amount: Amount to bet
        """
        player = self.players[player_index]
        # Ensure we don't bet more than available energy
        actual_amount = min(amount, player.energy)
        player.current_bet += actual_amount
        player.total_bet += actual_amount
        player.energy -= actual_amount
        self.pot += actual_amount

    def _get_call_amount(self, player_index: int) -> float:
        """Get the amount a player needs to call.

        Args:
            player_index: Index of the player

        Returns:
            Amount needed to call
        """
        player = self.players[player_index]
        active_bets = [p.current_bet for p in self.players if not p.folded]
        if not active_bets:
            return 0.0
        max_bet = max(active_bets)
        return max_bet - player.current_bet

    def _advance_round(self):
        """Move to the next betting round and deal community cards."""
        # Check if only one player remains - if so, end immediately without dealing cards
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) <= 1:
            self.current_round = BettingRound.SHOWDOWN
            self._showdown()
            return

        if self.current_round == BettingRound.PRE_FLOP:
            # Deal flop
            self.deck.deal(1)  # Burn card
            self.community_cards.extend(self.deck.deal(3))
            self.current_round = BettingRound.FLOP
            self.message = "Flop dealt!"
        elif self.current_round == BettingRound.FLOP:
            # Deal turn
            self.deck.deal(1)  # Burn card
            self.community_cards.append(self.deck.deal_one())
            self.current_round = BettingRound.TURN
            self.message = "Turn dealt!"
        elif self.current_round == BettingRound.TURN:
            # Deal river
            self.deck.deal(1)  # Burn card
            self.community_cards.append(self.deck.deal_one())
            self.current_round = BettingRound.RIVER
            self.message = "River dealt!"
        elif self.current_round == BettingRound.RIVER:
            # Go to showdown
            self.current_round = BettingRound.SHOWDOWN
            self._showdown()
            return

        # Reset current bets and action counter for new round
        for player in self.players:
            player.current_bet = 0.0
        self.actions_this_round = 0

        # First to act post-flop is player after button
        self.current_player_index = (self.button_index + 1) % len(self.players)
        # Skip folded players and all-in players (with loop guard to prevent infinite loop)
        attempts = 0
        while attempts < len(self.players):
            player = self.players[self.current_player_index]
            # Player can act if not folded and has energy
            if not player.folded and player.energy > 0:
                break
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            attempts += 1

        # Safety check: if no players can act, end the hand (all folded or all-in)
        if attempts >= len(self.players):
            logger.warning("No players can act - going to showdown")
            self.current_round = BettingRound.SHOWDOWN
            self._showdown()
            return

    def _showdown(self):
        """Determine winner at showdown."""
        active_players = [p for p in self.players if not p.folded]

        if len(active_players) == 1:
            # Only one player left - they win
            self.winner_index = self.players.index(active_players[0])
            winner = self.players[self.winner_index]
            winner.energy += self.pot
            self.message = f"{winner.name} wins {self.pot:.0f} energy!"
            self.game_over = True
            self._check_session_over()
            return

        # Evaluate hands
        best_hand: Optional[PokerHand] = None
        winning_player_indices: List[int] = []

        for i, player in enumerate(self.players):
            if player.folded:
                continue

            hand = evaluate_hand(player.hole_cards, self.community_cards)
            logger.debug(f"Player {player.name}: {hand}")

            if best_hand is None or hand.beats(best_hand):
                best_hand = hand
                winning_player_indices = [i]
            elif hand.ties(best_hand):
                winning_player_indices.append(i)

        if winning_player_indices:
            split_amount = self.pot / len(winning_player_indices)
            for idx in winning_player_indices:
                self.players[idx].energy += split_amount

            # Preserve legacy single-winner field for UI by picking the first winner
            self.winner_index = winning_player_indices[0]

            if len(winning_player_indices) == 1:
                winner = self.players[self.winner_index]
                self.message = f"{winner.name} wins {self.pot:.0f} energy with {best_hand}!"
            else:
                winners = ", ".join(self.players[idx].name for idx in winning_player_indices)
                self.message = (
                    f"Hand ends in a tie - {winners} split {self.pot:.0f} energy with {best_hand}!"
                )

            self.game_over = True
            self._check_session_over()

    def start_new_hand(self) -> Dict[str, Any]:
        """Start a new hand after the previous one ends.

        Returns:
            Dictionary with success status and game state
        """
        if self.session_over:
            return {
                "success": False,
                "error": "Session is over - only 1 player has energy remaining",
                "state": self.get_state(),
            }

        if not self.game_over:
            return {
                "success": False,
                "error": "Current hand is not over yet",
                "state": self.get_state(),
            }

        # Move button to next player with energy
        self.button_index = self._get_next_active_player(self.button_index)

        # Start new hand
        self._start_hand()

        return {
            "success": True,
            "state": self.get_state(),
        }

    def _is_betting_complete(self) -> bool:
        """Check if betting is complete for the current round.

        Returns:
            True if all active players have matched the current bet
        """
        players_in_hand = [p for p in self.players if not p.folded]

        # If no players remain (shouldn't happen) or only one, betting is complete
        if len(players_in_hand) <= 1:
            return True

        # All non-folded bets contribute to the pot and call requirements
        max_bet = max(p.current_bet for p in players_in_hand)

        # Players who can still act (have energy) must match the highest bet
        active_players = [p for p in players_in_hand if p.energy > 0]
        for player in active_players:
            if player.current_bet + 1e-6 < max_bet:  # small epsilon for float safety
                return False

        # Pre-flop special case: big blind gets option to raise even if all call
        if self.current_round == BettingRound.PRE_FLOP and self.big_blind_has_option:
            bb_player = self.players[self.big_blind_index]
            # BB still has option if they haven't acted yet (only posted blind)
            # and no one has raised above the big blind
            if not bb_player.folded and bb_player.energy > 0:
                # Check if max bet is still just the big blind (no raises)
                if max_bet <= self.big_blind + 0.01:  # epsilon for float comparison
                    return False

        # Ensure all players have had a chance to act this round
        return self.actions_this_round >= len(active_players)

    def _next_player(self):
        """Move to the next active player."""
        original_index = self.current_player_index

        # Guard against infinite loops - max iterations is number of players * 2
        max_iterations = len(self.players) * 2
        iterations = 0

        while True:
            iterations += 1
            if iterations > max_iterations:
                logger.error(
                    f"_next_player exceeded {max_iterations} iterations - forcing round advance. "
                    f"Game state: round={self.current_round}, player_idx={self.current_player_index}"
                )
                self._advance_round()
                return

            self.current_player_index = (self.current_player_index + 1) % len(self.players)

            # If betting is complete, advance round
            if self._is_betting_complete():
                self._advance_round()
                return

            # If we've looped back to start without finding someone to act, advance round
            if self.current_player_index == original_index:
                self._advance_round()
                return

            # Skip folded players and all-in players (energy = 0)
            player = self.players[self.current_player_index]
            if not player.folded and player.energy > 0:
                # This player can act - they need to if there's a bet to call
                # or if not everyone has acted yet this round
                return

    def handle_action(self, player_id: str, action: str, amount: float = 0.0) -> Dict[str, Any]:
        """Handle a player action.

        Args:
            player_id: ID of the player making the action
            action: Action type (fold, check, call, raise, bet)
            amount: Amount for raise/bet actions

        Returns:
            Dictionary with action result and updated game state
        """
        if self.game_over:
            return {
                "success": False,
                "error": "Game is over",
                "state": self.get_state(),
            }

        current_player = self.players[self.current_player_index]

        # Verify it's the correct player's turn
        if current_player.player_id != player_id:
            return {
                "success": False,
                "error": f"Not your turn! Waiting for {current_player.name}",
                "state": self.get_state(),
            }

        call_amount = self._get_call_amount(self.current_player_index)

        # Clear big blind option if BB is acting
        if self.current_player_index == self.big_blind_index:
            self.big_blind_has_option = False

        # Process action
        if action == "fold":
            current_player.folded = True
            current_player.last_action = "fold"
            self.last_move = {"player": current_player.name, "action": "fold"}
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "fold",
                    "amount": 0.0,
                }
            )
            self.actions_this_round += 1
            self.message = f"{current_player.name} folds"

            # Check if only one player left
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                self._showdown()

        elif action == "check":
            # Use small epsilon for floating point comparison
            if call_amount > 0.01:
                return {
                    "success": False,
                    "error": f"Cannot check - must call {call_amount:.0f} or fold",
                    "state": self.get_state(),
                }
            current_player.last_action = "check"
            self.last_move = {"player": current_player.name, "action": "check"}
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "check",
                    "amount": 0.0,
                }
            )
            self.actions_this_round += 1
            self.message = f"{current_player.name} checks"

        elif action == "call":
            if call_amount == 0:
                return {
                    "success": False,
                    "error": "Nothing to call - use check instead",
                    "state": self.get_state(),
                }
            if call_amount > current_player.energy:
                # All-in call
                call_amount = current_player.energy
            self._player_bet(self.current_player_index, call_amount)
            current_player.last_action = f"call {call_amount:.0f}"
            self.last_move = {"player": current_player.name, "action": f"call {call_amount:.0f}"}
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "call",
                    "amount": call_amount,
                }
            )
            self.actions_this_round += 1
            self.message = f"{current_player.name} calls {call_amount:.0f}"

        elif action in ["raise", "bet"]:
            if amount <= 0:
                return {
                    "success": False,
                    "error": "Raise/bet amount must be positive",
                    "state": self.get_state(),
                }

            # Total amount is call + raise
            total_amount = call_amount + amount
            if total_amount > current_player.energy:
                total_amount = current_player.energy

            self._player_bet(self.current_player_index, total_amount)
            action_name = "raise" if call_amount > 0 else "bet"
            current_player.last_action = f"{action_name} {total_amount:.0f}"
            self.last_move = {"player": current_player.name, "action": f"{action_name} {total_amount:.0f}"}
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": action_name,
                    "amount": total_amount,
                }
            )
            # Reset action counter on raise - others need to respond
            self.actions_this_round = 1
            # Clear big blind option since there was a raise
            self.big_blind_has_option = False
            self.message = f"{current_player.name} {action_name}s {total_amount:.0f}"

        else:
            return {
                "success": False,
                "error": f"Invalid action: {action}",
                "state": self.get_state(),
            }

        # Move to next player
        if not self.game_over:
            self._next_player()

            # Don't process AI turns automatically - let frontend poll for each one
            # This allows the UI to show the highlight on each AI player's turn

        return {
            "success": True,
            "state": self.get_state(),
        }

    def process_single_ai_turn(self) -> dict:
        """Process a single AI player's turn if it's their turn.

        Returns:
            Dictionary with success status, whether an action was taken, and game state
        """
        # If game is over, nothing to do
        if self.game_over:
            return {
                "success": True,
                "action_taken": False,
                "reason": "game_over",
                "state": self.get_state(),
            }

        current_player = self.players[self.current_player_index]

        # If it's the human's turn, don't process
        if current_player.is_human:
            return {
                "success": True,
                "action_taken": False,
                "reason": "human_turn",
                "state": self.get_state(),
            }

        # Process the AI action
        self._process_ai_action_internal()

        return {
            "success": True,
            "action_taken": True,
            "state": self.get_state(),
        }

    def _process_ai_turns(self):
        """Process AI player actions until it's the human's turn or game is over."""
        # Guard against infinite loops - max iterations based on reasonable game actions
        # In worst case: 4 players * 4 rounds * 10 actions per round = 160 actions
        max_iterations = 200
        iterations = 0

        while not self.game_over and not self.players[self.current_player_index].is_human:
            iterations += 1
            if iterations > max_iterations:
                logger.error(
                    f"_process_ai_turns exceeded {max_iterations} iterations - breaking to prevent hang. "
                    f"Game state: round={self.current_round}, player_idx={self.current_player_index}"
                )
                # Force game over to prevent hang
                self.game_over = True
                self.message = "Game ended due to error - please start a new hand"
                break
            self._process_ai_action_internal()

    def _process_ai_action_internal(self):
        """Process an AI player's action internally without recursion."""
        player = self.players[self.current_player_index]

        if player.folded or self.game_over:
            self._next_player()
            return

        # Clear big blind option if BB is acting
        if self.current_player_index == self.big_blind_index:
            self.big_blind_has_option = False

        # Evaluate hand
        hand = evaluate_hand(player.hole_cards, self.community_cards)
        call_amount = self._get_call_amount(self.current_player_index)

        # Use decide_action to decide action
        active_bets = [p.current_bet for p in self.players if not p.folded]
        opponent_bet = max(active_bets) if active_bets else 0.0

        action, bet_amount = decide_action(
            hand=hand,
            current_bet=player.current_bet,
            opponent_bet=opponent_bet,
            pot=self.pot,
            player_energy=player.energy,
            aggression=player.aggression,
            hole_cards=player.hole_cards,
            community_cards=self.community_cards,
            position_on_button=(self.current_player_index == self.button_index),
            rng=self._decision_rng,
        )

        # Process action directly without calling handle_action to avoid recursion
        if action == BettingAction.FOLD:
            player.folded = True
            player.last_action = "fold"
            self.last_move = {"player": player.name, "action": "fold"}
            self.betting_history.append({"player": player.name, "action": "fold", "amount": 0.0})
            self.actions_this_round += 1
            self.message = f"{player.name} folds"
            # Check if only one player left
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                self._showdown()
                return

        elif action == BettingAction.CHECK:
            player.last_action = "check"
            self.last_move = {"player": player.name, "action": "check"}
            self.betting_history.append({"player": player.name, "action": "check", "amount": 0.0})
            self.actions_this_round += 1
            self.message = f"{player.name} checks"

        elif action == BettingAction.CALL:
            if call_amount > player.energy:
                call_amount = player.energy
            self._player_bet(self.current_player_index, call_amount)
            player.last_action = f"call {call_amount:.0f}"
            self.last_move = {"player": player.name, "action": f"call {call_amount:.0f}"}
            self.betting_history.append(
                {"player": player.name, "action": "call", "amount": call_amount}
            )
            self.actions_this_round += 1
            self.message = f"{player.name} calls {call_amount:.0f}"

        elif action == BettingAction.RAISE:
            total_amount = call_amount + bet_amount
            if total_amount > player.energy:
                total_amount = player.energy
            self._player_bet(self.current_player_index, total_amount)
            action_name = "raise" if call_amount > 0 else "bet"
            player.last_action = f"{action_name} {total_amount:.0f}"
            self.last_move = {"player": player.name, "action": f"{action_name} {total_amount:.0f}"}
            self.betting_history.append(
                {
                    "player": player.name,
                    "action": action_name,
                    "amount": total_amount,
                }
            )
            # Reset action counter on raise - others need to respond
            self.actions_this_round = 1
            # Clear big blind option since there was a raise
            self.big_blind_has_option = False
            self.message = (
                f"{player.name} {action_name}s {total_amount:.0f}"
            )

        # Move to next player
        if not self.game_over:
            self._next_player()

    def get_state(self) -> Dict[str, Any]:
        """Get current game state for frontend.

        Returns:
            Dictionary with complete game state
        """
        current_player = self.players[self.current_player_index]

        # Get human player (always index 0)
        human_player = self.players[0]

        return {
            "game_id": self.game_id,
            "pot": int(self.pot),
            "current_round": self.current_round.name,
            "community_cards": [str(card) for card in self.community_cards],
            "current_player": current_player.name,
            "is_your_turn": current_player.is_human,
            "game_over": self.game_over,
            "session_over": self.session_over,
            "hands_played": self.hands_played,
            "message": self.message,
            "winner": (
                self.players[self.winner_index].name if self.winner_index is not None else None
            ),
            "players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "energy": int(p.energy),
                    "current_bet": int(p.current_bet),
                    "total_bet": int(p.total_bet),
                    "folded": p.folded,
                    "is_human": p.is_human,
                    "fish_id": p.fish_id,
                    "generation": p.generation,
                    "algorithm": p.algorithm,
                    "genome_data": p.genome_data,
                    "last_action": p.last_action,
                    # Show hole cards for human player or during showdown
                    "hole_cards": (
                        [str(card) for card in p.hole_cards]
                        if (p.is_human or self.current_round == BettingRound.SHOWDOWN)
                        else ["??", "??"]
                    ),
                }
                for p in self.players
            ],
            "your_cards": [str(card) for card in human_player.hole_cards],
            "call_amount": int(self._get_call_amount(0)) if not human_player.folded else 0,
            "min_raise": int(self.big_blind),
            "last_move": self.last_move,
        }
