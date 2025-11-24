"""Auto-evaluation poker game for testing fish poker skills.

This module manages automated poker games where multiple fish play against
a standard poker evaluation algorithm for 1000 hands or until one player
runs out of money.
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
from core.poker.strategy.implementations import PokerStrategyAlgorithm

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
    is_standard: bool = False  # True if this is the standard algorithm player
    starting_energy: float = 0.0
    # For fish player
    poker_strategy: Optional[PokerStrategyAlgorithm] = None
    fish_id: Optional[int] = None
    fish_generation: Optional[int] = None
    plant_id: Optional[int] = None
    species: str = "fish"
    # Stats tracking
    hands_won: int = 0
    hands_lost: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0


@dataclass
class AutoEvaluateStats:
    """Statistics for the auto-evaluation game."""

    hands_played: int = 0
    hands_remaining: int = 1000
    players: List[Dict[str, Any]] = field(default_factory=list)  # List of player stats
    game_over: bool = False
    winner: Optional[str] = None
    reason: str = ""
    performance_history: List[Dict[str, Any]] = field(default_factory=list)


class AutoEvaluatePokerGame:
    """Manages an automated poker evaluation game between multiple fish and standard algorithm."""

    def __init__(
        self,
        game_id: str,
        player_pool: List[Dict[str, Any]],
        standard_energy: float = 500.0,
        max_hands: int = 1000,
        small_blind: float = 5.0,
        big_blind: float = 10.0,
    ):
        """Initialize a new auto-evaluation poker game.

        Args:
            game_id: Unique identifier for this game
            player_pool: Benchmark players (fish and/or plants) containing
                at least a "name" and "poker_strategy" key. Optional metadata
                such as fish_id, plant_id, generation, or species is preserved
                for downstream reporting.
            standard_energy: Starting energy for standard algorithm player
            max_hands: Maximum number of hands to play (default 1000)
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.game_id = game_id
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_hands = max_hands
        self.hands_played = 0

        # Create players list
        self.players: List[EvalPlayerState] = []

        # Add fish players - ensure they have enough energy to play all hands
        # With 4 players, blinds rotate, so each player posts SB+BB every 4 hands
        # Minimum energy needed: (SB + BB) * (max_hands / num_players) * 2
        min_energy_needed = (small_blind + big_blind) * (max_hands / len(player_pool) + 1) * 2
        starting_energy = max(standard_energy, min_energy_needed)

        for i, player_data in enumerate(player_pool):
            self.players.append(
                EvalPlayerState(
                    player_id=f"fish_{i}",
                    name=player_data["name"],
                    energy=starting_energy,
                    starting_energy=starting_energy,
                    poker_strategy=player_data["poker_strategy"],
                    fish_id=player_data.get("fish_id"),
                    fish_generation=player_data.get("generation"),
                    plant_id=player_data.get("plant_id"),
                    species=player_data.get("species", "fish"),
                    is_standard=False,
                )
            )

        # Add standard algorithm player
        self.players.append(
            EvalPlayerState(
                player_id="standard",
                name="Standard Algorithm",
                energy=starting_energy,
                is_standard=True,
                starting_energy=starting_energy,
            )
        )

        # Game state
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.button_position = 0  # Dealer button position
        self.current_player_index = 0
        self.game_over = False
        self.winner: Optional[str] = None
        self.last_hand_message = ""
        self.performance_history: List[Dict[str, Any]] = []

    def get_players(self) -> List[EvalPlayerState]:
        """Get list of players."""
        return self.players

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

        # Rotate button
        num_players = len(self.players)
        self.button_position = (self.button_position + 1) % num_players

        # Post blinds (small blind is player after button, big blind is next player)
        small_blind_index = (self.button_position + 1) % num_players
        big_blind_index = (self.button_position + 2) % num_players

        self._player_bet(small_blind_index, self.small_blind)
        self._player_bet(big_blind_index, self.big_blind)

        # First to act pre-flop is player after big blind
        self.current_player_index = (big_blind_index + 1) % num_players

        self.hands_played += 1

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
        player = self.players[player_index]
        max_bet = max(p.current_bet for p in self.players if not p.folded)
        return max_bet - player.current_bet

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
        for player in self.players:
            player.current_bet = 0.0

        # First to act post-flop is player after button
        num_players = len(self.players)
        self.current_player_index = (self.button_position + 1) % num_players
        # Skip folded players
        while self.players[self.current_player_index].folded:
            self.current_player_index = (self.current_player_index + 1) % num_players

    def _showdown(self):
        """Determine winner at showdown."""
        active_players = [i for i, p in enumerate(self.players) if not p.folded]

        # If only one player left, they win
        if len(active_players) == 1:
            self._award_pot(active_players[0])
            return

        # Evaluate hands for all active players
        best_hand: Optional[PokerHand] = None
        best_player_index: Optional[int] = None
        tied_players: List[int] = []

        for i in active_players:
            player = self.players[i]
            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
            logger.debug(f"Auto-eval {self.game_id}: {player.name}: {hand}")

            if best_hand is None or hand.beats(best_hand):
                best_hand = hand
                best_player_index = i
                tied_players = [i]
            elif hand.ties(best_hand):
                tied_players.append(i)

        # Award pot to winner(s)
        if len(tied_players) > 1:
            self._split_pot(tied_players)
            self.last_hand_message = f"Tie! Pot split among {len(tied_players)} players."
        elif best_player_index is not None:
            self._award_pot(best_player_index)
            winner = self.players[best_player_index]
            self.last_hand_message = f"{winner.name} wins with {best_hand}!"

    def _award_pot(self, winner_index: int):
        """Award the pot to the winner."""
        winner = self.players[winner_index]

        winner.energy += self.pot
        winner.hands_won += 1
        winner.total_energy_won += self.pot

        # Track losses for non-winners who didn't fold
        for i, player in enumerate(self.players):
            if i != winner_index and player.total_bet > 0:
                player.hands_lost += 1
                player.total_energy_lost += player.total_bet



    def _split_pot(self, tied_player_indices: List[int]):
        """Split the pot among tied players."""
        split_amount = self.pot / len(tied_player_indices)
        for i in tied_player_indices:
            self.players[i].energy += split_amount
            self.players[i].total_energy_won += split_amount

    def _process_player_action(self, player_index: int):
        """Process a player's action."""
        player = self.players[player_index]

        if player.folded:
            return

        call_amount = self._get_call_amount(player_index)

        # Can't call - must fold
        if call_amount > player.energy:
            player.folded = True
            logger.debug(f"Auto-eval {self.game_id}: {player.name} folds (insufficient energy)")
            return

        # Determine action based on player type
        if player.is_standard:  # Standard player
            # Use PokerEngine.decide_action (standard algorithm)
            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
            max_opponent_bet = max(p.current_bet for p in self.players if not p.folded)

            action, amount = PokerEngine.decide_action(
                hand=hand,
                current_bet=player.current_bet,
                opponent_bet=max_opponent_bet,
                pot=self.pot,
                player_energy=player.energy,
                aggression=0.5,  # Medium aggression
                hole_cards=player.hole_cards,
                community_cards=self.community_cards if self.community_cards else None,
                position_on_button=(player_index == self.button_position),
            )

        else:  # Fish player
            # Use fish's poker strategy
            hand = PokerEngine.evaluate_hand(player.hole_cards, self.community_cards)
            hand_strength = hand.rank_value / 10.0  # Normalize to 0-1
            max_opponent_bet = max(p.current_bet for p in self.players if not p.folded)

            action, amount = player.poker_strategy.decide_action(
                hand_strength=hand_strength,
                current_bet=player.current_bet,
                opponent_bet=max_opponent_bet,
                pot=self.pot,
                player_energy=player.energy,
                position_on_button=(player_index == self.button_position),
            )

        # Execute action
        if action == BettingAction.FOLD:
            player.folded = True
            logger.debug(f"Auto-eval {self.game_id}: {player.name} folds")

        elif action == BettingAction.CHECK:
            logger.debug(f"Auto-eval {self.game_id}: {player.name} checks")

        elif action == BettingAction.CALL:
            if call_amount > player.energy:
                call_amount = player.energy
            self._player_bet(player_index, call_amount)
            logger.debug(f"Auto-eval {self.game_id}: {player.name} calls {call_amount:.1f}")

        elif action == BettingAction.RAISE:
            total_amount = call_amount + amount
            if total_amount > player.energy:
                total_amount = player.energy
            self._player_bet(player_index, total_amount)
            logger.debug(f"Auto-eval {self.game_id}: {player.name} raises {total_amount:.1f}")

    def _play_betting_round(self):
        """Play one betting round."""
        max_actions = 100  # Prevent infinite loops (increased for multi-player)
        actions_taken = 0
        num_players = len(self.players)

        while actions_taken < max_actions:
            current = self.players[self.current_player_index]

            # If current player folded, skip to next
            if current.folded:
                self.current_player_index = (self.current_player_index + 1) % num_players
                actions_taken += 1
                continue

            # Process action
            self._process_player_action(self.current_player_index)

            # Check if only one player left
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) <= 1:
                break

            # Check if betting is complete
            if self._is_betting_complete():
                break

            # Move to next player
            self.current_player_index = (self.current_player_index + 1) % num_players
            actions_taken += 1

    def _is_betting_complete(self) -> bool:
        """Check if betting is complete for the current round."""
        active_players = [p for p in self.players if not p.folded]

        # If only one player left, betting is done
        if len(active_players) <= 1:
            return True

        # Get max bet
        max_bet = max(p.current_bet for p in active_players)

        # Check if all active players have matched max bet
        for player in active_players:
            if player.current_bet < max_bet and player.energy > 0:
                return False

        return True

    def play_hand(self):
        """Play one complete hand of poker."""
        self._start_hand()

        # Play pre-flop
        self._play_betting_round()

        # Continue through remaining rounds if more than one player active
        while self.current_round != BettingRound.SHOWDOWN:
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) <= 1:
                # Someone won by everyone else folding
                self._showdown()
                break

            self._advance_round()
            if self.current_round != BettingRound.SHOWDOWN:
                self._play_betting_round()

        # If we haven't had a showdown yet, trigger it
        if self.current_round != BettingRound.SHOWDOWN:
            self._showdown()

        # Capture performance snapshot after each hand
        self._record_hand_performance()

    def _record_hand_performance(self):
        """Record net energy performance for all players after a hand."""
        snapshot: Dict[str, Any] = {
            "hand": self.hands_played,
            "players": [],
        }

        for player in self.players:
            snapshot["players"].append(
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "is_standard": player.is_standard,
                    "species": getattr(player, "species", "fish"),
                    "energy": round(player.energy, 1),
                    "net_energy": round(player.energy - player.starting_energy, 1),
                }
            )

        self.performance_history.append(snapshot)

    def run_evaluation(self) -> AutoEvaluateStats:
        """Run the full evaluation (max_hands or until only one player remains).

        Returns:
            Final evaluation statistics
        """
        # Auto-evaluation runs silently in background

        # Baseline snapshot before any hands are played
        self._record_hand_performance()

        while self.hands_played < self.max_hands:
            # Check how many players can still play (have energy >= big blind)
            active_players = [p for p in self.players if p.energy >= self.big_blind]

            if len(active_players) <= 1:
                # Only one player left who can afford to play
                self.game_over = True
                if len(active_players) == 1:
                    self.winner = active_players[0].name
                break

            # Play one hand
            self.play_hand()

        # If we completed all hands, determine winner by energy
        if not self.game_over:
            self.game_over = True
            # Find player with most energy
            max_energy = max(p.energy for p in self.players)
            winners = [p for p in self.players if p.energy == max_energy]

            if len(winners) == 1:
                self.winner = winners[0].name
            else:
                self.winner = "Tie"

        return self.get_stats()

    def get_stats(self) -> AutoEvaluateStats:
        """Get current evaluation statistics."""
        # Build player stats list
        players_stats = []
        for player in self.players:
            players_stats.append(
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "is_standard": player.is_standard,
                    "fish_id": player.fish_id,
                    "fish_generation": player.fish_generation,
                    "plant_id": player.plant_id,
                    "species": player.species,
                    "energy": round(player.energy, 1),
                    "hands_won": player.hands_won,
                    "hands_lost": player.hands_lost,
                    "total_energy_won": round(player.total_energy_won, 1),
                    "total_energy_lost": round(player.total_energy_lost, 1),
                    "net_energy": round(player.total_energy_won - player.total_energy_lost, 1),
                }
            )

        return AutoEvaluateStats(
            hands_played=self.hands_played,
            hands_remaining=max(0, self.max_hands - self.hands_played),
            players=players_stats,
            game_over=self.game_over,
            winner=self.winner,
            reason=(
                f"Completed {self.hands_played} hands"
                if self.hands_played >= self.max_hands
                else f"Game ended after {self.hands_played} hands"
            ),
            performance_history=self.performance_history,
        )
