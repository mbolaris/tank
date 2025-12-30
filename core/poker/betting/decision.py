"""
Betting decision logic for Texas Hold'em poker.

This module provides decision-making logic for poker AI, including
hand strength-based action selection and betting amounts.
"""

import random
from typing import List, Optional, Tuple

from core.config.poker import (
    POKER_AGGRESSION_HIGH,
    POKER_AGGRESSION_LOW,
    POKER_AGGRESSION_MEDIUM,
    POKER_MEDIUM_AGGRESSION_MULTIPLIER,
    POKER_MEDIUM_CALL_MULTIPLIER,
    POKER_MEDIUM_ENERGY_FRACTION,
    POKER_MEDIUM_ENERGY_FRACTION_RERAISE,
    POKER_MEDIUM_POT_MULTIPLIER,
    POKER_MEDIUM_POT_ODDS_FOLD_THRESHOLD,
    POKER_MEDIUM_RAISE_PROBABILITY,
    POKER_PREFLOP_MAX_ENERGY_FRACTION,
    POKER_PREFLOP_MIN_RAISE_MULTIPLIER,
    POKER_PREFLOP_STRENGTH_THRESHOLD,
    POKER_STRONG_CALL_MULTIPLIER,
    POKER_STRONG_ENERGY_FRACTION,
    POKER_STRONG_ENERGY_FRACTION_RERAISE,
    POKER_STRONG_POT_MULTIPLIER,
    POKER_STRONG_RAISE_PROBABILITY,
    POKER_WEAK_BLUFF_PROBABILITY,
    POKER_WEAK_CALL_PROBABILITY,
    POKER_WEAK_ENERGY_FRACTION,
    POKER_WEAK_POT_MULTIPLIER,
)
from core.poker.betting.actions import BettingAction
from core.poker.core.cards import Card
from core.poker.core.hand import HandRank, PokerHand
from core.poker.evaluation.strength import (
    calculate_pot_odds,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)

# Default aggression constants
AGGRESSION_LOW = POKER_AGGRESSION_LOW
AGGRESSION_MEDIUM = POKER_AGGRESSION_MEDIUM
AGGRESSION_HIGH = POKER_AGGRESSION_HIGH


def _decide_strong_hand_action(
    call_amount: float, pot: float, player_energy: float, aggression: float, rng: random.Random
) -> Tuple[BettingAction, float]:
    """Decide action for strong hands (flush or better)."""
    if call_amount == 0:
        # No bet to call - raise most of the time
        if rng.random() < POKER_STRONG_RAISE_PROBABILITY:
            raise_amount = min(
                pot * POKER_STRONG_POT_MULTIPLIER, player_energy * POKER_STRONG_ENERGY_FRACTION
            )
            return (BettingAction.RAISE, raise_amount)
        else:
            return (BettingAction.CHECK, 0.0)
    else:
        # There's a bet - call or raise
        if rng.random() < aggression:
            # Raise
            raise_amount = min(
                call_amount * POKER_STRONG_CALL_MULTIPLIER,
                player_energy * POKER_STRONG_ENERGY_FRACTION_RERAISE,
            )
            return (BettingAction.RAISE, raise_amount)
        else:
            # Call
            return (BettingAction.CALL, call_amount)


def _decide_medium_hand_action(
    call_amount: float, pot: float, player_energy: float, aggression: float, rng: random.Random
) -> Tuple[BettingAction, float]:
    """Decide action for medium hands (pair through straight)."""
    if call_amount == 0:
        # No bet - check or small raise
        if rng.random() < aggression * POKER_MEDIUM_AGGRESSION_MULTIPLIER:
            raise_amount = min(
                pot * POKER_MEDIUM_POT_MULTIPLIER, player_energy * POKER_MEDIUM_ENERGY_FRACTION
            )
            return (BettingAction.RAISE, raise_amount)
        else:
            return (BettingAction.CHECK, 0.0)
    else:
        # There's a bet - fold, call, or raise based on bet size and aggression
        pot_odds = call_amount / (pot + call_amount) if pot > 0 else 1.0

        # More likely to fold if bet is large relative to pot
        if pot_odds > POKER_MEDIUM_POT_ODDS_FOLD_THRESHOLD and rng.random() > aggression:
            return (BettingAction.FOLD, 0.0)
        elif rng.random() < aggression * POKER_MEDIUM_RAISE_PROBABILITY:
            # Sometimes raise with medium hands
            raise_amount = min(
                call_amount * POKER_MEDIUM_CALL_MULTIPLIER,
                player_energy * POKER_MEDIUM_ENERGY_FRACTION_RERAISE,
            )
            return (BettingAction.RAISE, raise_amount)
        else:
            # Usually call
            return (BettingAction.CALL, call_amount)


