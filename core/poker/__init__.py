"""
Poker system for fish interactions.

This package provides a complete Texas Hold'em poker implementation including:
- Core game engine (cards, hands, game state)
- Hand strength evaluation
- Betting decision logic
- Game simulation
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
    PokerGameState,
    PokerHand,
    Rank,
    Suit,
    get_card,
)

# Betting module
from core.poker.betting import (
    AGGRESSION_HIGH,
    AGGRESSION_LOW,
    AGGRESSION_MEDIUM,
    decide_action,
)

# Hand evaluation
from core.poker.evaluation import (
    calculate_pot_odds,
    evaluate_hand,
    evaluate_hand_cached,
    evaluate_starting_hand_strength,
    get_action_recommendation,
)

# Simulation
from core.poker.simulation import (
    finalize_pot,
    resolve_bet,
    simulate_game,
    simulate_multi_round_game,
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
from core.poker.table import PokerTable

__all__ = [
    # Core
    "Card",
    "Deck",
    "Rank",
    "Suit",
    "get_card",
    "HandRank",
    "PokerHand",
    "BettingAction",
    "BettingRound",
    "PokerGameState",
    # Betting
    "AGGRESSION_HIGH",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
    "decide_action",
    # Evaluation
    "calculate_pot_odds",
    "evaluate_hand",
    "evaluate_hand_cached",
    "evaluate_starting_hand_strength",
    "get_action_recommendation",
    # Simulation
    "finalize_pot",
    "resolve_bet",
    "simulate_game",
    "simulate_multi_round_game",
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
    "PokerTable",
]
