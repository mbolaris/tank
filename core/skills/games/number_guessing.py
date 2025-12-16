"""Number Prediction skill game implementation.

This is a skill-based game where fish must predict values based on patterns.
Unlike pure random guessing, this game rewards:
1. Pattern recognition (detecting sequences, trends)
2. Memory (remembering past observations)
3. Adaptation (adjusting strategy when patterns change)

The game works as follows:
- A "target generator" produces values following hidden patterns
- Fish observe a history of recent values
- Fish predict the next value
- Closer predictions win more energy

Patterns include:
- Simple sequences (counting up/down)
- Alternating patterns (high/low)
- Cycles (repeating sequences)
- Trends with noise
- Mean-reverting values

The optimal strategy depends on the pattern - fish must learn to identify
which pattern is active and predict accordingly.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.skills.base import (
    SkillEvaluationMetrics,
    SkillGame,
    SkillGameResult,
    SkillGameType,
    SkillStrategy,
)


class PatternType(Enum):
    """Types of patterns the generator can produce."""

    CONSTANT = "constant"  # Same value repeatedly
    LINEAR_UP = "linear_up"  # Increasing sequence
    LINEAR_DOWN = "linear_down"  # Decreasing sequence
    ALTERNATING = "alternating"  # High/low/high/low
    CYCLE = "cycle"  # Repeating sequence
    MEAN_REVERTING = "mean_reverting"  # Tends toward a mean
    RANDOM_WALK = "random_walk"  # Random but continuous changes


@dataclass
class PatternGenerator:
    """Generates values following a hidden pattern.

    Fish must learn to identify the pattern from observations.
    """

    pattern_type: PatternType = PatternType.ALTERNATING
    value_range: tuple = (0.0, 100.0)  # Min and max values
    noise_level: float = 0.1  # How much noise to add (0-1)

    # Internal state
    _current_value: float = 50.0
    _step: int = 0
    _cycle: List[float] = field(default_factory=lambda: [25.0, 75.0, 50.0])
    _mean: float = 50.0

    def reset(self, pattern_type: Optional[PatternType] = None) -> None:
        """Reset the generator, optionally with a new pattern."""
        if pattern_type is not None:
            self.pattern_type = pattern_type
        self._current_value = (self.value_range[0] + self.value_range[1]) / 2
        self._step = 0

    def generate_next(self) -> float:
        """Generate the next value in the pattern."""
        self._step += 1
        min_val, max_val = self.value_range
        range_size = max_val - min_val

        if self.pattern_type == PatternType.CONSTANT:
            base_value = self._mean

        elif self.pattern_type == PatternType.LINEAR_UP:
            # Increase by 5% of range each step, wrap around
            base_value = min_val + ((self._step * 0.05 * range_size) % range_size)

        elif self.pattern_type == PatternType.LINEAR_DOWN:
            base_value = max_val - ((self._step * 0.05 * range_size) % range_size)

        elif self.pattern_type == PatternType.ALTERNATING:
            # Switch between 25% and 75% of range
            if self._step % 2 == 0:
                base_value = min_val + 0.25 * range_size
            else:
                base_value = min_val + 0.75 * range_size

        elif self.pattern_type == PatternType.CYCLE:
            # Cycle through predefined values
            idx = self._step % len(self._cycle)
            base_value = self._cycle[idx]

        elif self.pattern_type == PatternType.MEAN_REVERTING:
            # Move toward mean with some momentum
            diff = self._mean - self._current_value
            self._current_value += diff * 0.3 + random.gauss(0, range_size * 0.1)
            base_value = self._current_value

        elif self.pattern_type == PatternType.RANDOM_WALK:
            # Random walk with drift back to center
            drift = (self._mean - self._current_value) * 0.05
            self._current_value += drift + random.gauss(0, range_size * 0.1)
            base_value = self._current_value

        else:
            base_value = self._mean

        # Add noise
        if self.noise_level > 0:
            noise = random.gauss(0, self.noise_level * range_size * 0.2)
            base_value += noise

        # Clamp to range
        self._current_value = max(min_val, min(max_val, base_value))
        return self._current_value

    def get_optimal_prediction(self, history: List[float]) -> float:
        """Get the optimal prediction given the pattern type and history.

        This is what a perfect predictor would guess.
        """
        min_val, max_val = self.value_range
        range_size = max_val - min_val

        if self.pattern_type == PatternType.CONSTANT:
            return self._mean

        elif self.pattern_type == PatternType.LINEAR_UP:
            if len(history) >= 2:
                return history[-1] + (history[-1] - history[-2])
            return history[-1] + 0.05 * range_size if history else self._mean

        elif self.pattern_type == PatternType.LINEAR_DOWN:
            if len(history) >= 2:
                return history[-1] + (history[-1] - history[-2])
            return history[-1] - 0.05 * range_size if history else self._mean

        elif self.pattern_type == PatternType.ALTERNATING:
            if history:
                # Predict opposite of last value
                last = history[-1]
                mid = (min_val + max_val) / 2
                if last > mid:
                    return min_val + 0.25 * range_size
                else:
                    return min_val + 0.75 * range_size
            return self._mean

        elif self.pattern_type == PatternType.CYCLE:
            if len(history) >= len(self._cycle):
                # Try to detect cycle position
                for start in range(len(self._cycle)):
                    match = True
                    for i, val in enumerate(self._cycle):
                        hist_idx = -(len(self._cycle) - i)
                        if abs(history[hist_idx] - val) > range_size * 0.2:
                            match = False
                            break
                    if match:
                        return self._cycle[start]
            return self._mean

        elif self.pattern_type == PatternType.MEAN_REVERTING:
            if history:
                # Predict movement toward mean
                diff = self._mean - history[-1]
                return history[-1] + diff * 0.3
            return self._mean

        elif self.pattern_type == PatternType.RANDOM_WALK:
            # Best prediction is last value (random walk has no predictable direction)
            return history[-1] if history else self._mean

        return self._mean


@dataclass
class NumberGuessingStrategy(SkillStrategy[float]):
    """Strategy for the Number Prediction game.

    The strategy learns to identify patterns and predict accordingly.
    Parameters control how much weight is given to different prediction methods.
    """

    # Weights for different prediction strategies (will be normalized)
    weight_last_value: float = 0.3  # Predict same as last
    weight_trend: float = 0.3  # Extrapolate trend
    weight_mean: float = 0.2  # Predict mean of history
    weight_alternating: float = 0.2  # Predict opposite of last

    # Learning parameters
    learning_rate: float = 0.1
    memory_length: int = 10

    # Internal state
    _history: List[float] = field(default_factory=list)
    _prediction_errors: Dict[str, List[float]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize prediction error tracking."""
        self._prediction_errors = {
            "last_value": [],
            "trend": [],
            "mean": [],
            "alternating": [],
        }

    def choose_action(self, game_state: Dict[str, Any]) -> float:
        """Predict the next value based on observed history.

        Args:
            game_state: Contains "history" - list of recent values

        Returns:
            Predicted value
        """
        history = game_state.get("history", [])
        value_range = game_state.get("value_range", (0.0, 100.0))
        min_val, max_val = value_range

        if not history:
            return (min_val + max_val) / 2  # No data, guess middle

        # Calculate predictions from different methods
        predictions = {}

        # 1. Predict same as last value
        predictions["last_value"] = history[-1]

        # 2. Extrapolate trend
        if len(history) >= 2:
            trend = history[-1] - history[-2]
            predictions["trend"] = history[-1] + trend
        else:
            predictions["trend"] = history[-1]

        # 3. Predict mean of history
        predictions["mean"] = sum(history) / len(history)

        # 4. Predict alternating (opposite of last)
        mid = (min_val + max_val) / 2
        if history[-1] > mid:
            predictions["alternating"] = mid - (history[-1] - mid)
        else:
            predictions["alternating"] = mid + (mid - history[-1])

        # Weight predictions based on recent accuracy
        weights = {
            "last_value": self.weight_last_value,
            "trend": self.weight_trend,
            "mean": self.weight_mean,
            "alternating": self.weight_alternating,
        }

        # Adjust weights based on prediction error history
        for method, errors in self._prediction_errors.items():
            if len(errors) >= 3:
                avg_error = sum(errors[-5:]) / len(errors[-5:])
                # Lower error = higher weight
                weights[method] *= max(0.1, 1.0 - avg_error / (max_val - min_val))

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # Weighted average prediction
        prediction = sum(predictions[m] * weights[m] for m in predictions)

        # Clamp to valid range
        return max(min_val, min(max_val, prediction))

    def learn_from_result(self, result: SkillGameResult) -> None:
        """Update strategy based on prediction outcome.

        Args:
            result: Contains the actual value and prediction error
        """
        details = result.details
        actual = details.get("actual_value")
        history = details.get("history_before", [])

        if actual is None or not history:
            return

        value_range = details.get("value_range", (0.0, 100.0))
        min_val, max_val = value_range

        # Calculate what each method would have predicted
        predictions = {}
        predictions["last_value"] = history[-1] if history else actual

        if len(history) >= 2:
            predictions["trend"] = history[-1] + (history[-1] - history[-2])
        else:
            predictions["trend"] = history[-1] if history else actual

        predictions["mean"] = sum(history) / len(history) if history else actual

        mid = (min_val + max_val) / 2
        if history and history[-1] > mid:
            predictions["alternating"] = mid - (history[-1] - mid)
        elif history:
            predictions["alternating"] = mid + (mid - history[-1])
        else:
            predictions["alternating"] = mid

        # Track errors for each method
        for method, pred in predictions.items():
            error = abs(pred - actual)
            self._prediction_errors[method].append(error)
            if len(self._prediction_errors[method]) > 20:
                self._prediction_errors[method] = self._prediction_errors[method][-20:]

        # Reinforce weights based on which method was best
        errors = {m: abs(predictions[m] - actual) for m in predictions}
        best_method = min(errors, key=errors.get)

        # Increase weight for best method, decrease others
        for method in ["last_value", "trend", "mean", "alternating"]:
            weight_attr = f"weight_{method}"
            current = getattr(self, weight_attr)
            if method == best_method:
                setattr(self, weight_attr, min(0.8, current + self.learning_rate))
            else:
                setattr(self, weight_attr, max(0.05, current - self.learning_rate * 0.3))

        # Normalize weights
        total = (
            self.weight_last_value
            + self.weight_trend
            + self.weight_mean
            + self.weight_alternating
        )
        if total > 0:
            self.weight_last_value /= total
            self.weight_trend /= total
            self.weight_mean /= total
            self.weight_alternating /= total

    def get_parameters(self) -> Dict[str, float]:
        """Get strategy parameters for inheritance."""
        return {
            "weight_last_value": self.weight_last_value,
            "weight_trend": self.weight_trend,
            "weight_mean": self.weight_mean,
            "weight_alternating": self.weight_alternating,
            "learning_rate": self.learning_rate,
        }

    def set_parameters(self, params: Dict[str, float]) -> None:
        """Set strategy parameters."""
        self.weight_last_value = params.get("weight_last_value", 0.25)
        self.weight_trend = params.get("weight_trend", 0.25)
        self.weight_mean = params.get("weight_mean", 0.25)
        self.weight_alternating = params.get("weight_alternating", 0.25)
        self.learning_rate = params.get("learning_rate", 0.1)


