"""
Poker game simulation for Texas Hold'em.

This module provides game simulation, pot resolution, and bet finalization logic.
"""

import random
from typing import TYPE_CHECKING, Optional, Tuple

from core.poker.betting.decision import AGGRESSION_MEDIUM
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import PokerHand
from core.poker.evaluation.hand_evaluator import evaluate_hand
from core.poker.simulation.hand_engine import MultiplayerGameState, simulate_hand

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm


def _hand_state_to_poker_game_state(
    state: MultiplayerGameState, button_position: int
) -> PokerGameState:
    """Convert a shared hand-engine state into the legacy heads-up game state."""
    if len(state.players) < 2:
        raise ValueError("Expected at least 2 players in hand state")

    game_state = PokerGameState(
        small_blind=state.small_blind,
        big_blind=state.big_blind,
        button_position=button_position,
        rng=state.deck.rng,
    )
    game_state.deck = state.deck
    game_state.current_round = state.current_round
    game_state.pot = state.pot
    game_state.min_raise = state.min_raise
    game_state.last_raise_amount = state.last_raise_amount

    player_one = state.players[0]
    player_two = state.players[1]

    game_state.player1_current_bet = player_one.current_bet
    game_state.player2_current_bet = player_two.current_bet
    game_state.player1_total_bet = player_one.total_bet
    game_state.player2_total_bet = player_two.total_bet
    game_state.player1_folded = player_one.folded
    game_state.player2_folded = player_two.folded
    game_state.player1_hole_cards = list(player_one.hole_cards)
    game_state.player2_hole_cards = list(player_two.hole_cards)
    game_state.community_cards = list(state.community_cards)
    game_state.player1_hand = state.player_hands.get(0)
    game_state.player2_hand = state.player_hands.get(1)
    game_state.betting_history = [
        (player_id + 1, action, amount) for player_id, action, amount in state.betting_history
    ]

    return game_state


def _resolve_aggression(value: Optional[float]) -> float:
    if value is None:
        return AGGRESSION_MEDIUM
    return value


def simulate_multi_round_game(
    initial_bet: float,
    player1_energy: float,
    player2_energy: float,
    player1_aggression: Optional[float] = None,
    player2_aggression: Optional[float] = None,
    button_position: int = 1,
    player1_strategy: Optional["PokerStrategyAlgorithm"] = None,
    player2_strategy: Optional["PokerStrategyAlgorithm"] = None,
    rng: Optional[random.Random] = None,
) -> PokerGameState:
    """Simulate a complete multi-round Texas Hold'em poker game with blinds.

    Args:
        rng: Optional seeded Random instance for deterministic behavior.
             If not provided, creates a new unseeded Random (non-deterministic).
    """
    if rng is None:
        rng = random.Random()

    button_index = button_position - 1
    if button_index not in (0, 1):
        raise ValueError("button_position must be 1 or 2")

    hand_state = simulate_hand(
        num_players=2,
        initial_bet=initial_bet,
        player_energies=[player1_energy, player2_energy],
        player_aggressions=[
            _resolve_aggression(player1_aggression),
            _resolve_aggression(player2_aggression),
        ],
        player_strategies=[player1_strategy, player2_strategy],
        button_position=button_index,
        rng=rng,
    )

    return _hand_state_to_poker_game_state(hand_state, button_position)


def resolve_bet(
    hand1: PokerHand, hand2: PokerHand, bet1_amount: float, bet2_amount: float
) -> Tuple[float, float]:
    """
    Resolve a poker bet between two hands with proper kicker comparison.

    Returns deltas (profit/loss) for each player. For actual pot distribution,
    use finalize_pot() instead.
    """
    if hand1.beats(hand2):
        return (bet2_amount, -bet2_amount)
    if hand2.beats(hand1):
        return (-bet1_amount, bet1_amount)
    return (0.0, 0.0)


def finalize_pot(game_state: PokerGameState) -> Tuple[float, float]:
    """
    Determines the final payout from the pot to Player 1 and Player 2.

    This method examines the game state (folds, hand rankings) and returns
    the actual pot distribution. For ties, the pot is split equally.
    """
    winner_by_fold = game_state.get_winner_by_fold()
    if winner_by_fold == 1:
        return (game_state.pot, 0.0)
    if winner_by_fold == 2:
        return (0.0, game_state.pot)

    if not game_state.player1_hand:
        game_state.player1_hand = evaluate_hand(
            game_state.player1_hole_cards, game_state.community_cards
        )
    if not game_state.player2_hand:
        game_state.player2_hand = evaluate_hand(
            game_state.player2_hole_cards, game_state.community_cards
        )

    if game_state.player1_hand.beats(game_state.player2_hand):
        return (game_state.pot, 0.0)
    if game_state.player2_hand.beats(game_state.player1_hand):
        return (0.0, game_state.pot)
    half_pot = game_state.pot / 2
    return (half_pot, half_pot)


def simulate_game(
    bet_amount: float = 10.0, player1_energy: float = 100.0, player2_energy: float = 100.0
) -> PokerGameState:
    """Simulate a complete Texas Hold'em poker game between two players."""
    return simulate_multi_round_game(
        initial_bet=bet_amount, player1_energy=player1_energy, player2_energy=player2_energy
    )
