"""Skill game framework for evolving learnable behaviors.

IMPORTANT: This is Alife (Artificial Life), NOT a Genetic Algorithm!

Fish play skill games as natural interactions in the tank:
- Winners gain energy, losers lose energy
- Better players survive longer and reproduce more
- Evolution emerges through natural selection, not explicit fitness evaluation

This module provides a pluggable framework for different "skill games" that fish
can learn to play. The framework allows easy swapping between games of different
complexity, from simple toy problems (Rock-Paper-Scissors, Number Guessing) to
complex games (Poker).

Key concepts:
- SkillGame: Abstract base class defining the interface for any game
- SkillStrategy: Fish's approach to playing a game (inheritable, learnable)
- SkillGameResult: Outcome of a game (energy flow between players)
- SkillEvaluationMetrics: OBSERVATIONAL metrics (for reporting, NOT selection)

Design goals:
1. Natural selection: Games affect energy, which affects survival/reproduction
2. Skill matters: Games reward learning and adaptation, not just randomness
3. Configurable: Swap games without changing core simulation code
4. Observable: Clear metrics for humans/AI to track evolutionary progress
"""

from core.skills.base import (
    SkillGame,
    SkillGameType,
    SkillStrategy,
    SkillGameResult,
    SkillEvaluationMetrics,
)
from core.skills.config import SkillGameConfig, get_active_skill_game

__all__ = [
    "SkillGame",
    "SkillGameType",
    "SkillStrategy",
    "SkillGameResult",
    "SkillEvaluationMetrics",
    "SkillGameConfig",
    "get_active_skill_game",
]
