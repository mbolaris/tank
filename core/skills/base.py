"""Base classes for the skill game framework.

IMPORTANT: This is Alife (Artificial Life), NOT a Genetic Algorithm!

In Alife, evolution emerges naturally:
- Fish play skill games as part of their life in the tank
- Winning games gives energy (can reproduce more)
- Losing games costs energy (may starve/die)
- Natural selection favors fish with better strategies
- No explicit "fitness evaluation" drives selection

The "evaluation" methods in this module are for OBSERVATION only:
- We (humans/AI) use them to measure how well evolution is working
- They help us understand which strategies are emerging
- They do NOT drive selection - that happens through energy and survival

Key design principles:
1. Games are natural interactions, not fitness tests
2. Energy flows through games (winners gain, losers lose)
3. Better players survive longer and reproduce more
4. Metrics are for observation/reporting, not selection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar


class SkillGameType(Enum):
    """Enumeration of available skill games."""

    ROCK_PAPER_SCISSORS = "rock_paper_scissors"
    NUMBER_GUESSING = "number_guessing"
    MATCHING_PENNIES = "matching_pennies"
    POKER = "poker"


@dataclass
class SkillGameResult:
    """Result of a skill game round/match.

    This is a generic result container that works across all game types.
    Games can add custom data in the `details` field.
    """

    # Core outcome
    player_id: str
    opponent_id: Optional[str]  # None for single-player games
    won: bool
    tied: bool = False

    # Energy/score changes
    score_change: float = 0.0  # Positive = gained, negative = lost

    # For evaluation purposes
    optimal_action: Optional[Any] = None  # What optimal strategy would have done
    actual_action: Optional[Any] = None  # What the player actually did
    was_optimal: bool = False  # Did the player play optimally?

    # Game-specific details
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillEvaluationMetrics:
    """Observational metrics for skill game performance.

    IMPORTANT: These metrics are for OBSERVATION, not for driving selection!
    We use these to understand how evolution is progressing, not to select
    which fish survive. Survival is determined by energy (won/lost in games).

    These metrics help us (humans/AI) answer questions like:
    - Are fish learning to play better over generations?
    - What strategies are emerging in the population?
    - How far is the population from optimal play?
    """

    # Basic performance
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0

    # Score/energy tracking
    total_score: float = 0.0
    average_score_per_game: float = 0.0

    # Optimality metrics (the key evaluation metrics!)
    optimal_actions: int = 0  # How many times player chose optimal action
    suboptimal_actions: int = 0
    optimality_rate: float = 0.0  # optimal_actions / total_actions

    # Distance from optimal (lower is better)
    # For deterministic games: 0.0 = perfect play
    # For stochastic games: theoretical minimum variance
    distance_from_optimal: float = 1.0

    # Exploitability (for game-theoretic games)
    # How much could a perfect counter-strategy win against this player?
    exploitability: float = 1.0

    # Learning metrics
    recent_optimality_rate: float = 0.0  # Last N games
    improvement_trend: float = 0.0  # Positive = getting better

    # Game-specific metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.wins + self.losses + self.ties
        return self.wins / total if total > 0 else 0.0

    def update_from_result(self, result: SkillGameResult) -> None:
        """Update metrics from a game result."""
        self.games_played += 1

        if result.won:
            self.wins += 1
        elif result.tied:
            self.ties += 1
        else:
            self.losses += 1

        self.total_score += result.score_change
        self.average_score_per_game = self.total_score / self.games_played

        if result.was_optimal:
            self.optimal_actions += 1
        else:
            self.suboptimal_actions += 1

        total_actions = self.optimal_actions + self.suboptimal_actions
        self.optimality_rate = self.optimal_actions / total_actions if total_actions > 0 else 0.0


# Type variable for game-specific action types
ActionType = TypeVar("ActionType")


class SkillStrategy(ABC, Generic[ActionType]):
    """Abstract base class for skill game strategies.

    Each fish has a strategy for each skill game. Strategies can be:
    - Genetically encoded (inherited parameters)
    - Learned (updated based on game outcomes)
    - Mixed (some genes, some learning)
    """

    @abstractmethod
    def choose_action(self, game_state: Dict[str, Any]) -> ActionType:
        """Choose an action given the current game state.

        Args:
            game_state: Game-specific state information

        Returns:
            The action to take (type depends on the game)
        """
        pass

    @abstractmethod
    def learn_from_result(self, result: SkillGameResult) -> None:
        """Update strategy based on game outcome.

        This is how fish learn to play better over time within their lifetime.

        Args:
            result: The outcome of the game
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, float]:
        """Get the strategy parameters (for inheritance/mutation).

        Returns:
            Dictionary of parameter names to values
        """
        pass

    @abstractmethod
    def set_parameters(self, params: Dict[str, float]) -> None:
        """Set strategy parameters (from parent genome or mutation).

        Args:
            params: Dictionary of parameter names to values
        """
        pass

    def mutate(self, mutation_rate: float = 0.1, rng: Optional["random.Random"] = None) -> None:
        """Apply random mutation to strategy parameters.

        Default implementation mutates all parameters slightly.
        Override for game-specific mutation logic.

        Args:
            mutation_rate: Probability and magnitude of mutations
            rng: Optional random number generator for deterministic mutations
        """
        import random
        _rng = rng if rng is not None else random
        params = self.get_parameters()
        mutated = {}
        for key, value in params.items():
            if _rng.random() < mutation_rate:
                # Add Gaussian noise
                mutated[key] = value + _rng.gauss(0, mutation_rate)
            else:
                mutated[key] = value
        self.set_parameters(mutated)


