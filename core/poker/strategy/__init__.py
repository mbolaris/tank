"""
Poker strategy system for evolving AI players.

This package contains poker strategy engines and evolving strategy algorithms.
"""

from core.poker.strategy.base import (HandStrength, OpponentModel,
                                      PokerStrategyEngine)
# Re-export from new location
from core.poker.strategy.composable import (BettingStyle, BluffingApproach,
                                            ComposablePokerStrategy,
                                            HandSelection, PositionAwareness,
                                            ShowdownTendency)
from core.poker.strategy.implementations import (ALL_POKER_STRATEGIES,
                                                 BASELINE_STRATEGIES,
                                                 BalancedStrategy,
                                                 LooseAggressiveStrategy,
                                                 LoosePassiveStrategy,
                                                 ManiacStrategy,
                                                 PokerStrategyAlgorithm,
                                                 TightAggressiveStrategy,
                                                 TightPassiveStrategy,
                                                 crossover_poker_strategies,
                                                 get_random_poker_strategy)

__all__ = [
    # Base
    "HandStrength",
    "OpponentModel",
    "PokerStrategyEngine",
    # Implementations (monolithic - kept for benchmarking)
    "PokerStrategyAlgorithm",
    "TightAggressiveStrategy",
    "LooseAggressiveStrategy",
    "TightPassiveStrategy",
    "LoosePassiveStrategy",
    "BalancedStrategy",
    "ManiacStrategy",
    "ALL_POKER_STRATEGIES",
    "BASELINE_STRATEGIES",
    "get_random_poker_strategy",
    "crossover_poker_strategies",
    # Composable (new evolvable system)
    "ComposablePokerStrategy",
    "HandSelection",
    "BettingStyle",
    "BluffingApproach",
    "PositionAwareness",
    "ShowdownTendency",
]
