"""
Poker game simulation for Texas Hold'em.

This module provides game simulation, pot resolution, and bet finalization logic.
"""

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from core.config.poker import (
    POKER_MAX_ACTIONS_PER_ROUND,
    POKER_MAX_HAND_RANK,
)
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import AGGRESSION_MEDIUM, decide_action
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import PokerHand
from core.poker.evaluation.hand_evaluator import evaluate_hand
from core.poker.evaluation.strength import evaluate_starting_hand_strength

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class _HandEvaluationCache:
    community_cards_seen: int
    hands: Dict[int, PokerHand]


@dataclass
class PlayerContext:
    """Runtime state needed to evaluate betting decisions."""

    remaining_energy: float
    aggression: float
    strategy: Optional["PokerStrategyAlgorithm"]


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
    # Create RNG if not provided (for backward compatibility)
    if rng is None:
        rng = random.Random()

    contexts = _build_player_contexts(
        player1_energy=player1_energy,
        player2_energy=player2_energy,
        player1_aggression=player1_aggression or AGGRESSION_MEDIUM,
        player2_aggression=player2_aggression or AGGRESSION_MEDIUM,
        player1_strategy=player1_strategy,
        player2_strategy=player2_strategy,
    )

    game_state = _create_game_state(initial_bet, button_position, contexts)
    _play_betting_rounds(game_state, contexts, button_position, rng)
    _evaluate_final_hands(game_state)
    return game_state


def _build_player_contexts(
    *,
    player1_energy: float,
    player2_energy: float,
    player1_aggression: float,
    player2_aggression: float,
    player1_strategy: Optional["PokerStrategyAlgorithm"],
    player2_strategy: Optional["PokerStrategyAlgorithm"],
) -> Dict[int, PlayerContext]:
    return {
        1: PlayerContext(
            remaining_energy=player1_energy,
            aggression=player1_aggression,
            strategy=player1_strategy,
        ),
        2: PlayerContext(
            remaining_energy=player2_energy,
            aggression=player2_aggression,
            strategy=player2_strategy,
        ),
    }


def _create_game_state(
    initial_bet: float, button_position: int, contexts: Dict[int, PlayerContext]
) -> PokerGameState:
    big_blind = min(initial_bet, contexts[1].remaining_energy, contexts[2].remaining_energy)
    small_blind = min(initial_bet / 2, big_blind / 2, contexts[1].remaining_energy, contexts[2].remaining_energy)

    game_state = PokerGameState(
        small_blind=small_blind, big_blind=big_blind, button_position=button_position
    )
    game_state.deal_cards()

    if button_position == 1:
        small_blind_player = 1
        big_blind_player = 2
    else:
        small_blind_player = 2
        big_blind_player = 1

    game_state.player_bet(small_blind_player, small_blind)
    game_state.player_bet(big_blind_player, big_blind)

    contexts[small_blind_player].remaining_energy -= small_blind
    contexts[big_blind_player].remaining_energy -= big_blind
    return game_state


def _play_betting_rounds(
    game_state: PokerGameState,
    contexts: Dict[int, PlayerContext],
    button_position: int,
    rng: random.Random,
) -> None:
    hand_cache = _HandEvaluationCache(
        community_cards_seen=len(game_state.community_cards), hands={}
    )

    for round_num in range(4):  # Pre-flop, Flop, Turn, River
        if game_state.get_winner_by_fold() is not None:
            break

        if round_num > 0:
            game_state.advance_round()
            hand_cache.hands.clear()
            hand_cache.community_cards_seen = len(game_state.community_cards)

        current_player = button_position if round_num == 0 else 2 if button_position == 1 else 1
        actions_this_round = 0

        while actions_this_round < POKER_MAX_ACTIONS_PER_ROUND:
            remaining_energy = contexts[current_player].remaining_energy
            action, bet_amount = _decide_player_action(
                current_player=current_player,
                game_state=game_state,
                contexts=contexts,
                button_position=button_position,
                hand_cache=hand_cache,
                rng=rng,
            )

            if _apply_action(
                current_player=current_player,
                action=action,
                bet_amount=bet_amount,
                remaining_energy=remaining_energy,
                game_state=game_state,
                contexts=contexts,
            ):
                break

            actions_this_round += 1

            if _round_is_complete(game_state, actions_this_round):
                break

            current_player = 2 if current_player == 1 else 1

        _refund_unmatched_bets(game_state, contexts)


