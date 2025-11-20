"""
Human poker game manager for interactive poker games.

This module manages poker games between a human player and AI fish opponents.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.poker.core import (
    BettingAction,
    BettingRound,
    Card,
    Deck,
    PokerEngine,
    PokerHand,
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
    algorithm: Optional[str] = None
    aggression: float = 0.5


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
    game_over: bool = False
    message: str = ""


class HumanPokerGame:
    """Manages a poker game between a human player and AI fish opponents."""

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
            human_energy: Starting energy for human player
            ai_fish: List of AI fish dictionaries with keys: fish_id, name, energy, algorithm, aggression
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.game_id = game_id
        self.small_blind = small_blind
        self.big_blind = big_blind

        # Create players list (human + 3 AI)
        self.players: List[PlayerState] = []

        # Add human player
        self.players.append(
            PlayerState(
                player_id="human",
                name="You",
                energy=human_energy,
                is_human=True,
            )
        )

        # Add AI fish players
        for i, fish in enumerate(ai_fish[:3]):  # Limit to 3 AI opponents
            self.players.append(
                PlayerState(
                    player_id=f"ai_{i}",
                    name=fish.get("name", f"Fish {i+1}"),
                    energy=fish.get("energy", 100.0),
                    fish_id=fish.get("fish_id"),
                    algorithm=fish.get("algorithm", "Unknown"),
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
        self.message = ""

        # Deal cards and post blinds
        self._start_hand()

    def _start_hand(self):
        """Start a new hand: deal cards and post blinds."""
        # Reset deck and deal hole cards
        self.deck.reset()
        for player in self.players:
            player.hole_cards = self.deck.deal(2)
            player.current_bet = 0.0
            player.total_bet = 0.0
            player.folded = False

        self.community_cards = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.betting_history = []
        self.winner_index = None
        self.game_over = False

        # Post blinds
        # In multi-player: player after button posts small blind, next player posts big blind
        small_blind_index = (self.button_index + 1) % len(self.players)
        big_blind_index = (self.button_index + 2) % len(self.players)

        self._player_bet(small_blind_index, self.small_blind)
        self._player_bet(big_blind_index, self.big_blind)

        # First to act is player after big blind
        self.current_player_index = (self.button_index + 3) % len(self.players)

        self.message = f"New hand started! Blinds: {self.small_blind}/{self.big_blind}"
        logger.info(
            f"Game {self.game_id}: Started new hand. Button at index {self.button_index}, "
            f"current player: {self.current_player_index}"
        )

        # Process AI actions if first player to act is AI
        self._process_ai_turns()

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
        max_bet = max(p.current_bet for p in self.players if not p.folded)
        return max_bet - player.current_bet

    def _advance_round(self):
        """Move to the next betting round and deal community cards."""
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

        # Reset current bets for new round
        for player in self.players:
            player.current_bet = 0.0

        # First to act post-flop is player after button
        self.current_player_index = (self.button_index + 1) % len(self.players)
        # Skip folded players
        while self.players[self.current_player_index].folded:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def _showdown(self):
        """Determine winner at showdown."""
        active_players = [p for p in self.players if not p.folded]

        if len(active_players) == 1:
            # Only one player left - they win
            self.winner_index = self.players.index(active_players[0])
            winner = self.players[self.winner_index]
            winner.energy += self.pot
            self.message = f"{winner.name} wins {self.pot:.1f} energy!"
            self.game_over = True
            return

        # Evaluate hands
        best_hand: Optional[PokerHand] = None
        best_player_index: Optional[int] = None

        for i, player in enumerate(self.players):
            if player.folded:
                continue

            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
            logger.info(f"Player {player.name}: {hand}")

            if best_hand is None or hand.beats(best_hand):
                best_hand = hand
                best_player_index = i
            elif hand.ties(best_hand):
                # Handle ties - split pot (simplified: first player wins for now)
                pass

        if best_player_index is not None:
            self.winner_index = best_player_index
            winner = self.players[best_player_index]
            winner.energy += self.pot
            self.message = f"{winner.name} wins {self.pot:.1f} energy with {best_hand}!"
            self.game_over = True

    def _is_betting_complete(self) -> bool:
        """Check if betting is complete for the current round.

        Returns:
            True if all active players have matched the current bet
        """
        active_players = [p for p in self.players if not p.folded]

        if len(active_players) == 1:
            return True

        # Get max bet
        max_bet = max(p.current_bet for p in active_players)

        # Check if all active players have matched max bet
        for player in active_players:
            if player.current_bet < max_bet:
                return False

        # Also ensure all players have had a chance to act
        return len(self.betting_history) >= len(active_players)

    def _next_player(self):
        """Move to the next active player."""
        original_index = self.current_player_index

        while True:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

            # If we've looped back to start and betting is complete, advance round
            if self.current_player_index == original_index or self._is_betting_complete():
                if self._is_betting_complete():
                    self._advance_round()
                return

            # Skip folded players and all-in players
            player = self.players[self.current_player_index]
            if not player.folded and player.energy > 0:
                # Check if this player needs to act
                call_amount = self._get_call_amount(self.current_player_index)
                if call_amount > 0 or len(self.betting_history) < len(self.players):
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

        # Process action
        if action == "fold":
            current_player.folded = True
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "fold",
                    "amount": 0.0,
                }
            )
            self.message = f"{current_player.name} folds"

            # Check if only one player left
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                self._showdown()

        elif action == "check":
            if call_amount > 0:
                return {
                    "success": False,
                    "error": f"Cannot check - must call {call_amount:.1f} or fold",
                    "state": self.get_state(),
                }
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "check",
                    "amount": 0.0,
                }
            )
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
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "call",
                    "amount": call_amount,
                }
            )
            self.message = f"{current_player.name} calls {call_amount:.1f}"

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
            self.betting_history.append(
                {
                    "player": current_player.name,
                    "action": "raise" if call_amount > 0 else "bet",
                    "amount": total_amount,
                }
            )
            self.message = f"{current_player.name} {'raises' if call_amount > 0 else 'bets'} {total_amount:.1f}"

        else:
            return {
                "success": False,
                "error": f"Invalid action: {action}",
                "state": self.get_state(),
            }

        # Move to next player
        if not self.game_over:
            self._next_player()

            # Process AI actions automatically
            self._process_ai_turns()

        return {
            "success": True,
            "state": self.get_state(),
        }

    def _process_ai_turns(self):
        """Process AI player actions until it's the human's turn or game is over."""
        while not self.game_over and not self.players[self.current_player_index].is_human:
            self._process_ai_action_internal()

    def _process_ai_action_internal(self):
        """Process an AI player's action internally without recursion."""
        player = self.players[self.current_player_index]

        if player.folded or self.game_over:
            self._next_player()
            return

        # Evaluate hand
        hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
        call_amount = self._get_call_amount(self.current_player_index)

        # Use PokerEngine to decide action
        action, bet_amount = PokerEngine.decide_action(
            hand=hand,
            current_bet=player.current_bet,
            opponent_bet=max(p.current_bet for p in self.players if not p.folded),
            pot=self.pot,
            player_energy=player.energy,
            aggression=player.aggression,
            hole_cards=player.hole_cards,
            community_cards=self.community_cards,
            position_on_button=(self.current_player_index == self.button_index),
        )

        # Process action directly without calling handle_action to avoid recursion
        if action == BettingAction.FOLD:
            player.folded = True
            self.betting_history.append({"player": player.name, "action": "fold", "amount": 0.0})
            self.message = f"{player.name} folds"
            # Check if only one player left
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                self._showdown()
                return

        elif action == BettingAction.CHECK:
            self.betting_history.append({"player": player.name, "action": "check", "amount": 0.0})
            self.message = f"{player.name} checks"

        elif action == BettingAction.CALL:
            if call_amount > player.energy:
                call_amount = player.energy
            self._player_bet(self.current_player_index, call_amount)
            self.betting_history.append(
                {"player": player.name, "action": "call", "amount": call_amount}
            )
            self.message = f"{player.name} calls {call_amount:.1f}"

        elif action == BettingAction.RAISE:
            total_amount = call_amount + bet_amount
            if total_amount > player.energy:
                total_amount = player.energy
            self._player_bet(self.current_player_index, total_amount)
            self.betting_history.append(
                {
                    "player": player.name,
                    "action": "raise" if call_amount > 0 else "bet",
                    "amount": total_amount,
                }
            )
            self.message = (
                f"{player.name} {'raises' if call_amount > 0 else 'bets'} {total_amount:.1f}"
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
            "pot": round(self.pot, 1),
            "current_round": self.current_round.name,
            "community_cards": [str(card) for card in self.community_cards],
            "current_player": current_player.name,
            "is_your_turn": current_player.is_human,
            "game_over": self.game_over,
            "message": self.message,
            "winner": (
                self.players[self.winner_index].name if self.winner_index is not None else None
            ),
            "players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "energy": round(p.energy, 1),
                    "current_bet": round(p.current_bet, 1),
                    "total_bet": round(p.total_bet, 1),
                    "folded": p.folded,
                    "is_human": p.is_human,
                    "algorithm": p.algorithm,
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
            "call_amount": round(self._get_call_amount(0), 1) if not human_player.folded else 0,
            "min_raise": round(self.big_blind, 1),
        }