def _decide_weak_hand_action(
    call_amount: float, pot: float, player_energy: float, aggression: float, rng: random.Random
) -> Tuple[BettingAction, float]:
    """Decide action for weak hands (high card)."""
    if call_amount == 0:
        # No bet - usually check, rarely bluff
        if rng.random() < aggression * POKER_WEAK_BLUFF_PROBABILITY:
            # Bluff
            raise_amount = min(
                pot * POKER_WEAK_POT_MULTIPLIER, player_energy * POKER_WEAK_ENERGY_FRACTION
            )
            return (BettingAction.RAISE, raise_amount)
        else:
            return (BettingAction.CHECK, 0.0)
    else:
        # There's a bet - usually fold, rarely bluff call
        if rng.random() < aggression * POKER_WEAK_CALL_PROBABILITY:
            # Bluff call
            return (BettingAction.CALL, call_amount)
        else:
            return (BettingAction.FOLD, 0.0)


def decide_action(
    hand: PokerHand,
    current_bet: float,
    opponent_bet: float,
    pot: float,
    player_energy: float,
    aggression: Optional[float] = None,
    hole_cards: Optional[List[Card]] = None,
    community_cards: Optional[List[Card]] = None,
    position_on_button: bool = False,
    rng: random.Random = None,  # type: ignore[assignment]  # Required at runtime
) -> Tuple[BettingAction, float]:
    """
    Decide what action to take based on hand strength and game state.

    Enhanced with realistic pre-flop hand evaluation and position awareness.

    Args:
        rng: Required seeded Random instance for deterministic behavior.
             Callers must provide this to ensure reproducible simulations.
    """
    if rng is None:
        raise ValueError("rng parameter is required for deterministic behavior")

    if aggression is None:
        aggression = AGGRESSION_MEDIUM

    _rng = rng

    # Calculate how much needs to be called
    call_amount = opponent_bet - current_bet

    # TABLE STAKES RULE: If player cannot cover the full call, they go All-In
    # Players are never forced to fold due to lack of funds - they call with what they have
    if call_amount > player_energy:
        # All-in: call with remaining energy
        return (BettingAction.CALL, player_energy)

    # Enhanced pre-flop decision making with starting hand evaluation
    is_preflop = community_cards is None or len(community_cards) == 0
    if is_preflop and hole_cards is not None and len(hole_cards) == 2:
        # Evaluate starting hand strength
        starting_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)

        # Calculate pot odds
        pot_odds = calculate_pot_odds(call_amount, pot) if call_amount > 0 else 0.0

        # Get recommended action based on situation
        action_type, bet_multiplier = get_action_recommendation(
            hand_strength=starting_strength,
            pot_odds=pot_odds,
            aggression=aggression,
            position_on_button=position_on_button,
            is_preflop=True,
        )

        # Convert recommendation to actual action
        if action_type == "fold":
            return (BettingAction.FOLD, 0.0)
        elif action_type == "check":
            if call_amount == 0:
                return (BettingAction.CHECK, 0.0)
            else:
                # Can't check with a bet to call
                if starting_strength > pot_odds * POKER_PREFLOP_STRENGTH_THRESHOLD:
                    return (BettingAction.CALL, call_amount)
                else:
                    return (BettingAction.FOLD, 0.0)
        elif action_type == "call":
            if call_amount == 0:
                return (BettingAction.CHECK, 0.0)
            else:
                return (BettingAction.CALL, call_amount)
        else:  # raise
            raise_amount = min(
                pot * bet_multiplier, player_energy * POKER_PREFLOP_MAX_ENERGY_FRACTION
            )
            if call_amount > 0:
                raise_amount = max(raise_amount, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER)
            return (BettingAction.RAISE, raise_amount)

    # Determine hand strength category and delegate to appropriate helper
    hand_strength = hand.rank_value

    # Strong hands (flush or better)
    if hand_strength >= HandRank.FLUSH:
        return _decide_strong_hand_action(call_amount, pot, player_energy, aggression, _rng)
    # Medium hands (pair through straight)
    elif hand_strength >= HandRank.PAIR:
        return _decide_medium_hand_action(call_amount, pot, player_energy, aggression, _rng)
    # Weak hands (high card)
    else:
        return _decide_weak_hand_action(call_amount, pot, player_energy, aggression, _rng)