def _decide_player_action(
    *,
    current_player: int,
    game_state: PokerGameState,
    contexts: Dict[int, PlayerContext],
    button_position: int,
    hand_cache: _HandEvaluationCache,
    rng: random.Random,
):
    hand = _evaluate_hand_for_player(current_player, game_state, hand_cache)

    current_bet = (
        game_state.player1_current_bet
        if current_player == 1
        else game_state.player2_current_bet
    )
    opponent_bet = (
        game_state.player2_current_bet
        if current_player == 1
        else game_state.player1_current_bet
    )

    context = contexts[current_player]
    player_on_button = current_player == button_position
    hole_cards = (
        game_state.player1_hole_cards if current_player == 1 else game_state.player2_hole_cards
    )

    player_strategy = context.strategy
    if player_strategy is not None:
        # Use starting hand evaluation for pre-flop to match standard algorithm's info
        is_preflop = len(game_state.community_cards) == 0
        if is_preflop and hole_cards and len(hole_cards) == 2:
            # Pre-flop: use starting hand strength like the standard algorithm
            hand_strength = evaluate_starting_hand_strength(hole_cards, player_on_button)
        else:
            # Post-flop: use evaluated hand rank
            hand_strength = hand.rank_value / POKER_MAX_HAND_RANK
        return player_strategy.decide_action(
            hand_strength=hand_strength,
            current_bet=current_bet,
            opponent_bet=opponent_bet,
            pot=game_state.pot,
            player_energy=context.remaining_energy,
            position_on_button=player_on_button,
        )

    return decide_action(
        hand=hand,
        current_bet=current_bet,
        opponent_bet=opponent_bet,
        pot=game_state.pot,
        player_energy=context.remaining_energy,
        aggression=context.aggression,
        hole_cards=hole_cards,
        community_cards=game_state.community_cards,
        position_on_button=player_on_button,
        rng=rng,
    )


def _evaluate_hand_for_player(
    current_player: int,
    game_state: PokerGameState,
    hand_cache: _HandEvaluationCache,
) -> PokerHand:
    community_len = len(game_state.community_cards)
    if community_len != hand_cache.community_cards_seen:
        hand_cache.hands.clear()
        hand_cache.community_cards_seen = community_len

    if current_player in hand_cache.hands:
        return hand_cache.hands[current_player]

    if current_player == 1:
        hand = evaluate_hand(game_state.player1_hole_cards, game_state.community_cards)
    else:
        hand = evaluate_hand(game_state.player2_hole_cards, game_state.community_cards)

    hand_cache.hands[current_player] = hand
    return hand


def _apply_action(
    *,
    current_player: int,
    action: BettingAction,
    bet_amount: float,
    remaining_energy: float,
    game_state: PokerGameState,
    contexts: Dict[int, PlayerContext],
) -> bool:
    if action == BettingAction.FOLD:
        game_state.betting_history.append((current_player, action, 0.0))
        if current_player == 1:
            game_state.player1_folded = True
        else:
            game_state.player2_folded = True
        return True

    if action == BettingAction.CHECK:
        game_state.betting_history.append((current_player, action, 0.0))
        return False

    if action == BettingAction.CALL:
        call_amount = _calculate_call_amount(current_player, game_state)
        actual_call = min(call_amount, remaining_energy)

        game_state.betting_history.append((current_player, action, actual_call))
        game_state.player_bet(current_player, actual_call)
        contexts[current_player].remaining_energy -= actual_call
        return False

    if action == BettingAction.RAISE:
        call_amount = _calculate_call_amount(current_player, game_state)
        call_payment = min(call_amount, remaining_energy)
        remaining_after_call = remaining_energy - call_payment

        actual_raise = _calculate_actual_raise(
            bet_amount=bet_amount,
            available_energy=remaining_after_call,
            game_state=game_state,
        )

        total_bet = call_payment + actual_raise
        game_state.player_bet(current_player, total_bet)

        if actual_raise > 0:
            game_state.betting_history.append((current_player, action, actual_raise))
            game_state.last_raise_amount = actual_raise
            game_state.min_raise = actual_raise
        else:
            game_state.betting_history.append(
                (current_player, BettingAction.CALL, call_payment)
            )

        contexts[current_player].remaining_energy -= total_bet
        return False

    logger.warning("Unknown betting action %s", action)
    return False


def _calculate_call_amount(current_player: int, game_state: PokerGameState) -> float:
    if current_player == 1:
        return max(0.0, game_state.player2_current_bet - game_state.player1_current_bet)
    return max(0.0, game_state.player1_current_bet - game_state.player2_current_bet)


