"""Poker skill game adapter - wraps existing poker system as a SkillGame.

This module adapts the existing poker system (PokerInteraction, PokerStrategyAlgorithm)
to conform to the generic SkillGame interface. This allows poker to be treated
uniformly with other skill games (RPS, NumberGuessing, etc.).

Key Design Decisions:
- PokerSkillStrategy wraps PokerStrategyAlgorithm to implement SkillStrategy
- PokerSkillGame wraps poker engine to implement SkillGame
- Existing poker logic is reused, not duplicated
- Migration support maintained with existing poker system

Benefits:
- Poker is now interchangeable with other skill games
- Consistent evaluation/metrics across all games
- Fish can use same SkillfulAgent interface for poker
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations import (BalancedStrategy,
                                                 PokerStrategyAlgorithm,
                                                 get_random_poker_strategy)
from core.skills.base import (SkillEvaluationMetrics, SkillGame,
                              SkillGameResult, SkillGameType, SkillStrategy)


@dataclass
class PokerSkillStrategy(SkillStrategy[BettingAction]):
    """Adapter wrapping PokerStrategyAlgorithm as a SkillStrategy.

    This allows poker strategies to work with the generic skill game framework
    while reusing all existing poker strategy logic.
    """

    # The wrapped poker strategy
    _strategy: PokerStrategyAlgorithm = field(default_factory=get_random_poker_strategy)

    # Track recent results for learning
    _recent_results: list = field(default_factory=list)
    _max_history: int = 20

    def __post_init__(self):
        """Ensure we have a valid strategy."""
        if self._strategy is None:
            self._strategy = get_random_poker_strategy()

    def choose_action(self, game_state: Dict[str, Any]) -> BettingAction:
        """Choose a poker betting action based on game state.

        Args:
            game_state: Dict containing:
                - hand_strength: 0.0-1.0 normalized hand strength
                - current_bet: Current player's bet
                - opponent_bet: Opponent's bet
                - pot: Current pot size
                - player_energy: Player's available energy
                - position_on_button: Whether player is on button

        Returns:
            BettingAction to take
        """
        action, amount = self._strategy.decide_action(
            hand_strength=game_state.get("hand_strength", 0.5),
            current_bet=game_state.get("current_bet", 0.0),
            opponent_bet=game_state.get("opponent_bet", 0.0),
            pot=game_state.get("pot", 0.0),
            player_energy=game_state.get("player_energy", 100.0),
            position_on_button=game_state.get("position_on_button", False),
        )
        return action

    def learn_from_result(self, result: SkillGameResult) -> None:
        """Update strategy based on game outcome.

        Unlike RPS, poker learning is more complex. We track results
        and can use them for future parameter adjustments.

        Args:
            result: The game result
        """
        # Track result for analysis
        self._recent_results.append(
            {
                "won": result.won,
                "score_change": result.score_change,
                "was_optimal": result.was_optimal,
            }
        )

        # Keep history bounded
        if len(self._recent_results) > self._max_history:
            self._recent_results = self._recent_results[-self._max_history :]

        # Note: Actual parameter evolution happens through genome mutation,
        # not runtime learning. This is intentional - poker is complex enough
        # that we let evolution find good parameters rather than runtime learning.

    def get_parameters(self) -> Dict[str, float]:
        """Get strategy parameters for inheritance.

        Returns:
            Dict of strategy parameters
        """
        params = dict(self._strategy.parameters)
        params["strategy_type"] = hash(type(self._strategy).__name__) % 1000
        return params

    def set_parameters(self, params: Dict[str, float]) -> None:
        """Set strategy parameters.

        Args:
            params: Parameters to set
        """
        for key, value in params.items():
            if key in self._strategy.parameters:
                self._strategy.parameters[key] = value

    def mutate(self, mutation_rate: float = 0.1, rng: Optional[random.Random] = None) -> None:
        """Mutate the strategy.

        Args:
            mutation_rate: Mutation magnitude
            rng: Optional RNG for deterministic mutations
        """
        self._strategy.mutate_parameters(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_rate * 2,
            rng=rng,
        )

    @property
    def strategy_algorithm(self) -> PokerStrategyAlgorithm:
        """Get the underlying poker strategy algorithm."""
        return self._strategy

    @classmethod
    def from_poker_strategy(cls, strategy: PokerStrategyAlgorithm) -> "PokerSkillStrategy":
        """Create a PokerSkillStrategy from an existing PokerStrategyAlgorithm.

        Args:
            strategy: The poker strategy to wrap

        Returns:
            New PokerSkillStrategy wrapping the given strategy
        """
        return cls(_strategy=strategy)


class OptimalPokerStrategy(PokerSkillStrategy):
    """A GTO-inspired poker strategy used as benchmark.

    This uses the BalancedStrategy which is designed to be harder to exploit.
    """

    def __init__(self):
        super().__init__(_strategy=BalancedStrategy())

    def learn_from_result(self, result: SkillGameResult) -> None:
        """Optimal strategy doesn't change from results."""
        pass

    def set_parameters(self, params: Dict[str, float]) -> None:
        """Optimal strategy ignores parameter changes."""
        pass


