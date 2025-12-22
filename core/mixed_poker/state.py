"""Player and game state for multiplayer poker.

This module contains the runtime state tracking classes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant

Player = Union["Fish", "Plant"]


@dataclass
class MultiplayerPlayerContext:
    """Runtime state for a player in multiplayer poker."""
    player: Player
    player_idx: int
    remaining_energy: float
    aggression: float
    current_bet: float = 0.0
    total_bet: float = 0.0
    folded: bool = False
    is_all_in: bool = False
    strategy: Optional[Any] = None


class MultiplayerGameState:
    """Tracks the state of a multiplayer Texas Hold'em poker game."""

    def __init__(
        self,
        num_players: int,
        small_blind: float = 2.5,
        big_blind: float = 5.0,
        button_position: int = 0,
    ) -> None:
        # Import at runtime to avoid circular imports
        from core.poker.core.cards import Deck

        self.num_players = num_players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.button_position = button_position

        # Initialize deck and state
        self.deck = Deck()
        self.deck.shuffle()
        self.community_cards: List[Tuple[int, int]] = []
        self.hole_cards: List[List[Tuple[int, int]]] = [[] for _ in range(num_players)]
        self.pot: float = 0.0
        self.current_round: int = 0  # MultiplayerBettingRound
        self.current_bets: List[float] = [0.0] * num_players
        self.folded: List[bool] = [False] * num_players
        self.player_hands: Dict[int, Any] = {}  # maps to PokerHand
        self.betting_history: List[Tuple[int, Any, float]] = []

    def deal_hole_cards(self) -> None:
        """Deal 2 hole cards to each player."""
        for i in range(self.num_players):
            self.hole_cards[i] = [self.deck.draw(), self.deck.draw()]

    def deal_flop(self) -> None:
        """Deal the flop (3 community cards)."""
        self.community_cards = [self.deck.draw() for _ in range(3)]

    def deal_turn(self) -> None:
        """Deal the turn (4th community card)."""
        self.community_cards.append(self.deck.draw())

    def deal_river(self) -> None:
        """Deal the river (5th community card)."""
        self.community_cards.append(self.deck.draw())

    def advance_round(self) -> None:
        """Move to the next betting round."""
        from core.mixed_poker.types import MultiplayerBettingRound

        self.current_round += 1
        # Reset current bets for new round
        self.current_bets = [0.0] * self.num_players

        # Deal community cards based on round
        if self.current_round == MultiplayerBettingRound.FLOP:
            self.deal_flop()
        elif self.current_round == MultiplayerBettingRound.TURN:
            self.deal_turn()
        elif self.current_round == MultiplayerBettingRound.RIVER:
            self.deal_river()

    def player_bet(self, player_idx: int, amount: float) -> None:
        """Record a player's bet."""
        self.current_bets[player_idx] += amount
        self.pot += amount

    def get_active_player_count(self) -> int:
        """Return number of players still in the hand."""
        return sum(1 for f in self.folded if not f)

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner index if only one player remains, None otherwise."""
        active = [i for i, f in enumerate(self.folded) if not f]
        if len(active) == 1:
            return active[0]
        return None

    def get_max_current_bet(self) -> float:
        """Get the highest current bet among active players."""
        return max(
            bet for i, bet in enumerate(self.current_bets)
            if not self.folded[i]
        )

    def is_betting_complete(self) -> bool:
        """Check if betting round is complete."""
        active_players = [
            i for i in range(self.num_players) if not self.folded[i]
        ]
        if len(active_players) <= 1:
            return True

        max_bet = self.get_max_current_bet()
        # All active players must have matched the max bet
        for i in active_players:
            if self.current_bets[i] < max_bet:
                return False
        return True

    def evaluate_hands(self) -> None:
        """Evaluate hands for all active players."""
        from core.poker_interaction import PokerHand

        for i in range(self.num_players):
            if not self.folded[i] and self.hole_cards[i]:
                combined = self.hole_cards[i] + self.community_cards
                self.player_hands[i] = PokerHand.from_cards(combined)

