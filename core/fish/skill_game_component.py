"""Fish skill game statistics and strategy component.

This module tracks individual fish skill game performance and manages
their learned strategies for each game type.

IMPORTANT: This is Alife, not GA. Stats are for observation only.
Selection happens naturally through energy gains/losses from games.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Deque, Dict, Optional

if TYPE_CHECKING:
    from random import Random

from core.skills.base import SkillGameResult, SkillGameType, SkillStrategy


@dataclass
class FishSkillGameStats:
    """Tracks skill game statistics for an individual fish.

    These stats are for OBSERVATION purposes - to help us understand
    how well fish are learning. Selection pressure comes from energy
    changes, not from these metrics.

    Attributes:
        game_type: Which skill game these stats are for
        total_games: Total games played
        wins: Number of games won
        losses: Number of games lost
        ties: Number of tied games
        total_energy_won: Cumulative energy won
        total_energy_lost: Cumulative energy lost
        optimal_plays: Times the fish played optimally
        suboptimal_plays: Times the fish played suboptimally
    """

    game_type: SkillGameType = SkillGameType.ROCK_PAPER_SCISSORS
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    optimal_plays: int = 0
    suboptimal_plays: int = 0

    # Track recent results for observing learning trends
    _recent_results: Deque[int] = field(default_factory=lambda: deque(maxlen=20), repr=False)
    _recent_optimal: Deque[int] = field(default_factory=lambda: deque(maxlen=20), repr=False)

    def get_net_energy(self) -> float:
        """Calculate net energy from skill games."""
        return self.total_energy_won - self.total_energy_lost

    def get_win_rate(self) -> float:
        """Calculate win rate (0.0 to 1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    def get_optimality_rate(self) -> float:
        """Calculate how often fish plays optimally (0.0 to 1.0)."""
        total = self.optimal_plays + self.suboptimal_plays
        if total == 0:
            return 0.0
        return self.optimal_plays / total

    def get_recent_win_rate(self) -> float:
        """Calculate win rate for recent games."""
        if len(self._recent_results) == 0:
            return 0.0
        return sum(self._recent_results) / len(self._recent_results)

    def get_recent_optimality_rate(self) -> float:
        """Calculate optimality rate for recent games."""
        if len(self._recent_optimal) == 0:
            return 0.0
        return sum(self._recent_optimal) / len(self._recent_optimal)

    def get_learning_trend(self) -> str:
        """Observe if fish is improving at the game.

        Returns:
            "improving" if recent optimality > overall
            "declining" if recent optimality < overall
            "stable" otherwise
        """
        if len(self._recent_optimal) < 10:
            return "stable"

        overall = self.get_optimality_rate()
        recent = self.get_recent_optimality_rate()

        if recent > overall + 0.1:
            return "improving"
        elif recent < overall - 0.1:
            return "declining"
        return "stable"

    def record_result(self, result: SkillGameResult) -> None:
        """Record a game result.

        Args:
            result: The skill game result
        """
        self.total_games += 1

        if result.won:
            self.wins += 1
            self._recent_results.append(1)
            if result.score_change > 0:
                self.total_energy_won += result.score_change
        elif result.tied:
            self.ties += 1
            self._recent_results.append(0)
        else:
            self.losses += 1
            self._recent_results.append(0)
            if result.score_change < 0:
                self.total_energy_lost += abs(result.score_change)

        if result.was_optimal:
            self.optimal_plays += 1
            self._recent_optimal.append(1)
        else:
            self.suboptimal_plays += 1
            self._recent_optimal.append(0)

    def get_stats_dict(self) -> Dict[str, Any]:
        """Get statistics as dictionary for serialization."""
        return {
            "game_type": self.game_type.value,
            "total_games": self.total_games,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "win_rate": self.get_win_rate(),
            "total_energy_won": self.total_energy_won,
            "total_energy_lost": self.total_energy_lost,
            "net_energy": self.get_net_energy(),
            "optimality_rate": self.get_optimality_rate(),
            "recent_win_rate": self.get_recent_win_rate(),
            "recent_optimality_rate": self.get_recent_optimality_rate(),
            "learning_trend": self.get_learning_trend(),
        }


class SkillGameComponent:
    """Manages skill game strategies and stats for a fish.

    This component stores:
    1. The fish's strategies for each game type
    2. Statistics for each game type

    Uses __slots__ for memory efficiency, matching the pattern of other
    fish components (EnergyComponent, LifecycleComponent, ReproductionComponent).
    """

    __slots__ = ("_strategies", "_stats")

    def __init__(self) -> None:
        """Initialize the skill game component."""
        # Strategies for each game type
        self._strategies: Dict[SkillGameType, SkillStrategy] = {}
        # Stats for each game type
        self._stats: Dict[SkillGameType, FishSkillGameStats] = {}

    def get_strategy(self, game_type: SkillGameType) -> Optional[SkillStrategy]:
        """Get the fish's strategy for a game type.

        Args:
            game_type: The game type

        Returns:
            The strategy, or None if not initialized
        """
        return self._strategies.get(game_type)

    def set_strategy(self, game_type: SkillGameType, strategy: SkillStrategy) -> None:
        """Set the fish's strategy for a game type.

        Args:
            game_type: The game type
            strategy: The strategy to use
        """
        self._strategies[game_type] = strategy

    def get_stats(self, game_type: SkillGameType) -> FishSkillGameStats:
        """Get stats for a game type, creating if needed.

        Args:
            game_type: The game type

        Returns:
            The stats for that game
        """
        if game_type not in self._stats:
            self._stats[game_type] = FishSkillGameStats(game_type=game_type)
        return self._stats[game_type]

    def record_game_result(
        self,
        game_type: SkillGameType,
        result: SkillGameResult,
    ) -> None:
        """Record a game result and update strategy via learning.

        Args:
            game_type: The game type
            result: The game result
        """
        # Update stats
        stats = self.get_stats(game_type)
        stats.record_result(result)

        # Let strategy learn from result
        strategy = self.get_strategy(game_type)
        if strategy is not None:
            strategy.learn_from_result(result)

    def get_strategy_parameters(self, game_type: SkillGameType) -> Dict[str, float]:
        """Get strategy parameters for inheritance.

        Args:
            game_type: The game type

        Returns:
            Strategy parameters dict, or empty if no strategy
        """
        strategy = self.get_strategy(game_type)
        if strategy is not None:
            return strategy.get_parameters()
        return {}

    def set_strategy_parameters(self, game_type: SkillGameType, params: Dict[str, float]) -> None:
        """Set strategy parameters (e.g., from parent).

        Args:
            game_type: The game type
            params: Parameters to set
        """
        strategy = self.get_strategy(game_type)
        if strategy is not None:
            strategy.set_parameters(params)

    def mutate_strategy(self, game_type: SkillGameType, mutation_rate: float = 0.1) -> None:
        """Apply mutation to a strategy.

        Args:
            game_type: The game type
            mutation_rate: Mutation rate/magnitude
        """
        strategy = self.get_strategy(game_type)
        if strategy is not None:
            strategy.mutate(mutation_rate)

    def get_all_stats_dict(self) -> Dict[str, Any]:
        """Get all game stats as dictionary."""
        return {game_type.value: stats.get_stats_dict() for game_type, stats in self._stats.items()}

    def inherit_from_parent(
        self,
        parent_component: "SkillGameComponent",
        mutation_rate: float = 0.1,
        rng: Optional["Random"] = None,
    ) -> None:
        """Inherit strategies from parent with mutation.

        Args:
            parent_component: Parent's skill game component
            mutation_rate: Mutation rate for inherited strategies
            rng: Optional RNG for deterministic mutation
        """
        for game_type, strategy in parent_component._strategies.items():
            # Copy parameters from parent
            params = strategy.get_parameters()

            # Create new strategy of same type
            child_strategy = type(strategy)()
            child_strategy.set_parameters(params)

            # Apply mutation
            child_strategy.mutate(mutation_rate, rng=rng)

            self._strategies[game_type] = child_strategy
