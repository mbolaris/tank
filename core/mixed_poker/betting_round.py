"""Betting round logic for poker games.

This module handles the mechanics of a single betting round including:
- Player action selection
- Bet/call/raise/fold processing  
- Round completion detection

Design Decision:
----------------
Betting logic is separated from the main interaction class because:
1. It's the most complex part of the poker flow
2. It can be tested with mock game states
3. It's reusable for different poker variants
"""

import logging
import random
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from core.config.poker import POKER_MAX_ACTIONS_PER_ROUND
from core.poker.betting.actions import BettingAction
from core.poker.core import evaluate_hand
from core.poker.evaluation.strength import (
    evaluate_hand_strength,
    evaluate_starting_hand_strength,
)

if TYPE_CHECKING:
    from core.mixed_poker.state import MultiplayerGameState, MultiplayerPlayerContext

logger = logging.getLogger(__name__)


def decide_player_action(
    player_idx: int,
    game_state: "MultiplayerGameState",
    contexts: "List[MultiplayerPlayerContext]",
    players: List[Any],
    rng: Optional[Any] = None,
) -> Tuple[BettingAction, float]:
    """Decide action for a player based on hand strength and aggression.

    Args:
        player_idx: Index of the player making the decision
        game_state: Current game state
        contexts: List of player contexts
        players: List of player objects (for RNG access)
        rng: Optional RNG for deterministic behavior

    Returns:
        Tuple of (action, bet_amount)
    """
    ctx = contexts[player_idx]

    # Can't act if folded or all-in
    if ctx.folded or ctx.is_all_in:
        return BettingAction.CHECK, 0.0

    # Evaluate current hand strength
    hole_cards = game_state.player_hole_cards[player_idx]
    is_preflop = len(game_state.community_cards) == 0
    position_on_button = (player_idx == game_state.button_position)

    if is_preflop and hole_cards and len(hole_cards) == 2:
        # Pre-flop: use proper starting hand evaluation
        hand_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)
    elif game_state.community_cards:
        hand = evaluate_hand(hole_cards, game_state.community_cards)
        # Normalize hand rank (0-1 scale) using correct constant
        hand_strength = evaluate_hand_strength(hand)
    else:
        hand_strength = 0.5

    # Calculate amount needed to call
    max_bet = game_state.get_max_current_bet()
    call_amount = max_bet - ctx.current_bet

    # Use evolved poker strategy if available
    if ctx.strategy is not None:
        return ctx.strategy.decide_action(
            hand_strength=hand_strength,
            current_bet=ctx.current_bet,
            opponent_bet=max_bet,
            pot=game_state.pot,
            player_energy=ctx.remaining_energy,
            position_on_button=position_on_button,
        )

    # Fallback: Simple aggression-based decision
    # Use provided RNG, or fallback to player environment, or local RNG
    player = players[player_idx]
    _rng = rng
    if _rng is None:
        _rng = getattr(getattr(player, "environment", None), "rng", None) or random.Random()
        
    aggression = ctx.aggression
    play_strength = hand_strength + (aggression - 0.5) * 0.2 + _rng.uniform(-0.1, 0.1)

    if call_amount <= 0:
        # No bet to call - can check or raise
        if play_strength > 0.6 and ctx.remaining_energy > game_state.big_blind * 2:
            # Strong hand or aggressive - raise
            raise_amount = game_state.big_blind * (1 + play_strength * 2)
            raise_amount = min(raise_amount, ctx.remaining_energy)
            return BettingAction.RAISE, raise_amount
        else:
            return BettingAction.CHECK, 0.0
    else:
        # Must call, raise, or fold
        pot_odds = call_amount / (game_state.pot + call_amount) if game_state.pot > 0 else 0.5

        if play_strength > pot_odds + 0.2:
            # Strong hand - might raise
            if play_strength > 0.7 and ctx.remaining_energy > call_amount + game_state.big_blind:
                raise_amount = call_amount + game_state.big_blind * (1 + play_strength)
                raise_amount = min(raise_amount, ctx.remaining_energy)
                return BettingAction.RAISE, raise_amount
            else:
                return BettingAction.CALL, call_amount
        elif play_strength > pot_odds - 0.1:
            # Marginal hand - call
            if call_amount <= ctx.remaining_energy:
                return BettingAction.CALL, call_amount
            else:
                return BettingAction.FOLD, 0.0
        else:
            # Weak hand - fold
            return BettingAction.FOLD, 0.0