class SkillGame(ABC):
    """Abstract base class for skill games.

    A skill game is any game that fish can learn to play. Games must provide:
    1. Rules for how the game is played
    2. An optimal strategy (or Nash equilibrium) for evaluation
    3. Metrics for measuring skill improvement
    """

    @property
    @abstractmethod
    def game_type(self) -> SkillGameType:
        """Return the type of this game."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the game."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the game and its optimal strategy."""
        pass

    @property
    @abstractmethod
    def is_zero_sum(self) -> bool:
        """Whether this is a zero-sum game (one player's gain = other's loss)."""
        pass

    @property
    @abstractmethod
    def has_optimal_strategy(self) -> bool:
        """Whether there's a known optimal/Nash equilibrium strategy."""
        pass

    @property
    def optimal_strategy_description(self) -> str:
        """Description of the optimal strategy for this game."""
        return "Unknown"

    @abstractmethod
    def create_default_strategy(self) -> SkillStrategy:
        """Create a new default strategy for this game.

        This is used when a fish is born and needs a starting strategy.

        Returns:
            A new strategy instance with default/random parameters
        """
        pass

    @abstractmethod
    def create_optimal_strategy(self) -> SkillStrategy:
        """Create an optimal (or Nash equilibrium) strategy.

        This is used as a benchmark for evaluation.

        Returns:
            A strategy that plays optimally (or near-optimally)
        """
        pass

    @abstractmethod
    def play_round(
        self,
        player_strategy: SkillStrategy,
        opponent_strategy: Optional[SkillStrategy] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> SkillGameResult:
        """Play one round of the game.

        Args:
            player_strategy: The player's strategy
            opponent_strategy: The opponent's strategy (None for single-player)
            game_state: Optional additional state

        Returns:
            The result of the round
        """
        pass

    @abstractmethod
    def observe_strategy(
        self,
        strategy: SkillStrategy,
        num_games: int = 1000,
        opponent: Optional[SkillStrategy] = None,
    ) -> SkillEvaluationMetrics:
        """Observe a strategy's performance for reporting purposes.

        This is for OBSERVATION ONLY - to help us understand what strategies
        are emerging and how well evolution is progressing. This does NOT
        drive selection. Selection happens naturally through energy flow.

        Plays the strategy against a benchmark and collects metrics.

        Args:
            strategy: The strategy to observe
            num_games: Number of games to play for observation
            opponent: Opponent strategy (default: optimal strategy)

        Returns:
            Observational metrics for reporting
        """
        pass

    @abstractmethod
    def calculate_exploitability(self, strategy: SkillStrategy) -> float:
        """Calculate how exploitable a strategy is.

        Exploitability measures how much a perfect counter-strategy could
        win against this strategy. Lower is better.

        For Nash equilibrium strategies, exploitability = 0.

        Args:
            strategy: The strategy to analyze

        Returns:
            Exploitability score (0.0 = unexploitable, 1.0 = highly exploitable)
        """
        pass

    def get_difficulty_rating(self) -> float:
        """Return a difficulty rating for this game (0.0-1.0).

        Used for progressive difficulty systems.
        0.0 = trivial, 1.0 = very complex
        """
        return 0.5

    def get_evaluation_summary(
        self,
        metrics: SkillEvaluationMetrics,
    ) -> Dict[str, Any]:
        """Get a summary of evaluation results for reporting.

        Args:
            metrics: The evaluation metrics

        Returns:
            Human-readable summary dictionary
        """
        return {
            "game": self.name,
            "games_played": metrics.games_played,
            "win_rate": f"{metrics.win_rate():.1%}",
            "optimality_rate": f"{metrics.optimality_rate:.1%}",
            "distance_from_optimal": f"{metrics.distance_from_optimal:.3f}",
            "exploitability": f"{metrics.exploitability:.3f}",
            "average_score": f"{metrics.average_score_per_game:.2f}",
        }
