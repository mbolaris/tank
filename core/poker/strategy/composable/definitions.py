"""Definitions for composable poker strategy system.

This module contains Enums and Constants used by the composable poker strategy.
"""

from enum import IntEnum

# =============================================================================
# Sub-behavior Enums - Each category has discrete options
# =============================================================================


class HandSelection(IntEnum):
    """How tight/loose to play pre-flop."""

    ULTRA_TIGHT = 0  # Only premium hands (AA, KK, QQ, AK) - ~5% of hands
    TIGHT = 1  # Strong hands - ~15% of hands
    BALANCED = 2  # Standard range - ~25% of hands
    LOOSE = 3  # Wide range - ~50% of hands


class BettingStyle(IntEnum):
    """How to size bets and raises."""

    SMALL_BALL = 0  # Small bets, pot control, minimize risk
    VALUE_HEAVY = 1  # Big bets with strong hands, extract value
    POLARIZED = 2  # Either big or check, rarely medium (GTO-like)
    POT_GEOMETRIC = 3  # Mathematical pot-ratio sizing for SPR


class BluffingApproach(IntEnum):
    """When and how to bluff."""

    NEVER_BLUFF = 0  # Only bet with made hands (exploitable but safe)
    OCCASIONAL = 1  # Low frequency, calculated bluffs
    BALANCED = 2  # GTO-inspired bluff-to-value ratio
    AGGRESSIVE = 3  # Frequent bluffs, apply maximum pressure


class PositionAwareness(IntEnum):
    """How much position affects strategic decisions."""

    IGNORE = 0  # Same play regardless of position
    SLIGHT_ADJUSTMENT = 1  # Minor adjustments (+5-10% range IP)
    HEAVY_EXPLOIT = 2  # Major strategy shift by position (+20%+ range IP)


class ShowdownTendency(IntEnum):
    """How to handle contested pots at showdown."""

    FOLD_EASILY = 0  # Give up with medium hands, avoid close spots
    CALL_STATION = 1  # Call down liberally, catch bluffs
    AGGRESSIVE_DENY = 2  # Raise or fold, rarely call (polarized response)


# Category counts for inheritance bounds
SUB_BEHAVIOR_COUNTS = {
    "hand_selection": len(HandSelection),
    "betting_style": len(BettingStyle),
    "bluffing_approach": len(BluffingApproach),
    "position_awareness": len(PositionAwareness),
    "showdown_tendency": len(ShowdownTendency),
}


# =============================================================================
# Sub-behavior Parameter Bounds
# =============================================================================

POKER_SUB_BEHAVIOR_PARAMS = {
    # Hand selection thresholds
    "premium_threshold": (0.75, 0.95),  # Minimum strength for premium play
    "playable_threshold": (0.20, 0.55),  # Minimum strength to enter pot
    "position_range_expand": (0.05, 0.20),  # How much position widens range
    # Betting parameters
    "value_bet_sizing": (0.4, 1.2),  # Pot fraction for value bets
    "bluff_sizing": (0.3, 0.9),  # Pot fraction for bluffs
    "continuation_bet_freq": (0.4, 0.85),  # C-bet frequency
    # Bluffing parameters
    "bluff_frequency": (0.05, 0.45),  # Base bluff rate
    "semibluff_threshold": (0.15, 0.40),  # Hand strength for semibluffs
    # Position parameters
    "ip_aggression_boost": (0.05, 0.30),  # Extra aggression in position
    "oop_tightening": (0.05, 0.25),  # How much tighter OOP
    # Pot odds and risk
    "pot_odds_sensitivity": (0.8, 1.6),  # How strictly to follow pot odds
    "risk_tolerance": (0.15, 0.55),  # Energy fraction willing to risk
    "desperation_threshold": (0.12, 0.35),  # Energy ratio triggering desperate play
    # Opponent modeling weights
    "opponent_model_weight": (0.0, 0.5),  # How much to adjust based on opponent history
}

# =============================================================================
# CFR Learning Constants
# =============================================================================

# Action space for CFR learning (4 actions as approved)
CFR_ACTIONS = ("fold", "call", "raise_small", "raise_big")

# Inheritance decay for Lamarckian learning (80% as approved)
CFR_INHERITANCE_DECAY = 0.80

# Maximum number of info sets to track (memory cap)
CFR_MAX_INFO_SETS = 100

# Minimum visits before an info set is inheritable
CFR_MIN_VISITS_FOR_INHERITANCE = 3

# Info set discretization buckets
CFR_HAND_STRENGTH_BUCKETS = 5  # 0-4: trash, weak, medium, strong, monster
CFR_POT_RATIO_BUCKETS = 5  # 0-4: tiny, small, medium, large, huge