def play_betting_round(
    game_state: "MultiplayerGameState",
    contexts: "List[MultiplayerPlayerContext]",
    start_position: int,
    num_players: int,
    players: List[Any],
    modify_player_energy: callable,
    rng: Optional[Any] = None,
) -> bool:
    """Play a single betting round.

    Args:
        game_state: Current game state
        contexts: Player contexts
        start_position: Position to start betting from
        num_players: Total number of players
        players: List of player objects
        modify_player_energy: Function to modify a player's energy
        rng: Optional RNG for deterministic behavior

    Returns:
        True if round completed normally, False if only one player remains
    """
    actions_this_round = 0
    current_pos = start_position
    players_acted = set()

    max_actions = POKER_MAX_ACTIONS_PER_ROUND * num_players

    while actions_this_round < max_actions:
        # Safety check: if all active players are all-in, we're done
        active_can_act = [
            i for i in range(num_players)
            if not contexts[i].folded and not contexts[i].is_all_in
        ]
        if not active_can_act:
            return game_state.get_active_player_count() > 1

        # Skip folded or all-in players
        if contexts[current_pos].folded or contexts[current_pos].is_all_in:
            current_pos = (current_pos + 1) % num_players
            continue

        # Check if only one player remains
        if game_state.get_active_player_count() <= 1:
            return False

        # Get player action
        action, amount = decide_player_action(current_pos, game_state, contexts, players, rng=rng)

        # Apply action
        if action == BettingAction.FOLD:
            contexts[current_pos].folded = True
            game_state.player_folded[current_pos] = True
            game_state.betting_history.append((current_pos, action, 0.0))

        elif action == BettingAction.CHECK:
            game_state.betting_history.append((current_pos, action, 0.0))
            players_acted.add(current_pos)

        elif action == BettingAction.CALL:
            call_amount = min(amount, contexts[current_pos].remaining_energy)
            game_state.player_bet(current_pos, call_amount)
            contexts[current_pos].remaining_energy -= call_amount
            contexts[current_pos].current_bet += call_amount
            # Deduct energy from the player
            modify_player_energy(players[current_pos], -call_amount)
            game_state.betting_history.append((current_pos, action, call_amount))
            players_acted.add(current_pos)

            if contexts[current_pos].remaining_energy <= 0:
                contexts[current_pos].is_all_in = True
                game_state.player_all_in[current_pos] = True

        elif action == BettingAction.RAISE:
            # First call, then raise
            max_bet = game_state.get_max_current_bet()
            call_amount = max_bet - contexts[current_pos].current_bet

            total_amount = min(amount, contexts[current_pos].remaining_energy)
            raise_portion = total_amount - call_amount

            if raise_portion > 0:
                game_state.player_bet(current_pos, total_amount)
                contexts[current_pos].remaining_energy -= total_amount
                contexts[current_pos].current_bet += total_amount
                # Deduct energy from the player
                modify_player_energy(players[current_pos], -total_amount)
                game_state.betting_history.append((current_pos, action, raise_portion))
                players_acted = {current_pos}  # Reset - others need to act again

                if contexts[current_pos].remaining_energy <= 0:
                    contexts[current_pos].is_all_in = True
                    game_state.player_all_in[current_pos] = True
            else:
                # Can't raise, just call
                game_state.player_bet(current_pos, call_amount)
                contexts[current_pos].remaining_energy -= call_amount
                contexts[current_pos].current_bet += call_amount
                modify_player_energy(players[current_pos], -call_amount)
                game_state.betting_history.append((current_pos, BettingAction.CALL, call_amount))
                players_acted.add(current_pos)

        actions_this_round += 1

        # Check if betting round is complete
        active_players = [
            i for i in range(num_players)
            if not contexts[i].folded and not contexts[i].is_all_in
        ]

        if not active_players:
            return game_state.get_active_player_count() > 1

        # All active players have acted and bets are equal
        max_bet = game_state.get_max_current_bet()
        all_matched = all(
            contexts[i].current_bet == max_bet or contexts[i].is_all_in
            for i in active_players
        )
        all_acted = all(i in players_acted for i in active_players)

        if all_matched and all_acted:
            return game_state.get_active_player_count() > 1

        current_pos = (current_pos + 1) % num_players

    return game_state.get_active_player_count() > 1
