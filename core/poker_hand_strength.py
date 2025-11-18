"""
Poker hand strength evaluation for pre-flop and position-based decisions.

This module provides realistic poker AI enhancements including starting hand evaluation,
position-aware play, and improved decision making based on actual poker theory.
"""

from typing import List, Tuple
from core.poker_interaction import Card, Rank


def evaluate_starting_hand_strength(hole_cards: List[Card], position_on_button: bool) -> float:
    """Evaluate pre-flop starting hand strength (0.0 to 1.0).

    This implements a simplified version of actual poker hand rankings for Texas Hold'em,
    adjusted for position. Hands play better on the button than off the button.

    Args:
        hole_cards: The two hole cards
        position_on_button: True if player is on the button (better position)

    Returns:
        Hand strength from 0.0 (terrible) to 1.0 (premium)
    """
    if len(hole_cards) != 2:
        return 0.2  # Default weak strength if invalid

    card1, card2 = hole_cards[0], hole_cards[1]
    rank1 = card1.rank
    rank2 = card2.rank

    # Ensure rank1 is higher
    if rank2 > rank1:
        rank1, rank2 = rank2, rank1

    is_suited = card1.suit == card2.suit
    is_pair = rank1 == rank2
    gap = rank1 - rank2

    # Base strength calculation
    strength = 0.0

    # Pocket pairs
    if is_pair:
        # AA = 1.0, KK = 0.95, QQ = 0.90, etc.
        if rank1 == Rank.ACE:
            strength = 1.0
        elif rank1 == Rank.KING:
            strength = 0.95
        elif rank1 == Rank.QUEEN:
            strength = 0.90
        elif rank1 == Rank.JACK:
            strength = 0.82
        elif rank1 == Rank.TEN:
            strength = 0.75
        elif rank1 == Rank.NINE:
            strength = 0.68
        else:
            # Lower pairs: decreasing value
            strength = 0.45 + (rank1 - 2) * 0.03

    # High cards (broadway cards: A, K, Q, J, T)
    elif rank1 >= Rank.TEN:
        if rank1 == Rank.ACE and rank2 == Rank.KING:
            strength = 0.92 if is_suited else 0.88
        elif rank1 == Rank.ACE and rank2 == Rank.QUEEN:
            strength = 0.85 if is_suited else 0.78
        elif rank1 == Rank.ACE and rank2 == Rank.JACK:
            strength = 0.80 if is_suited else 0.72
        elif rank1 == Rank.ACE and rank2 == Rank.TEN:
            strength = 0.78 if is_suited else 0.70
        elif rank1 == Rank.KING and rank2 == Rank.QUEEN:
            strength = 0.77 if is_suited else 0.68
        elif rank1 == Rank.KING and rank2 == Rank.JACK:
            strength = 0.73 if is_suited else 0.64
        elif rank1 == Rank.QUEEN and rank2 == Rank.JACK:
            strength = 0.70 if is_suited else 0.60
        elif rank1 == Rank.JACK and rank2 == Rank.TEN:
            strength = 0.68 if is_suited else 0.58
        else:
            # Other broadway combinations
            strength = 0.55 if is_suited else 0.48

    # Suited connectors and gappers
    elif is_suited and gap <= 2:
        # Suited connectors/gappers have good playability
        if gap == 0:  # Connectors
            strength = 0.50 + (rank1 - 6) * 0.02
        else:  # One or two gap
            strength = 0.42 + (rank1 - 6) * 0.02 - (gap * 0.05)

    # Medium pairs and high cards
    elif rank1 >= Rank.EIGHT:
        if is_suited:
            strength = 0.45 + ((rank1 + rank2) - 10) * 0.02
        else:
            strength = 0.35 + ((rank1 + rank2) - 10) * 0.015

    # Weak hands
    else:
        if is_suited:
            strength = 0.25 + ((rank1 + rank2) - 4) * 0.01
        else:
            strength = 0.15 + ((rank1 + rank2) - 4) * 0.008

    # Position adjustment: button position adds value
    if position_on_button:
        # Hands play better in position
        position_bonus = 0.10 * strength  # 10% bonus for being on button
        strength = min(1.0, strength + position_bonus)
    else:
        # Out of position penalty for marginal hands
        if 0.3 < strength < 0.7:
            position_penalty = 0.08 * strength
            strength = max(0.0, strength - position_penalty)

    return min(1.0, max(0.0, strength))


def calculate_pot_odds(call_amount: float, pot_size: float) -> float:
    """Calculate pot odds (required equity to call).

    Args:
        call_amount: Amount needed to call
        pot_size: Current pot size

    Returns:
        Required equity as a fraction (0.0 to 1.0)
    """
    if call_amount <= 0:
        return 0.0

    total_pot = pot_size + call_amount
    if total_pot <= 0:
        return 1.0

    return call_amount / total_pot


def get_action_recommendation(
    hand_strength: float,
    pot_odds: float,
    aggression: float,
    position_on_button: bool,
    is_preflop: bool,
) -> Tuple[str, float]:
    """Get recommended action based on hand strength and situation.

    Args:
        hand_strength: Hand strength (0.0 to 1.0)
        pot_odds: Required pot odds to call (0.0 to 1.0)
        aggression: Player aggression factor (0.0 to 1.0)
        position_on_button: True if on the button
        is_preflop: True if pre-flop betting round

    Returns:
        Tuple of (action_type, bet_multiplier) where:
            action_type: 'fold', 'check', 'call', or 'raise'
            bet_multiplier: multiplier for bet sizing (0.3 to 2.0)
    """
    # Premium hands (>0.75): Almost always raise/call
    if hand_strength >= 0.75:
        if is_preflop or position_on_button:
            return ('raise', 1.0 + aggression * 0.5)
        else:
            return ('call', 0.0)

    # Strong hands (0.60-0.75): Raise or call depending on aggression
    elif hand_strength >= 0.60:
        if aggression > 0.5 or position_on_button:
            return ('raise', 0.7 + aggression * 0.4)
        else:
            return ('call', 0.0)

    # Medium hands (0.40-0.60): Play based on pot odds and position
    elif hand_strength >= 0.40:
        if hand_strength > pot_odds:
            # Hand is strong enough for pot odds
            if position_on_button and aggression > 0.6:
                return ('raise', 0.5 + aggression * 0.3)
            else:
                return ('call', 0.0)
        else:
            # Not getting right pot odds
            if position_on_button and aggression > 0.7:
                return ('raise', 0.4 + aggression * 0.2)  # Bluff
            else:
                return ('fold', 0.0)

    # Marginal hands (0.25-0.40): Mostly fold, sometimes play in position
    elif hand_strength >= 0.25:
        if position_on_button and aggression > 0.7 and pot_odds < 0.25:
            return ('call', 0.0)  # Speculative call in position
        elif aggression > 0.8:
            return ('raise', 0.3 + aggression * 0.2)  # Aggressive bluff
        else:
            return ('fold', 0.0)

    # Weak hands (<0.25): Usually fold, very rarely bluff
    else:
        if aggression > 0.9 and position_on_button and pot_odds < 0.15:
            return ('raise', 0.3)  # Pure bluff with high aggression
        else:
            return ('fold', 0.0)
