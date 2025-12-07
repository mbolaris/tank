"""Configuration for the skill game system.

This module provides configuration for selecting and parameterizing skill games.
The active skill game determines what type of competitive interactions fish have
in the tank (besides basic survival behaviors).

Configuration can be changed to:
1. Start with simpler games (RPS, Number Prediction) for faster evolution
2. Progress to complex games (Poker) once basic learning evolves
3. Run experiments comparing evolution across different games
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Type

from core.skills.base import SkillGame, SkillGameType


class SkillDifficulty(Enum):
    """Difficulty levels for skill games."""

    TRIVIAL = "trivial"  # Almost no skill required
    EASY = "easy"  # Simple pattern recognition
    MEDIUM = "medium"  # Requires learning and adaptation
    HARD = "hard"  # Complex multi-factor decisions
    EXPERT = "expert"  # Requires sophisticated reasoning


@dataclass
class SkillGameConfig:
    """Configuration for the skill game system.

    Attributes:
        active_game: Which skill game is currently active
        stake_multiplier: Multiplier for energy stakes in games
        encounter_rate: How often fish encounter skill game opportunities
        min_energy_to_play: Minimum energy required to participate
        learning_enabled: Whether fish can learn during their lifetime
        inherit_strategy: Whether offspring inherit parent's strategy params
    """

    active_game: SkillGameType = SkillGameType.ROCK_PAPER_SCISSORS
    stake_multiplier: float = 1.0
    encounter_rate: float = 0.1  # Probability of skill game per interaction
    min_energy_to_play: float = 20.0
    learning_enabled: bool = True
    inherit_strategy: bool = True

    # Game-specific configurations
    rps_config: Dict[str, Any] = field(default_factory=lambda: {
        "stake": 10.0,
    })

    number_prediction_config: Dict[str, Any] = field(default_factory=lambda: {
        "stake": 10.0,
        "max_error_for_reward": 20.0,
        "history_length": 5,
        "pattern_change_frequency": 50,
    })

    poker_config: Dict[str, Any] = field(default_factory=lambda: {
        "small_blind": 5.0,
        "big_blind": 10.0,
        "max_hands": 10,
    })


# Global configuration instance
_global_config: Optional[SkillGameConfig] = None

# Game registry - maps game types to their implementation classes
_game_registry: Dict[SkillGameType, Type[SkillGame]] = {}


def register_skill_game(game_type: SkillGameType, game_class: Type[SkillGame]) -> None:
    """Register a skill game implementation.

    Args:
        game_type: The type of game
        game_class: The class that implements it
    """
    _game_registry[game_type] = game_class


def get_skill_game_config() -> SkillGameConfig:
    """Get the current skill game configuration.

    Returns:
        The global config, creating a default if needed
    """
    global _global_config
    if _global_config is None:
        _global_config = SkillGameConfig()
    return _global_config


def set_skill_game_config(config: SkillGameConfig) -> None:
    """Set the skill game configuration.

    Args:
        config: The new configuration
    """
    global _global_config
    _global_config = config


def get_active_skill_game() -> Optional[SkillGame]:
    """Get an instance of the currently active skill game.

    Returns:
        Instance of the active game, or None if not registered
    """
    config = get_skill_game_config()
    game_type = config.active_game

    if game_type not in _game_registry:
        # Try to auto-register known games
        _auto_register_games()

    if game_type not in _game_registry:
        return None

    game_class = _game_registry[game_type]

    # Get game-specific config
    if game_type == SkillGameType.ROCK_PAPER_SCISSORS:
        game_config = config.rps_config
        stake = game_config.get("stake", 10.0) * config.stake_multiplier
        return game_class(stake=stake)

    elif game_type == SkillGameType.NUMBER_GUESSING:
        game_config = config.number_prediction_config
        return game_class(
            stake=game_config.get("stake", 10.0) * config.stake_multiplier,
            max_error_for_reward=game_config.get("max_error_for_reward", 20.0),
            history_length=game_config.get("history_length", 5),
            pattern_change_frequency=game_config.get("pattern_change_frequency", 50),
        )

    elif game_type == SkillGameType.POKER:
        # Poker uses the existing poker system
        # Return None here - poker has its own integration
        return None

    else:
        # Generic instantiation
        return game_class()


def _auto_register_games() -> None:
    """Auto-register known skill games."""
    try:
        from core.skills.games.rock_paper_scissors import RockPaperScissorsGame
        register_skill_game(SkillGameType.ROCK_PAPER_SCISSORS, RockPaperScissorsGame)
    except ImportError:
        pass

    try:
        from core.skills.games.number_guessing import NumberGuessingGame
        register_skill_game(SkillGameType.NUMBER_GUESSING, NumberGuessingGame)
    except ImportError:
        pass


def set_active_skill_game(game_type: SkillGameType) -> None:
    """Convenience function to change the active skill game.

    Args:
        game_type: The game type to activate
    """
    config = get_skill_game_config()
    config.active_game = game_type


def get_game_difficulty(game_type: SkillGameType) -> SkillDifficulty:
    """Get the difficulty rating for a game type.

    Args:
        game_type: The game type

    Returns:
        Difficulty level
    """
    difficulty_map = {
        SkillGameType.ROCK_PAPER_SCISSORS: SkillDifficulty.EASY,
        SkillGameType.NUMBER_GUESSING: SkillDifficulty.MEDIUM,
        SkillGameType.MATCHING_PENNIES: SkillDifficulty.EASY,
        SkillGameType.POKER: SkillDifficulty.EXPERT,
    }
    return difficulty_map.get(game_type, SkillDifficulty.MEDIUM)


def get_recommended_starting_game() -> SkillGameType:
    """Get the recommended game to start evolution with.

    Simpler games allow faster evolution of basic learning capabilities.
    Once fish show they can learn simple patterns, graduate to harder games.

    Returns:
        Recommended starting game type
    """
    return SkillGameType.ROCK_PAPER_SCISSORS


def get_game_progression() -> list:
    """Get recommended progression of games by difficulty.

    Returns:
        List of (game_type, description) tuples in progression order
    """
    return [
        (
            SkillGameType.ROCK_PAPER_SCISSORS,
            "Simple 2-player game. Optimal: random 1/3 each. Tests basic randomization.",
        ),
        (
            SkillGameType.NUMBER_GUESSING,
            "Pattern prediction. Tests memory and pattern recognition.",
        ),
        (
            SkillGameType.POKER,
            "Complex multi-factor game. Tests hand evaluation, opponent modeling, bluffing.",
        ),
    ]
