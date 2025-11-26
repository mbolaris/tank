"""
Poker game simulation for Texas Hold'em.

This module provides game simulation, pot resolution, and bet finalization logic.
"""

import logging
from typing import TYPE_CHECKING, Optional, Tuple

from core.constants import POKER_MAX_ACTIONS_PER_ROUND, POKER_MAX_HAND_RANK
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import AGGRESSION_MEDIUM, decide_action
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import PokerHand
from core.poker.evaluation.hand_evaluator import evaluate_hand

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


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
    """
    Simulate a complete multi-round Texas Hold'em poker game with blinds.
    """
    if player1_aggression is None:
        player1_aggression = AGGRESSION_MEDIUM
    if player2_aggression is None:
        player2_aggression = AGGRESSION_MEDIUM

    # Calculate blinds from initial bet
    big_blind = initial_bet
    small_blind = initial_bet / 2

    # Ensure blinds don't exceed available energy
    big_blind = min(big_blind, player1_energy, player2_energy)
    small_blind = min(small_blind, player1_energy, player2_energy, big_blind / 2)

    game_state = PokerGameState(
        small_blind=small_blind, big_blind=big_blind, button_position=button_position
    )

    # Deal hole cards
    game_state.deal_cards()

    # Post blinds
    # In heads-up, button posts small blind, other player posts big blind
    if button_position == 1:
        small_blind_player = 1
        big_blind_player = 2
    else:
        small_blind_player = 2
        big_blind_player = 1

    game_state.player_bet(small_blind_player, small_blind)
    game_state.player_bet(big_blind_player, big_blind)

    if small_blind_player == 1:
        player1_remaining = player1_energy - small_blind
        player2_remaining = player2_energy - big_blind
    else:
        player1_remaining = player1_energy - big_blind
        player2_remaining = player2_energy - small_blind

    # Play through betting rounds
    for round_num in range(4):  # Pre-flop, Flop, Turn, River
        if game_state.get_winner_by_fold() is not None:
            break

        # Advance round and deal community cards
        if round_num > 0:
            game_state.advance_round()

        # Simulate betting for this round
        # Players alternate actions until both have matched bets or someone folds
        max_actions_per_round = POKER_MAX_ACTIONS_PER_ROUND  # Prevent infinite loops
        actions_this_round = 0

        # In heads-up pre-flop, button (small blind) acts first
        # Post-flop, button acts last (so non-button acts first)
        if round_num == 0:  # Pre-flop
            current_player = button_position
        else:  # Post-flop
            current_player = 2 if button_position == 1 else 1

        while actions_this_round < max_actions_per_round:
            # Evaluate current hand strength based on available cards
            if current_player == 1:
                hand = evaluate_hand(
                    game_state.player1_hole_cards, game_state.community_cards
                )
                current_bet = game_state.player1_current_bet
                opponent_bet = game_state.player2_current_bet
                remaining_energy = player1_remaining
                aggression = player1_aggression
            else:
                hand = evaluate_hand(
                    game_state.player2_hole_cards, game_state.community_cards
                )
                current_bet = game_state.player2_current_bet
                opponent_bet = game_state.player1_current_bet
                remaining_energy = player2_remaining
                aggression = player2_aggression

            # Decide action
            # Determine if player is on button
            player_on_button = current_player == button_position

            # Get hole cards and community cards for enhanced decision making
            hole_cards = (
                game_state.player1_hole_cards
                if current_player == 1
                else game_state.player2_hole_cards
            )

            # Use poker strategy algorithm if available, otherwise fall back to aggression-based
            player_strategy = player1_strategy if current_player == 1 else player2_strategy

            if player_strategy is not None:
                # Use evolving poker strategy algorithm
                # Normalize hand strength from HandRank (0-9) to 0.0-1.0
                hand_strength = hand.rank_value / POKER_MAX_HAND_RANK

                action, bet_amount = player_strategy.decide_action(
                    hand_strength=hand_strength,
                    current_bet=current_bet,
                    opponent_bet=opponent_bet,
                    pot=game_state.pot,
                    player_energy=remaining_energy,
                    position_on_button=player_on_button,
                )
            else:
                # Fall back to old aggression-based decision making
                action, bet_amount = decide_action(
                    hand=hand,
                    current_bet=current_bet,
                    opponent_bet=opponent_bet,
                    pot=game_state.pot,
                    player_energy=remaining_energy,
                    aggression=aggression,
                    hole_cards=hole_cards,
                    community_cards=game_state.community_cards,
                    position_on_button=player_on_button,
                )

            # Process action
            if action == BettingAction.FOLD:
                game_state.betting_history.append((current_player, action, 0.0))
                if current_player == 1:
                    game_state.player1_folded = True
                else:
                    game_state.player2_folded = True
                break

            elif action == BettingAction.CHECK:
                # Check - no bet
                game_state.betting_history.append((current_player, action, 0.0))

            elif action == BettingAction.CALL:
                # Call - match opponent's bet
                game_state.betting_history.append((current_player, action, bet_amount))
                game_state.player_bet(current_player, bet_amount)
                if current_player == 1:
                    player1_remaining -= bet_amount
                else:
                    player2_remaining -= bet_amount

            elif action == BettingAction.RAISE:
                # Raise - increase bet
                # First call to match, then add raise amount
                call_amount = opponent_bet - current_bet

                # Enforce minimum raise rule (Texas Hold'em)
                # The raise amount must be at least the size of the last raise
                actual_raise = max(bet_amount, game_state.min_raise)

                # Cap raise at remaining energy after call
                max_raise = remaining_energy - call_amount
                if max_raise < game_state.min_raise:
                    # Can't afford minimum raise - treat as all-in
                    actual_raise = max(0, max_raise)
                else:
                    actual_raise = min(actual_raise, max_raise)

                total_bet = call_amount + actual_raise
                game_state.player_bet(current_player, total_bet)

                # Record the actual raise amount (after enforcement)
                game_state.betting_history.append((current_player, action, actual_raise))

                # Update minimum raise for next raise (min raise = this raise amount)
                if actual_raise > 0:
                    game_state.last_raise_amount = actual_raise
                    game_state.min_raise = actual_raise

                if current_player == 1:
                    player1_remaining -= total_bet
                else:
                    player2_remaining -= total_bet

            actions_this_round += 1

            # Check if betting is complete for this round
            # Complete if both players have equal bets and at least one has acted
            if (
                game_state.player1_current_bet == game_state.player2_current_bet
                and actions_this_round >= 2
            ):
                break

            # Switch to other player
            current_player = 2 if current_player == 1 else 1

        # UNMATCHED BETS FIX (Side Pot Logic for Heads-Up)
        # If one player is all-in for less than the other's current bet,
        # return the excess to the richer player. This ensures Table Stakes rules.
        if game_state.player1_current_bet != game_state.player2_current_bet:
            min_bet = min(game_state.player1_current_bet, game_state.player2_current_bet)

            # Refund the difference to the player with the larger bet
            if game_state.player1_current_bet > min_bet:
                refund = game_state.player1_current_bet - min_bet
                game_state.player1_current_bet = min_bet
                game_state.player1_total_bet -= refund
                game_state.pot -= refund
                player1_remaining += refund  # Give money back to stack

            elif game_state.player2_current_bet > min_bet:
                refund = game_state.player2_current_bet - min_bet
                game_state.player2_current_bet = min_bet
                game_state.player2_total_bet -= refund
                game_state.pot -= refund
                player2_remaining += refund  # Give money back to stack

    # Game is over - evaluate final hands at showdown
    game_state.current_round = BettingRound.SHOWDOWN

    # Evaluate best hands using all 7 cards (2 hole + 5 community)
    if not game_state.player1_folded:
        game_state.player1_hand = evaluate_hand(
            game_state.player1_hole_cards, game_state.community_cards
        )
    if not game_state.player2_folded:
        game_state.player2_hand = evaluate_hand(
            game_state.player2_hole_cards, game_state.community_cards
        )

    return game_state


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