def _calculate_actual_raise(
    *, bet_amount: float, available_energy: float, game_state: PokerGameState
) -> float:
    if available_energy < game_state.min_raise:
        return 0.0

    actual_raise = max(bet_amount, game_state.min_raise)
    return min(actual_raise, available_energy)


def _round_is_complete(game_state: PokerGameState, actions_this_round: int) -> bool:
    return (
        game_state.player1_current_bet == game_state.player2_current_bet
        and actions_this_round >= 2
    )


def _refund_unmatched_bets(
    game_state: PokerGameState, contexts: Dict[int, PlayerContext]
) -> None:
    if game_state.player1_current_bet == game_state.player2_current_bet:
        return

    min_bet = min(game_state.player1_current_bet, game_state.player2_current_bet)

    if game_state.player1_current_bet > min_bet:
        _refund_player_one(game_state, contexts, min_bet)
    elif game_state.player2_current_bet > min_bet:
        _refund_player_two(game_state, contexts, min_bet)


def _refund_player_one(
    game_state: PokerGameState, contexts: Dict[int, PlayerContext], min_bet: float
) -> None:
    refund = game_state.player1_current_bet - min_bet
    game_state.player1_current_bet = min_bet
    game_state.player1_total_bet -= refund
    game_state.pot -= refund
    contexts[1].remaining_energy += refund


def _refund_player_two(
    game_state: PokerGameState, contexts: Dict[int, PlayerContext], min_bet: float
) -> None:
    refund = game_state.player2_current_bet - min_bet
    game_state.player2_current_bet = min_bet
    game_state.player2_total_bet -= refund
    game_state.pot -= refund
    contexts[2].remaining_energy += refund


def _evaluate_final_hands(game_state: PokerGameState) -> None:
    game_state.current_round = BettingRound.SHOWDOWN

    if not game_state.player1_folded:
        game_state.player1_hand = evaluate_hand(
            game_state.player1_hole_cards, game_state.community_cards
        )
    if not game_state.player2_folded:
        game_state.player2_hand = evaluate_hand(
            game_state.player2_hole_cards, game_state.community_cards
        )


def resolve_bet(
    hand1: PokerHand, hand2: PokerHand, bet1_amount: float, bet2_amount: float
) -> Tuple[float, float]:
    """
    Resolve a poker bet between two hands with proper kicker comparison.

    Returns deltas (profit/loss) for each player. For actual pot distribution,
    use finalize_pot() instead.
    """
    # Determine winner using proper hand comparison including kickers
    if hand1.beats(hand2):
        # Player 1 wins, takes both bets
        return (bet2_amount, -bet2_amount)
    elif hand2.beats(hand1):
        # Player 2 wins, takes both bets
        return (-bet1_amount, bet1_amount)
    else:
        # Tie (same rank and kickers) - no money changes hands
        return (0.0, 0.0)


def finalize_pot(game_state: PokerGameState) -> Tuple[float, float]:
    """
    Determines the final payout from the pot to Player 1 and Player 2.

    This method examines the game state (folds, hand rankings) and returns
    the actual pot distribution. For ties, the pot is split equally.

    Args:
        game_state: The completed poker game state

    Returns:
        Tuple[float, float]: (Amount to Player 1, Amount to Player 2)
    """
    # 1. Check if someone folded (Pot goes to the survivor)
    winner_by_fold = game_state.get_winner_by_fold()
    if winner_by_fold == 1:
        return (game_state.pot, 0.0)
    elif winner_by_fold == 2:
        return (0.0, game_state.pot)

    # 2. If no fold, ensure hands are evaluated
    if not game_state.player1_hand:
        game_state.player1_hand = evaluate_hand(
            game_state.player1_hole_cards, game_state.community_cards
        )
    if not game_state.player2_hand:
        game_state.player2_hand = evaluate_hand(
            game_state.player2_hole_cards, game_state.community_cards
        )

    # 3. Compare Hands
    if game_state.player1_hand.beats(game_state.player2_hand):
        # Player 1 wins entire pot
        return (game_state.pot, 0.0)
    elif game_state.player2_hand.beats(game_state.player1_hand):
        # Player 2 wins entire pot
        return (0.0, game_state.pot)
    else:
        # TIE (Split Pot): Divide pot equally
        half_pot = game_state.pot / 2
        return (half_pot, half_pot)


def simulate_game(
    bet_amount: float = 10.0, player1_energy: float = 100.0, player2_energy: float = 100.0
) -> PokerGameState:
    """
    Simulate a complete Texas Hold'em poker game between two players.
    """
    return simulate_multi_round_game(
        initial_bet=bet_amount, player1_energy=player1_energy, player2_energy=player2_energy
    )
