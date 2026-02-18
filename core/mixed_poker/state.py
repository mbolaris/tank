"""Player and game state for multiplayer poker.

This module contains the runtime state tracking classes.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from core.mixed_poker.types import MultiplayerBettingRound, Player
from core.poker.betting.actions import BettingAction
from core.poker.core import Deck, PokerHand, evaluate_hand

if TYPE_CHECKING:
    pass


@dataclass
class MultiplayerPlayerContext:
    """Runtime state for a player in multiplayer poker."""

    player: Player
    player_idx: int  # 0-indexed position at table
    remaining_energy: float
    aggression: float
    current_bet: float = 0.0  # Bet in current betting round
    total_bet: float = 0.0  # Total bet across all rounds
    folded: bool = False
    is_all_in: bool = False
    strategy: Optional[Any] = None  # PokerStrategyAlgorithm if available


class MultiplayerGameState:
    """Tracks the state of a multiplayer Texas Hold'em poker game."""

    def __init__(
        self,
        num_players: int,
        small_blind: float = 2.5,
        big_blind: float = 5.0,
        button_position: int = 0,
        rng: Optional[Any] = None,
    ):
        self.num_players = num_players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.button_position = button_position  # 0-indexed

        self.current_round = MultiplayerBettingRound.PRE_FLOP
        self.pot = 0.0
        self.deck = Deck(rng=rng)

        # Per-player state
        self.player_hole_cards: list[list[Any]] = [[] for _ in range(num_players)]
        self.player_hands: list[Optional[PokerHand]] = [None] * num_players
        self.player_current_bets: list[float] = [0.0] * num_players
        self.player_total_bets: list[float] = [0.0] * num_players
        self.player_folded: list[bool] = [False] * num_players
        self.player_all_in: list[bool] = [False] * num_players

        self.community_cards: list[Any] = []
        self.betting_history: list[tuple[int, BettingAction, float]] = []

        # Raise tracking
        self.min_raise = big_blind
        self.last_raise_amount = big_blind
        self.last_aggressor: Optional[int] = None  # Who made the last raise

    def deal_hole_cards(self) -> None:
        """Deal 2 hole cards to each player."""
        for _ in range(2):
            for player_idx in range(self.num_players):
                if not self.player_folded[player_idx]:
                    self.player_hole_cards[player_idx].append(self.deck.deal_one())

    def deal_flop(self) -> None:
        """Deal the flop (3 community cards)."""
        self.deck.deal(1)  # Burn
        self.community_cards.extend(self.deck.deal(3))

    def deal_turn(self) -> None:
        """Deal the turn (4th community card)."""
        self.deck.deal(1)  # Burn
        self.community_cards.append(self.deck.deal_one())

    def deal_river(self) -> None:
        """Deal the river (5th community card)."""
        self.deck.deal(1)  # Burn
        self.community_cards.append(self.deck.deal_one())

    def advance_round(self) -> None:
        """Move to the next betting round."""
        if self.current_round < MultiplayerBettingRound.SHOWDOWN:
            self.current_round = MultiplayerBettingRound(self.current_round + 1)

            if self.current_round == MultiplayerBettingRound.FLOP:
                self.deal_flop()
            elif self.current_round == MultiplayerBettingRound.TURN:
                self.deal_turn()
            elif self.current_round == MultiplayerBettingRound.RIVER:
                self.deal_river()

            # Reset current round bets
            self.player_current_bets = [0.0] * self.num_players
            self.min_raise = self.big_blind
            self.last_raise_amount = self.big_blind
            self.last_aggressor = None

    def player_bet(self, player_idx: int, amount: float) -> None:
        """Record a player's bet."""
        self.player_current_bets[player_idx] += amount
        self.player_total_bets[player_idx] += amount
        self.pot += amount

    def get_active_player_count(self) -> int:
        """Return number of players still in the hand."""
        return sum(1 for folded in self.player_folded if not folded)

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner index if only one player remains, None otherwise."""
        active_players = [i for i, folded in enumerate(self.player_folded) if not folded]
        if len(active_players) == 1:
            return active_players[0]
        return None

    def get_max_current_bet(self) -> float:
        """Get the highest current bet among active players."""
        return max(
            bet for i, bet in enumerate(self.player_current_bets) if not self.player_folded[i]
        )

    def is_betting_complete(self) -> bool:
        """Check if betting round is complete."""
        active_players = [
            i
            for i in range(self.num_players)
            if not self.player_folded[i] and not self.player_all_in[i]
        ]

        if not active_players:
            return True

        max_bet = self.get_max_current_bet()
        return all(self.player_current_bets[i] == max_bet for i in active_players)

    def evaluate_hands(self) -> None:
        """Evaluate hands for all active players."""
        for i in range(self.num_players):
            if not self.player_folded[i]:
                self.player_hands[i] = evaluate_hand(
                    self.player_hole_cards[i], self.community_cards
                )
