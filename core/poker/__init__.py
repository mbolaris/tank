"""
Poker system for fish interactions.

This package provides a complete Texas Hold'em poker implementation including:
- Core game engine (cards, hands, game state)
- Hand strength evaluation
- Evolving AI strategies
- Fish poker interactions

The poker system is used to determine outcomes when fish collide, with the
winner gaining energy from the loser.
"""

# Core poker components
from core.poker.core import (
    BettingAction,
    BettingRound,
    Card,
    Deck,
    HandRank,
    PokerEngine,
    PokerGameState,
    PokerHand,
    Rank,
    Suit,
)

# Hand evaluation
from core.poker.evaluation import (
    calculate_pot_odds,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)

# Strategy system
from core.poker.strategy import (
    ALL_POKER_STRATEGIES,
    BalancedStrategy,
    HandStrength,
    LooseAggressiveStrategy,
    LoosePassiveStrategy,
    ManiacStrategy,
    OpponentModel,
    PokerStrategyAlgorithm,
    PokerStrategyEngine,
    TightAggressiveStrategy,
    TightPassiveStrategy,
    crossover_poker_strategies,
    get_random_poker_strategy,
)

__all__ = [
    # Core
    "Card",
    "Deck",
    "Rank",
    "Suit",
    "HandRank",
    "PokerHand",
    "BettingAction",
    "BettingRound",
    "PokerEngine",
    "PokerGameState",
    # Evaluation
    "calculate_pot_odds",
    "evaluate_starting_hand_strength",
    "get_action_recommendation",
    # Strategy
    "HandStrength",
    "OpponentModel",
    "PokerStrategyEngine",
    "PokerStrategyAlgorithm",
    "TightAggressiveStrategy",
    "LooseAggressiveStrategy",
    "TightPassiveStrategy",
    "LoosePassiveStrategy",
    "BalancedStrategy",
    "ManiacStrategy",
    "ALL_POKER_STRATEGIES",
    "get_random_poker_strategy",
    "crossover_poker_strategies",
]