@dataclass
class OptimalNumberGuessingStrategy(NumberGuessingStrategy):
    """Optimal strategy that knows the true pattern.

    Used as a benchmark for observation purposes.
    """

    _generator: Optional[PatternGenerator] = None

    def set_generator(self, generator: PatternGenerator) -> None:
        """Set the pattern generator for optimal predictions."""
        self._generator = generator

    def choose_action(self, game_state: Dict[str, Any]) -> float:
        """Make optimal prediction using knowledge of pattern."""
        history = game_state.get("history", [])

        if self._generator is not None:
            return self._generator.get_optimal_prediction(history)

        # Fallback to adaptive strategy if no generator set
        return super().choose_action(game_state)


class NumberGuessingGame(SkillGame):
    """Number Prediction implementation of SkillGame.

    Fish predict values based on observed patterns. This tests:
    - Pattern recognition skill
    - Memory and learning
    - Adaptation to changing patterns

    The game naturally selects for fish that are good at:
    - Detecting trends and cycles
    - Remembering past observations
    - Quickly adapting when patterns change
    """

    def __init__(
        self,
        stake: float = 10.0,
        max_error_for_reward: float = 20.0,
        history_length: int = 5,
        pattern_type: PatternType = PatternType.ALTERNATING,
        pattern_change_frequency: int = 50,  # Change pattern every N rounds
    ):
        """Initialize the game.

        Args:
            stake: Maximum energy at stake per game
            max_error_for_reward: Error above this gets no reward
            history_length: How many past values fish can observe
            pattern_type: Initial pattern type
            pattern_change_frequency: How often the pattern changes (0 = never)
        """
        self.stake = stake
        self.max_error_for_reward = max_error_for_reward
        self.history_length = history_length
        self.pattern_change_frequency = pattern_change_frequency

        self.generator = PatternGenerator(pattern_type=pattern_type)
        self._history: List[float] = []
        self._rounds_played = 0

    @property
    def game_type(self) -> SkillGameType:
        return SkillGameType.NUMBER_GUESSING

    @property
    def name(self) -> str:
        return "Number Prediction"

    @property
    def description(self) -> str:
        return (
            "Fish observe a sequence of values and predict the next one. "
            "Values follow hidden patterns (trends, cycles, alternating). "
            "Closer predictions win more energy. Tests pattern recognition "
            "and adaptation skills."
        )

    @property
    def is_zero_sum(self) -> bool:
        return False  # Single player game, energy comes from environment

    @property
    def has_optimal_strategy(self) -> bool:
        return True  # Optimal is to correctly identify and predict the pattern

    @property
    def optimal_strategy_description(self) -> str:
        return (
            "Identify the active pattern (trend, cycle, alternating, etc.) "
            "from recent observations and predict accordingly. The optimal "
            "predictor has perfect pattern recognition."
        )

    def create_default_strategy(self) -> NumberGuessingStrategy:
        """Create a new strategy with random initial weights."""
        weights = [random.random() for _ in range(4)]
        total = sum(weights)
        weights = [w / total for w in weights]

        return NumberGuessingStrategy(
            weight_last_value=weights[0],
            weight_trend=weights[1],
            weight_mean=weights[2],
            weight_alternating=weights[3],
            learning_rate=random.uniform(0.05, 0.2),
        )

    def create_optimal_strategy(self) -> OptimalNumberGuessingStrategy:
        """Create optimal strategy with access to generator."""
        strategy = OptimalNumberGuessingStrategy()
        strategy.set_generator(self.generator)
        return strategy

    def _maybe_change_pattern(self) -> None:
        """Possibly change the pattern to test adaptation."""
        if self.pattern_change_frequency <= 0:
            return

        if self._rounds_played > 0 and self._rounds_played % self.pattern_change_frequency == 0:
            patterns = list(PatternType)
            new_pattern = random.choice(patterns)
            self.generator.reset(new_pattern)

    def play_round(
        self,
        player_strategy: SkillStrategy,
        opponent_strategy: Optional[SkillStrategy] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> SkillGameResult:
        """Play one round of the prediction game.

        Args:
            player_strategy: The player's strategy
            opponent_strategy: Not used (single player game)
            game_state: Optional override for history

        Returns:
            Game result with prediction accuracy metrics
        """
        self._rounds_played += 1
        self._maybe_change_pattern()

        # Get history for player to observe
        history = list(self._history[-self.history_length :])

        # Generate the actual next value
        actual_value = self.generator.generate_next()

        # Get player's prediction
        state = {
            "history": history,
            "value_range": self.generator.value_range,
            "player_id": game_state.get("player_id", "player") if game_state else "player",
        }
        prediction = player_strategy.choose_action(state)

        # Calculate error and reward
        error = abs(prediction - actual_value)
        relative_error = error / (self.generator.value_range[1] - self.generator.value_range[0])

        # Reward decreases linearly with error, zero if error > max
        if error <= self.max_error_for_reward:
            reward_ratio = 1.0 - (error / self.max_error_for_reward)
            score_change = self.stake * reward_ratio
            won = score_change > self.stake * 0.5
        else:
            score_change = -self.stake * 0.2  # Small penalty for very bad predictions
            won = False

        # Get optimal prediction for comparison
        optimal_prediction = self.generator.get_optimal_prediction(history)
        optimal_error = abs(optimal_prediction - actual_value)
        was_optimal = error <= optimal_error + 1.0  # Within 1 unit of optimal

        # Update history
        self._history.append(actual_value)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        result = SkillGameResult(
            player_id=state["player_id"],
            opponent_id=None,
            won=won,
            tied=False,
            score_change=score_change,
            optimal_action=optimal_prediction,
            actual_action=prediction,
            was_optimal=was_optimal,
            details={
                "actual_value": actual_value,
                "prediction": prediction,
                "error": error,
                "relative_error": relative_error,
                "optimal_prediction": optimal_prediction,
                "optimal_error": optimal_error,
                "pattern_type": self.generator.pattern_type.value,
                "history_before": history,
                "value_range": self.generator.value_range,
            },
        )

        return result

    def observe_strategy(
        self,
        strategy: SkillStrategy,
        num_games: int = 1000,
        opponent: Optional[SkillStrategy] = None,
    ) -> SkillEvaluationMetrics:
        """Observe a strategy's prediction performance.

        Args:
            strategy: Strategy to observe
            num_games: Number of rounds to play
            opponent: Not used (single player)

        Returns:
            Observational metrics
        """
        metrics = SkillEvaluationMetrics()

        total_error = 0.0
        optimal_total_error = 0.0
        pattern_scores: Dict[str, List[float]] = {}

        for _ in range(num_games):
            result = self.play_round(strategy)
            metrics.update_from_result(result)

            error = result.details["error"]
            optimal_error = result.details["optimal_error"]
            pattern = result.details["pattern_type"]

            total_error += error
            optimal_total_error += optimal_error

            if pattern not in pattern_scores:
                pattern_scores[pattern] = []
            pattern_scores[pattern].append(result.score_change)

        # Calculate summary metrics
        avg_error = total_error / num_games
        avg_optimal_error = optimal_total_error / num_games

        # Distance from optimal: how much worse than optimal predictor
        if avg_optimal_error > 0:
            metrics.distance_from_optimal = (avg_error - avg_optimal_error) / avg_optimal_error
        else:
            metrics.distance_from_optimal = avg_error / self.max_error_for_reward

        metrics.distance_from_optimal = max(0, min(1, metrics.distance_from_optimal))

        # Custom metrics
        metrics.custom_metrics["avg_error"] = avg_error
        metrics.custom_metrics["avg_optimal_error"] = avg_optimal_error
        metrics.custom_metrics["error_ratio"] = avg_error / max(0.01, avg_optimal_error)

        # Per-pattern performance
        for pattern, scores in pattern_scores.items():
            if scores:
                metrics.custom_metrics[f"avg_score_{pattern}"] = sum(scores) / len(scores)

        return metrics

    def calculate_exploitability(self, strategy: SkillStrategy) -> float:
        """Calculate how far from optimal the strategy is.

        For single-player games, this measures skill gap from optimal.
        """
        metrics = self.observe_strategy(strategy, num_games=200)
        return metrics.distance_from_optimal

    def get_difficulty_rating(self) -> float:
        """Number prediction is moderately difficult."""
        return 0.4

    def get_evaluation_summary(
        self, metrics: SkillEvaluationMetrics
    ) -> Dict[str, Any]:
        """Get prediction-specific evaluation summary."""
        base = super().get_evaluation_summary(metrics)
        base.update(
            {
                "avg_error": f"{metrics.custom_metrics.get('avg_error', 0):.2f}",
                "error_ratio_vs_optimal": f"{metrics.custom_metrics.get('error_ratio', 0):.2f}x",
            }
        )
        return base