class PokerSkillGame(SkillGame):
    """Poker implementation of SkillGame.

    This adapts the existing poker system to work with the generic skill game
    framework. It doesn't replace the existing poker interaction system, but
    provides an alternative interface that conforms to SkillGame.

    Note: For full poker games with multiple betting rounds, the existing
    PokerInteraction system is still used. This adapter is primarily for:
    - Consistent strategy creation/evaluation
    - Integration with SkillGameComponent
    - Unified metrics and reporting
    """

    # Default stakes
    small_blind: float = 5.0
    big_blind: float = 10.0

    def __init__(
        self,
        small_blind: float = 5.0,
        big_blind: float = 10.0,
    ):
        """Initialize poker game with configurable blinds.

        Args:
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.small_blind = small_blind
        self.big_blind = big_blind

    @property
    def game_type(self) -> SkillGameType:
        return SkillGameType.POKER

    @property
    def name(self) -> str:
        return "Texas Hold'em Poker"

    @property
    def description(self) -> str:
        return (
            "Texas Hold'em poker with evolving betting strategies. "
            "Fish compete heads-up, making betting decisions based on "
            "hand strength and position. Winners gain energy from losers."
        )

    @property
    def is_zero_sum(self) -> bool:
        return True  # Winner's gain = loser's loss (minus rake if any)

    @property
    def has_optimal_strategy(self) -> bool:
        return True  # GTO exists, though very complex

    @property
    def optimal_strategy_description(self) -> str:
        return (
            "Game Theory Optimal (GTO) poker is the Nash equilibrium. "
            "It involves balanced ranges, proper sizing, and mixed strategies. "
            "Our 'balanced' strategy approximates this with position awareness "
            "and pot-odds-based decisions."
        )

    def create_default_strategy(self, rng: Optional[random.Random] = None) -> PokerSkillStrategy:
        """Create a new default poker strategy.

        Returns:
            Random poker strategy for new fish
        """
        return PokerSkillStrategy(_strategy=get_random_poker_strategy(rng=rng))

    def create_optimal_strategy(self) -> OptimalPokerStrategy:
        """Create an optimal (GTO-approximating) strategy.

        Returns:
            Balanced strategy as benchmark
        """
        return OptimalPokerStrategy()

    def play_round(
        self,
        player_strategy: SkillStrategy,
        opponent_strategy: Optional[SkillStrategy] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> SkillGameResult:
        """Play one round of simplified poker.

        This is a simplified version for strategy evaluation. For full
        multi-street poker, use PokerInteraction directly.

        Args:
            player_strategy: Player's poker strategy
            opponent_strategy: Opponent's strategy (default: optimal)
            game_state: Optional state including hand_strength, pot, rng, etc.

        Returns:
            Game result with score change
        """

        if opponent_strategy is None:
            opponent_strategy = self.create_optimal_strategy()

        state = game_state or {}

        # Use provided RNG or fail loudly
        _rng = state.get("rng")
        if _rng is None:
            # Check if we can fallback to a deterministic source, otherwise fail
            from core.util.rng import get_rng_or_default

            # If called from observe_strategy (before my fix lands), this might fail.
            # But user asked to fail loudly.
            _rng = get_rng_or_default(None, context="PokerSkillGame.play_round")

        # Generate random hand strengths if not provided (using RNG)
        player_strength = state.get("hand_strength", _rng.random())
        opponent_strength = state.get("opponent_strength", _rng.random())

        pot = self.small_blind + self.big_blind

        # Build game states for each player
        player_state = {
            "hand_strength": player_strength,
            "current_bet": self.small_blind,
            "opponent_bet": self.big_blind,
            "pot": pot,
            "player_energy": state.get("player_energy", 100.0),
            "position_on_button": state.get("position_on_button", False),
        }

        opponent_state = {
            "hand_strength": opponent_strength,
            "current_bet": self.big_blind,
            "opponent_bet": self.small_blind,
            "pot": pot,
            "player_energy": state.get("opponent_energy", 100.0),
            "position_on_button": not state.get("position_on_button", False),
        }

        # Get actions
        player_action = player_strategy.choose_action(player_state)
        opponent_action = opponent_strategy.choose_action(opponent_state)

        # Simplified showdown logic
        # Both fold = tie, one folds = other wins pot
        # Neither folds = better hand wins
        if player_action == BettingAction.FOLD:
            # Player folds
            won = False
            tied = False
            score_change = -self.small_blind
        elif opponent_action == BettingAction.FOLD:
            # Opponent folds
            won = True
            tied = False
            score_change = self.big_blind
        else:
            # Showdown
            if player_strength > opponent_strength:
                won = True
                tied = False
                score_change = pot / 2  # Win opponent's contribution
            elif player_strength < opponent_strength:
                won = False
                tied = False
                score_change = -pot / 2
            else:
                won = False
                tied = True
                score_change = 0

        # Determine if play was "optimal" (folded weak hands, bet strong hands)
        if isinstance(player_strategy, PokerSkillStrategy):
            # Good play: fold weak, bet/raise strong
            if (player_strength < 0.3 and player_action == BettingAction.FOLD) or (
                player_strength > 0.7 and player_action == BettingAction.RAISE
            ):
                was_optimal = True
            else:
                was_optimal = False
        else:
            was_optimal = False

        return SkillGameResult(
            player_id=state.get("player_id", "player"),
            opponent_id=state.get("opponent_id", "opponent"),
            won=won,
            tied=tied,
            score_change=score_change,
            optimal_action=None,  # No single optimal action in poker
            actual_action=player_action,
            was_optimal=was_optimal,
            details={
                "player_action": player_action,
                "opponent_action": opponent_action,
                "player_strength": player_strength,
                "opponent_strength": opponent_strength,
                "pot": pot,
            },
        )

    def observe_strategy(
        self,
        strategy: SkillStrategy,
        num_games: int = 1000,
        opponent: Optional[SkillStrategy] = None,
    ) -> SkillEvaluationMetrics:
        """Observe a poker strategy's performance.

        Args:
            strategy: Strategy to evaluate
            num_games: Number of hands to play
            opponent: Opponent strategy (default: optimal)

        Returns:
            Performance metrics
        """
        if opponent is None:
            opponent = self.create_optimal_strategy()

        metrics = SkillEvaluationMetrics()

        # Track action frequencies
        action_counts = dict.fromkeys(BettingAction, 0)

        # Use a consistent seed for benchmarking stability
        import random

        benchmark_rng = random.Random(42)

        for i in range(num_games):
            # Alternate position
            state = {
                "position_on_button": i % 2 == 0,
                "rng": benchmark_rng,
            }
            result = self.play_round(strategy, opponent, state)
            metrics.update_from_result(result)

            # Track actions
            action = result.actual_action
            if action in action_counts:
                action_counts[action] += 1

        # Store action distribution
        total = sum(action_counts.values())
        if total > 0:
            for action, count in action_counts.items():
                metrics.custom_metrics[f"action_{action.value}"] = count / total

        # Poker exploitability is complex, use simplified measure
        # Based on fold frequency (folding too much is exploitable)
        fold_rate = action_counts.get(BettingAction.FOLD, 0) / max(1, total)
        if fold_rate > 0.6:  # Over-folding
            metrics.exploitability = fold_rate - 0.4
        elif fold_rate < 0.1:  # Under-folding
            metrics.exploitability = 0.4 - fold_rate
        else:
            metrics.exploitability = 0.0

        return metrics

    def calculate_exploitability(self, strategy: SkillStrategy) -> float:
        """Calculate exploitability of a poker strategy.

        This is a simplified measure based on observed play patterns.
        True poker exploitability calculation is computationally intensive.

        Args:
            strategy: Strategy to analyze

        Returns:
            Exploitability estimate (0 = balanced, higher = more exploitable)
        """
        metrics = self.observe_strategy(strategy, num_games=200)
        return metrics.exploitability

    def get_difficulty_rating(self) -> float:
        """Poker is the most complex skill game."""
        return 0.9

    def get_evaluation_summary(
        self,
        metrics: SkillEvaluationMetrics,
    ) -> Dict[str, Any]:
        """Get poker-specific evaluation summary."""
        base = super().get_evaluation_summary(metrics)

        # Add action distribution
        actions = {}
        for action in BettingAction:
            key = f"action_{action.value}"
            if key in metrics.custom_metrics:
                actions[action.value] = f"{metrics.custom_metrics[key]:.1%}"

        base["action_distribution"] = actions
        return base
