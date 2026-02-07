"""
Human poker game manager for interactive poker games.

This module manages poker games between a human player and AI fish opponents.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.energy.energy_utils import apply_energy_delta
from core.poker.core import BettingAction, BettingRound, Card, Deck
from core.poker.simulation.hand_engine import (MultiplayerGameState,
                                               MultiplayerPlayerContext,
                                               apply_action,
                                               decide_action_for_player,
                                               determine_payouts,
                                               start_hand_from_players)

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
        self._hand_state: Optional[MultiplayerGameState] = None
        self._hand_cache: Dict[int, Any] = {}
        self._players_acted_since_raise: set[int] = set()
        self._last_raiser: Optional[int] = None

        # Deal cards and post blinds
        self._start_hand()

    def _start_hand(self):
        """Start a new hand: deal cards and post blinds."""
        len(self.players)

        self.deck.reset()
        contexts: Dict[int, MultiplayerPlayerContext] = {}
        for i, player in enumerate(self.players):
            player.current_bet = 0.0
            player.total_bet = 0.0
            player.last_action = None
            context = MultiplayerPlayerContext(
                player_id=i,
                remaining_energy=player.energy,
                aggression=player.aggression if not player.is_human else 0.5,
            )
            if player.energy <= 0:
                context.folded = True
                context.all_in = True
            contexts[i] = context

        self._hand_state = start_hand_from_players(
            players=contexts,
            button_position=self.button_index,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            deck=self.deck,
        )

        for i, player in enumerate(self.players):
            if contexts[i].folded:
                contexts[i].hole_cards = []
                player.hole_cards = []

        self.community_cards = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.betting_history = []
        self.winner_index = None
        self.game_over = False
        self.actions_this_round = 0
        self.hands_played += 1
        self._hand_cache = {}
        self._players_acted_since_raise = set()
        self._last_raiser = None

        # Track blind positions for game flow (BB option, first-to-act)
        small_blind_index = self._get_next_active_player(self.button_index)
        self.big_blind_index = self._get_next_active_player(small_blind_index)
        self.big_blind_has_option = True
        self._last_raiser = self.big_blind_index

        # First to act is player after big blind
        self.current_player_index = self._get_next_active_player(self.big_blind_index)

        self._sync_from_hand_state()

        self.message = f"Hand #{self.hands_played} - Blinds: {self.small_blind}/{self.big_blind}"
        logger.info(
            f"Game {self.game_id}: Started hand #{self.hands_played}. Button at index {self.button_index}, "
            f"current player: {self.current_player_index}"
        )

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
                self.message = (
                    f"Session ended after {self.hands_played} hands - all players are out!"
                )

    def _sync_from_hand_state(self) -> None:
        """Sync public-facing player state from the hand engine."""
        if self._hand_state is None:
            return

        self.pot = self._hand_state.pot
        self.community_cards = list(self._hand_state.community_cards)
        # Clamp round to valid range (0-4) to prevent "5 is not a valid BettingRound" error
        round_value = min(self._hand_state.current_round, BettingRound.SHOWDOWN)
        self.current_round = BettingRound(round_value)

        for i, player in enumerate(self.players):
            state_player = self._hand_state.players[i]
            player.current_bet = state_player.current_bet
            player.total_bet = state_player.total_bet
            target_energy = state_player.remaining_energy
            delta = target_energy - player.energy
            apply_energy_delta(
                player,
                delta,
                source="human_poker_sync",
                allow_direct_assignment=True,
            )
            player.folded = state_player.folded
            player.hole_cards = list(state_player.hole_cards)

    def _sync_hand_state_from_players(self) -> None:
        """Sync hand engine state from public-facing player data."""
        if self._hand_state is None:
            return

        for i, player in enumerate(self.players):
            state_player = self._hand_state.players[i]
            state_player.remaining_energy = player.energy
            state_player.current_bet = player.current_bet
            state_player.total_bet = player.total_bet
            state_player.folded = player.folded
            state_player.hole_cards = list(player.hole_cards)
            state_player.all_in = state_player.remaining_energy <= 0 and not state_player.folded

        self._hand_state.community_cards = list(self.community_cards)
        self._hand_state.pot = self.pot
        self._hand_state.current_round = self.current_round

    def _player_bet(self, player_index: int, amount: float):
        """Record a player's bet.

        Args:
            player_index: Index of the player
            amount: Amount to bet
        """
        if self._hand_state is None:
            return
        self._hand_state.player_bet(player_index, amount)
        self._sync_from_hand_state()

    def _get_call_amount(self, player_index: int) -> float:
        """Get the amount a player needs to call.

        Args:
            player_index: Index of the player

        Returns:
            Amount needed to call
        """
        if self._hand_state is None:
            return 0.0
        player = self._hand_state.players[player_index]
        active_bets = [p.current_bet for p in self._hand_state.players.values() if not p.folded]
        if not active_bets:
            return 0.0
        max_bet = max(active_bets)
        return max_bet - player.current_bet

    def _advance_round(self):
        """Move to the next betting round and deal community cards."""
        if self._hand_state is None:
            return

        active_players = [p for p in self._hand_state.players.values() if not p.folded]
        if len(active_players) <= 1:
            self._showdown()
            return

        self._hand_state.advance_round()
        self._hand_cache = {}
        self._players_acted_since_raise = set()
        self._last_raiser = None
        self.actions_this_round = 0
        self._sync_from_hand_state()

        if self.current_round == BettingRound.FLOP:
            self.message = "Flop dealt!"
        elif self.current_round == BettingRound.TURN:
            self.message = "Turn dealt!"
        elif self.current_round == BettingRound.RIVER:
            self.message = "River dealt!"
        elif self.current_round == BettingRound.SHOWDOWN:
            self._showdown()
            return

        self.current_player_index = (self.button_index + 1) % len(self.players)
        attempts = 0
        while attempts < len(self.players):
            player = self.players[self.current_player_index]
            if not player.folded and player.energy > 0:
                break
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            attempts += 1

        if attempts >= len(self.players):
            logger.warning("No players can act - going to showdown")
            self._showdown()
            return

    def _showdown(self):
        """Determine winner at showdown."""
        if self._hand_state is None:
            return

        self._sync_hand_state_from_players()
        self._hand_state.current_round = BettingRound.SHOWDOWN

        payouts = determine_payouts(self._hand_state)
        winner_by_fold = self._hand_state.get_winner_by_fold()
        winners = [player_id for player_id, payout in payouts.items() if payout > 0]

        for player_id, payout in payouts.items():
            state_player = self._hand_state.players[player_id]
            state_player.remaining_energy += payout

        self._sync_from_hand_state()

        if winner_by_fold is not None:
            winner = self.players[winner_by_fold]
            self.winner_index = winner_by_fold
            self.message = f"{winner.name} wins {self.pot:.0f} energy!"
            self.game_over = True
            self._check_session_over()
            return

        if winners:
            self.winner_index = winners[0]
            if len(winners) == 1:
                winner = self.players[self.winner_index]
                winning_hand = self._hand_state.player_hands.get(self.winner_index)
                if winning_hand is not None:
                    self.message = f"{winner.name} wins {self.pot:.0f} energy with {winning_hand}!"
                else:
                    self.message = f"{winner.name} wins {self.pot:.0f} energy!"
            else:
                winners_str = ", ".join(self.players[idx].name for idx in winners)
                self.message = f"Hand ends in a tie - {winners_str} split {self.pot:.0f} energy!"

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
        if self._hand_state is None:
            return True

        self._sync_hand_state_from_players()
        active_players = [
            pid
            for pid, player in self._hand_state.players.items()
            if not player.folded and player.remaining_energy > 0
        ]
        if not active_players:
            return True

        max_bet = max(
            player.current_bet for player in self._hand_state.players.values() if not player.folded
        )

        for pid in active_players:
            player = self._hand_state.players[pid]
            if player.current_bet + 1e-6 < max_bet:
                return False
            if pid not in self._players_acted_since_raise:
                return False

        return True

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

        if self._hand_state is not None:
            self._sync_hand_state_from_players()

        call_amount = self._get_call_amount(self.current_player_index)

        # Clear big blind option if BB is acting
        if self.current_player_index == self.big_blind_index:
            self.big_blind_has_option = False

        if self._hand_state is None:
            return {
                "success": False,
                "error": "Game state not initialized",
                "state": self.get_state(),
            }

        state_player = self._hand_state.players[self.current_player_index]
        before_bet = state_player.current_bet

        if action == "fold":
            action_enum = BettingAction.FOLD
            bet_amount = 0.0
        elif action == "check":
            if call_amount > 0.01:
                return {
                    "success": False,
                    "error": f"Cannot check - must call {call_amount:.0f} or fold",
                    "state": self.get_state(),
                }
            action_enum = BettingAction.CHECK
            bet_amount = 0.0
        elif action == "call":
            if call_amount == 0:
                return {
                    "success": False,
                    "error": "Nothing to call - use check instead",
                    "state": self.get_state(),
                }
            action_enum = BettingAction.CALL
            bet_amount = 0.0
        elif action in ["raise", "bet"]:
            if amount <= 0:
                return {
                    "success": False,
                    "error": "Raise/bet amount must be positive",
                    "state": self.get_state(),
                }
            action_enum = BettingAction.RAISE
            bet_amount = amount
        else:
            return {
                "success": False,
                "error": f"Invalid action: {action}",
                "state": self.get_state(),
            }

        was_raise = apply_action(
            game_state=self._hand_state,
            player_id=self.current_player_index,
            action=action_enum,
            bet_amount=bet_amount,
        )
        actual_amount = max(0.0, state_player.current_bet - before_bet)

        if was_raise:
            self._last_raiser = self.current_player_index
            self._players_acted_since_raise = {self.current_player_index}
            self.actions_this_round = 1
            self.big_blind_has_option = False
        else:
            self._players_acted_since_raise.add(self.current_player_index)
            self.actions_this_round = len(self._players_acted_since_raise)

        if action_enum == BettingAction.FOLD:
            current_player.last_action = "fold"
            self.last_move = {"player": current_player.name, "action": "fold"}
            self.betting_history.append(
                {"player": current_player.name, "action": "fold", "amount": 0.0}
            )
            self.message = f"{current_player.name} folds"
        elif action_enum == BettingAction.CHECK:
            current_player.last_action = "check"
            self.last_move = {"player": current_player.name, "action": "check"}
            self.betting_history.append(
                {"player": current_player.name, "action": "check", "amount": 0.0}
            )
            self.message = f"{current_player.name} checks"
        elif action_enum == BettingAction.CALL:
            current_player.last_action = f"call {actual_amount:.0f}"
            self.last_move = {
                "player": current_player.name,
                "action": f"call {actual_amount:.0f}",
            }
            self.betting_history.append(
                {"player": current_player.name, "action": "call", "amount": actual_amount}
            )
            self.message = f"{current_player.name} calls {actual_amount:.0f}"
        elif action_enum == BettingAction.RAISE:
            action_name = "raise" if call_amount > 0 else "bet"
            current_player.last_action = f"{action_name} {actual_amount:.0f}"
            self.last_move = {
                "player": current_player.name,
                "action": f"{action_name} {actual_amount:.0f}",
            }
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": action_name,
                    "amount": actual_amount,
                }
            )
            self.message = f"{current_player.name} {action_name}s {actual_amount:.0f}"

        self._sync_from_hand_state()

        active_players = [p for p in self._hand_state.players.values() if not p.folded]
        if len(active_players) <= 1:
            self._showdown()

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

        if self._hand_state is None:
            return

        if self.current_player_index == self.big_blind_index:
            self.big_blind_has_option = False

        call_amount = self._get_call_amount(self.current_player_index)
        state_player = self._hand_state.players[self.current_player_index]
        before_bet = state_player.current_bet

        action, bet_amount = decide_action_for_player(
            game_state=self._hand_state,
            player_id=self.current_player_index,
            hand_cache=self._hand_cache,
            rng=self._decision_rng,
        )

        was_raise = apply_action(
            game_state=self._hand_state,
            player_id=self.current_player_index,
            action=action,
            bet_amount=bet_amount,
        )
        actual_amount = max(0.0, state_player.current_bet - before_bet)

        if was_raise:
            self._last_raiser = self.current_player_index
            self._players_acted_since_raise = {self.current_player_index}
            self.actions_this_round = 1
            self.big_blind_has_option = False
        else:
            self._players_acted_since_raise.add(self.current_player_index)
            self.actions_this_round = len(self._players_acted_since_raise)

        if action == BettingAction.FOLD:
            player.last_action = "fold"
            self.last_move = {"player": player.name, "action": "fold"}
            self.betting_history.append({"player": player.name, "action": "fold", "amount": 0.0})
            self.message = f"{player.name} folds"
        elif action == BettingAction.CHECK:
            player.last_action = "check"
            self.last_move = {"player": player.name, "action": "check"}
            self.betting_history.append({"player": player.name, "action": "check", "amount": 0.0})
            self.message = f"{player.name} checks"
        elif action == BettingAction.CALL:
            player.last_action = f"call {actual_amount:.0f}"
            self.last_move = {"player": player.name, "action": f"call {actual_amount:.0f}"}
            self.betting_history.append(
                {"player": player.name, "action": "call", "amount": actual_amount}
            )
            self.message = f"{player.name} calls {actual_amount:.0f}"
        elif action == BettingAction.RAISE:
            action_name = "raise" if call_amount > 0 else "bet"
            player.last_action = f"{action_name} {actual_amount:.0f}"
            self.last_move = {"player": player.name, "action": f"{action_name} {actual_amount:.0f}"}
            self.betting_history.append(
                {"player": player.name, "action": action_name, "amount": actual_amount}
            )
            self.message = f"{player.name} {action_name}s {actual_amount:.0f}"

        self._sync_from_hand_state()

        active_players = [p for p in self._hand_state.players.values() if not p.folded]
        if len(active_players) <= 1:
            self._showdown()
            return

        if not self.game_over:
            self._next_player()

    def get_last_hand_result(self) -> Optional[Dict[str, Any]]:
        """
        Returns a summary of the last hand result for reward processing.
        Should be called immediately after a hand concludes (game_over=True)
        but before a new round starts.
        """
        if not self.game_over or self.winner_index is None:
            return None

        winner = self.players[self.winner_index]
        return {
            "winner_index": self.winner_index,
            "is_human": winner.is_human,
            "fish_id": winner.fish_id,
            "pot": self.pot,
            "message": self.message,
            "winning_hand_description": self.message,
        }

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
