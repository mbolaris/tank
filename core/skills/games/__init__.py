"""Concrete skill game implementations.

This module contains implementations of specific skill games:
- Rock-Paper-Scissors: Simple 2-player game with known Nash equilibrium
- Number Guessing: Single-player game testing estimation skills
- Matching Pennies: Zero-sum game similar to RPS but binary
"""

from core.skills.games.rock_paper_scissors import (
    RockPaperScissorsGame,
    RPSAction,
    RPSStrategy,
    OptimalRPSStrategy,
)
from core.skills.games.number_guessing import (
    NumberGuessingGame,
    NumberGuessingStrategy,
    OptimalNumberGuessingStrategy,
)

__all__ = [
    "RockPaperScissorsGame",
    "RPSAction",
    "RPSStrategy",
    "OptimalRPSStrategy",
    "NumberGuessingGame",
    "NumberGuessingStrategy",
    "OptimalNumberGuessingStrategy",
]
