"""CFR (Counterfactual Regret Minimization) learning for poker.

This module handles post-game learning updates for fish with
ComposablePokerStrategy. It implements Lamarckian learning where
fish improve their poker skills during their lifetime.

Design Decision:
----------------
CFR learning is separated from the core interaction logic because:
1. It's optional (only applies to fish with composable strategies)
2. It's complex enough to warrant its own module
3. It can be tested independently
4. It may evolve separately from the core poker rules
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from core.poker.betting.actions import BettingAction
from core.poker.core import evaluate_hand
from core.poker.evaluation.strength import (evaluate_hand_strength,
                                            evaluate_starting_hand_strength)

if TYPE_CHECKING:
    from core.mixed_poker.state import (MultiplayerGameState,
                                        MultiplayerPlayerContext)

logger = logging.getLogger(__name__)


def update_cfr_learning(
    game_state: "MultiplayerGameState",
    contexts: "List[MultiplayerPlayerContext]",
    winner_idx: int,
    tied_players: List[int],
    players: List[Any],
    get_player_energy: Callable[[Any], float],
    initial_player_energies: List[float],
) -> None:
    """Update CFR learning for fish with composable strategies.

    After each hand, we update the regret tables so fish can learn from experience.
    This implements Lamarckian learning - fish improve during their lifetime.

    Args:
        game_state: The completed game state
        contexts: Player contexts with strategy info
        winner_idx: Index of winning player
        tied_players: Indices of tied players (if tie)
        players: List of player objects
        get_player_energy: Function to get current energy of a player
        initial_player_energies: List of initial energies at game start
    """
    try:
        from core.poker.strategy.composable import ComposablePokerStrategy
    except ImportError:
        return  # CFR not available

    for i, ctx in enumerate(contexts):
        if ctx.strategy is None:
            continue
        if not isinstance(ctx.strategy, ComposablePokerStrategy):
            continue

        # Compute this player's actual outcome (net profit/loss)
        initial_energy = initial_player_energies[i]
        final_energy = get_player_energy(players[i])
        actual_profit = final_energy - initial_energy

        # Compute info set from the hand
        hole_cards = game_state.player_hole_cards[i]
        if not hole_cards or len(hole_cards) < 2:
            continue

        # Compute hand strength at showdown
        if game_state.community_cards:
            try:
                hand = evaluate_hand(hole_cards, game_state.community_cards)
                hand_strength = evaluate_hand_strength(hand)
            except Exception:
                logger.debug("Hand strength evaluation failed, defaulting to 0.5", exc_info=True)
                hand_strength = 0.5
        else:
            # Pre-flop fold - use starting hand strength
            position_on_button = i == game_state.button_position
            hand_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)

        # Pot ratio relative to initial energy
        pot_ratio = game_state.pot / max(1.0, initial_energy)
        position_on_button = i == game_state.button_position

        # Get info set
        info_set = ctx.strategy.get_info_set(hand_strength, pot_ratio, position_on_button, street=0)

        # Determine what action we effectively took
        action_taken = _infer_action_taken(i, game_state)

        # Compute counterfactual values for each action
        action_values = _estimate_counterfactual_values(
            i, game_state, contexts, winner_idx, actual_profit
        )

        # Update regret
        ctx.strategy.update_regret(info_set, action_taken, action_values)


def _infer_action_taken(player_idx: int, game_state: "MultiplayerGameState") -> str:
    """Infer the primary action taken by a player from betting history.

    Simplifies to one of: fold, call, raise_small, raise_big
    """
    # Look for this player's actions in history
    player_actions = [
        (action, amount)
        for (idx, action, amount) in game_state.betting_history
        if idx == player_idx
    ]

    if not player_actions:
        return "call"  # Default

    # Find the most aggressive action
    for action, amount in reversed(player_actions):
        if action == BettingAction.FOLD:
            return "fold"
        elif action == BettingAction.RAISE:
            # Determine if small or big raise based on pot
            if amount > game_state.pot * 0.6:
                return "raise_big"
            else:
                return "raise_small"
        elif action == BettingAction.CALL:
            continue  # Keep looking for raises

    return "call"


def _estimate_counterfactual_values(
    player_idx: int,
    game_state: "MultiplayerGameState",
    contexts: "List[MultiplayerPlayerContext]",
    winner_idx: int,
    actual_profit: float,
) -> Dict[str, float]:
    """Estimate what we would have won/lost with each action.

    This is a simplified estimate - true CFR would require re-playing the hand.
    We use heuristics based on the actual outcome.

    Returns:
        Dict mapping action -> estimated counterfactual value
    """
    my_bet = game_state.player_total_bets[player_idx]
    i_won = player_idx == winner_idx
    i_folded = contexts[player_idx].folded

    # Base values - what we could have won/lost
    if i_folded:
        # We folded - regret not calling/raising if we would have won
        fold_value = -my_bet  # Lost our bet
        # Estimate call/raise values based on hand strength
        call_value = fold_value * 0.8  # Slightly better than fold on average
        raise_small_value = fold_value * 0.6
        raise_big_value = fold_value * 0.4
    elif i_won:
        # We won - any action that kept us in was good
        fold_value = -my_bet  # Would have lost our bet
        call_value = actual_profit
        raise_small_value = actual_profit * 1.1  # Raising might have won more
        raise_big_value = actual_profit * 1.2  # Big raise might have won even more
    else:
        # We lost - folding would have saved money
        fold_value = -my_bet * 0.3  # Would have lost less (early fold)
        call_value = actual_profit  # What we actually got
        raise_small_value = actual_profit * 0.9  # Raising lost more
        raise_big_value = actual_profit * 0.8  # Big raise lost even more

    return {
        "fold": fold_value,
        "call": call_value,
        "raise_small": raise_small_value,
        "raise_big": raise_big_value,
    }
