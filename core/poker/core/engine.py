"""
Poker game engine implementing Texas Hold'em rules and betting logic.

This module provides backward-compatible re-exports from the refactored
poker modules. For new code, prefer importing directly from:
- core.poker.betting.actions: BettingAction, BettingRound
- core.poker.betting.decision: decide_action
- core.poker.core.game_state: PokerGameState
- core.poker.evaluation.hand_evaluator: evaluate_hand
- core.poker.simulation.engine: simulate_multi_round_game, finalize_pot, resolve_bet
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

# Re-export all public symbols for backward compatibility
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import (
    AGGRESSION_HIGH,
    AGGRESSION_LOW,
    AGGRESSION_MEDIUM,
    decide_action as _decide_action,
    _decide_strong_hand_action,
    _decide_medium_hand_action,
    _decide_weak_hand_action,
)
from core.poker.core.cards import Card, Deck, Rank, Suit, get_card
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import HandRank, PokerHand
from core.poker.evaluation.hand_evaluator import (
    evaluate_hand as _evaluate_hand,
    evaluate_hand_cached as _evaluate_hand_cached,
    _evaluate_five_cards,
    _evaluate_five_cards_cached,
    _evaluate_five_cards_core,
    _rank_name,
)
from core.poker.evaluation.strength import (
    calculate_pot_odds,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)
from core.poker.simulation.engine import (
    finalize_pot as _finalize_pot,
    resolve_bet as _resolve_bet,
    simulate_game as _simulate_game,
    simulate_multi_round_game as _simulate_multi_round_game,
)

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


class PokerEngine:
    """Core poker game logic for fish interactions with authentic Texas Hold'em.

    This class is maintained for backward compatibility. It delegates to
    the refactored modules and provides class-level access to the same functions.

    For new code, consider importing the functions directly:
    - evaluate_hand from core.poker.evaluation.hand_evaluator
    - decide_action from core.poker.betting.decision
    - simulate_multi_round_game from core.poker.simulation.engine
    """

    # Aggression constants
    AGGRESSION_LOW = AGGRESSION_LOW
    AGGRESSION_MEDIUM = AGGRESSION_MEDIUM
    AGGRESSION_HIGH = AGGRESSION_HIGH

    # Pre-computed rank names for fast lookup (index 0-14, only 2-14 valid)
    _RANK_NAMES = ("", "", "2", "3", "4", "5", "6", "7", "8", "9", "Ten", "Jack", "Queen", "King", "Ace")

    @staticmethod
    def _rank_name(rank: int) -> str:
        """Get the name of a rank."""
        return _rank_name(rank)

    @staticmethod
    def _evaluate_five_cards_core(
        ranks: List[int], suits: List[int]
    ) -> Tuple[str, HandRank, str, List[int], List[int]]:
        """Core 5-card evaluation logic."""
        return _evaluate_five_cards_core(ranks, suits)

    @staticmethod
    def _evaluate_five_cards(cards: List[Card]) -> PokerHand:
        """Evaluate exactly 5 Card objects and return the poker hand."""
        return _evaluate_five_cards(cards)

    @staticmethod
    def evaluate_hand(hole_cards: List[Card], community_cards: List[Card]) -> PokerHand:
        """Evaluate the best 5-card poker hand from hole cards and community cards."""
        return _evaluate_hand(hole_cards, community_cards)

    @staticmethod
    def evaluate_hand_cached(hole_key: Tuple[int, ...], community_key: Tuple[int, ...]) -> PokerHand:
        """Cached evaluate_hand that uses compact int keys for input cards."""
        return _evaluate_hand_cached(hole_key, community_key)

    @staticmethod
    def _evaluate_five_cards_cached(five_cards_key: Tuple[int, int, int, int, int]) -> PokerHand:
        """Cached hand evaluation using compact int keys."""
        return _evaluate_five_cards_cached(five_cards_key)

    @staticmethod
    def _decide_strong_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for strong hands (flush or better)."""
        return _decide_strong_hand_action(call_amount, pot, player_energy, aggression)

    @staticmethod
    def _decide_medium_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for medium hands (pair through straight)."""
        return _decide_medium_hand_action(call_amount, pot, player_energy, aggression)

    @staticmethod
    def _decide_weak_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for weak hands (high card)."""
        return _decide_weak_hand_action(call_amount, pot, player_energy, aggression)

    @staticmethod
    def decide_action(
        hand: PokerHand,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        aggression: float = None,
        hole_cards: Optional[List[Card]] = None,
        community_cards: Optional[List[Card]] = None,
        position_on_button: bool = False,
    ) -> Tuple[BettingAction, float]:
        """Decide what action to take based on hand strength and game state."""
        return _decide_action(
            hand=hand,
            current_bet=current_bet,
            opponent_bet=opponent_bet,
            pot=pot,
            player_energy=player_energy,
            aggression=aggression,
            hole_cards=hole_cards,
            community_cards=community_cards,
            position_on_button=position_on_button,
        )

    @staticmethod
    def simulate_multi_round_game(
        initial_bet: float,
        player1_energy: float,
        player2_energy: float,
        player1_aggression: float = None,
        player2_aggression: float = None,
        button_position: int = 1,
        player1_strategy: Optional["PokerStrategyAlgorithm"] = None,
        player2_strategy: Optional["PokerStrategyAlgorithm"] = None,
    ) -> PokerGameState:
        """Simulate a complete multi-round Texas Hold'em poker game with blinds."""
        return _simulate_multi_round_game(
            initial_bet=initial_bet,
            player1_energy=player1_energy,
            player2_energy=player2_energy,
            player1_aggression=player1_aggression,
            player2_aggression=player2_aggression,
            button_position=button_position,
            player1_strategy=player1_strategy,
            player2_strategy=player2_strategy,
        )

    @staticmethod
    def resolve_bet(
        hand1: PokerHand, hand2: PokerHand, bet1_amount: float, bet2_amount: float
    ) -> Tuple[float, float]:
        """Resolve a poker bet between two hands with proper kicker comparison."""
        return _resolve_bet(hand1, hand2, bet1_amount, bet2_amount)

    @staticmethod
    def finalize_pot(game_state: PokerGameState) -> Tuple[float, float]:
        """Determines the final payout from the pot to Player 1 and Player 2."""
        return _finalize_pot(game_state)

    @staticmethod
    def simulate_game(
        bet_amount: float = 10.0, player1_energy: float = 100.0, player2_energy: float = 100.0
    ) -> PokerGameState:
        """Simulate a complete Texas Hold'em poker game between two players."""
        return _simulate_game(bet_amount, player1_energy, player2_energy)


__all__ = [
    # Enums
    "BettingAction",
    "BettingRound",
    # Classes
    "PokerEngine",
    "PokerGameState",
    # Constants
    "AGGRESSION_HIGH",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
]
