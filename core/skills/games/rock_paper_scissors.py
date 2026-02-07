"""Rock-Paper-Scissors skill game implementation.

This is an ideal toy problem for testing evolution because:
1. The Nash equilibrium is known exactly: play each action with probability 1/3
2. Any deviation from 1/3-1/3-1/3 can be exploited by a counter-strategy
3. Exploitability can be calculated analytically
4. Simple enough to debug, complex enough to be interesting

Key metrics:
- Optimality Rate: How often does the fish play each action with ~33% probability?
- Exploitability: How much could a perfect exploiter win per game?
- Entropy: How random/predictable is the fish's play?
"""

import math
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


class RPSAction(Enum):
    """Rock-Paper-Scissors actions."""

    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


# Payoff matrix: payoffs[my_action][opponent_action] = my_payoff
RPS_PAYOFFS = {
    RPSAction.ROCK: {
        RPSAction.ROCK: 0,
        RPSAction.PAPER: -1,
        RPSAction.SCISSORS: 1,
    },
    RPSAction.PAPER: {
        RPSAction.ROCK: 1,
        RPSAction.PAPER: 0,
        RPSAction.SCISSORS: -1,
    },
    RPSAction.SCISSORS: {
        RPSAction.ROCK: -1,
        RPSAction.PAPER: 1,
        RPSAction.SCISSORS: 0,
    },
}


@dataclass
class RPSStrategy(SkillStrategy[RPSAction]):
    """Strategy for playing Rock-Paper-Scissors.

    The strategy is defined by probabilities for each action.
    These probabilities can evolve/mutate and be learned from experience.
    """

    # Probabilities for each action (must sum to 1.0)
    prob_rock: float = 0.33
    prob_paper: float = 0.33
    prob_scissors: float = 0.34

    # Learning parameters
    learning_rate: float = 0.1
    memory_length: int = 10  # How many recent opponent actions to remember

    # Opponent modeling (for learning)
    opponent_history: List[RPSAction] = field(default_factory=list)

    # Track own action history for entropy calculation
    own_history: List[RPSAction] = field(default_factory=list)

    def __post_init__(self):
        """Normalize probabilities after initialization."""
        self._normalize_probabilities()

    def _normalize_probabilities(self) -> None:
        """Ensure probabilities sum to 1.0."""
        total = self.prob_rock + self.prob_paper + self.prob_scissors
        if total > 0:
            self.prob_rock /= total
            self.prob_paper /= total
            self.prob_scissors /= total
        else:
            # Reset to uniform if all zero
            self.prob_rock = self.prob_paper = self.prob_scissors = 1.0 / 3.0

    def choose_action(
        self, game_state: Dict[str, Any], rng: Optional[random.Random] = None
    ) -> RPSAction:
        """Choose an action based on current probabilities.

        Args:
            game_state: Optional state (not used in basic RPS)
            rng: Optional random number generator for determinism

        Returns:
            The chosen action
        """
        _rng = rng if rng is not None else random.Random()
        r = _rng.random()
        if r < self.prob_rock:
            action = RPSAction.ROCK
        elif r < self.prob_rock + self.prob_paper:
            action = RPSAction.PAPER
        else:
            action = RPSAction.SCISSORS

        # Track own history
        self.own_history.append(action)
        if len(self.own_history) > 100:
            self.own_history = self.own_history[-100:]

        return action

    def learn_from_result(self, result: SkillGameResult) -> None:
        """Update strategy based on game outcome.

        This implements a simple learning rule:
        - If we won, slightly increase the probability of that action
        - If we lost, slightly decrease it and increase the counter
        - Over time this should converge toward exploiting predictable opponents

        Args:
            result: The game result
        """
        opponent_action = result.details.get("opponent_action")
        my_action = result.actual_action
        if not isinstance(opponent_action, RPSAction) or not isinstance(my_action, RPSAction):
            return

        # Track opponent history
        self.opponent_history.append(opponent_action)
        if len(self.opponent_history) > self.memory_length:
            self.opponent_history = self.opponent_history[-self.memory_length :]

        # Simple reinforcement learning
        if result.won:
            # Reinforce winning action slightly
            self._adjust_probability(my_action, self.learning_rate * 0.5)
        elif not result.tied:
            # Reduce losing action, increase counter
            self._adjust_probability(my_action, -self.learning_rate * 0.3)
            counter = self._get_counter(opponent_action)
            self._adjust_probability(counter, self.learning_rate * 0.2)

        self._normalize_probabilities()

    def _get_counter(self, action: RPSAction) -> RPSAction:
        """Get the action that beats the given action."""
        if action == RPSAction.ROCK:
            return RPSAction.PAPER
        elif action == RPSAction.PAPER:
            return RPSAction.SCISSORS
        else:
            return RPSAction.ROCK

    def _adjust_probability(self, action: RPSAction, delta: float) -> None:
        """Adjust the probability of an action."""
        if action == RPSAction.ROCK:
            self.prob_rock = max(0.01, min(0.98, self.prob_rock + delta))
        elif action == RPSAction.PAPER:
            self.prob_paper = max(0.01, min(0.98, self.prob_paper + delta))
        else:
            self.prob_scissors = max(0.01, min(0.98, self.prob_scissors + delta))

    def get_parameters(self) -> Dict[str, float]:
        """Get strategy parameters for inheritance."""
        return {
            "prob_rock": self.prob_rock,
            "prob_paper": self.prob_paper,
            "prob_scissors": self.prob_scissors,
            "learning_rate": self.learning_rate,
        }

    def set_parameters(self, params: Dict[str, float]) -> None:
        """Set strategy parameters."""
        self.prob_rock = params.get("prob_rock", 0.33)
        self.prob_paper = params.get("prob_paper", 0.33)
        self.prob_scissors = params.get("prob_scissors", 0.34)
        self.learning_rate = params.get("learning_rate", 0.1)
        self._normalize_probabilities()

    def get_action_distribution(self) -> Dict[str, float]:
        """Get the probability distribution over actions."""
        return {
            "rock": self.prob_rock,
            "paper": self.prob_paper,
            "scissors": self.prob_scissors,
        }

    def calculate_entropy(self) -> float:
        """Calculate the entropy of the strategy.

        Higher entropy = more random (optimal is max entropy).
        Max entropy for 3 actions = log(3) = ~1.099

        Returns:
            Entropy in nats (natural log)
        """
        entropy = 0.0
        for p in [self.prob_rock, self.prob_paper, self.prob_scissors]:
            if p > 0:
                entropy -= p * math.log(p)
        return entropy

    def calculate_empirical_entropy(self) -> float:
        """Calculate entropy from actual play history.

        This measures how random the fish actually plays, not just
        what their probabilities say.

        Returns:
            Empirical entropy from recent play
        """
        if len(self.own_history) < 10:
            return self.calculate_entropy()  # Not enough data

        counts = {RPSAction.ROCK: 0, RPSAction.PAPER: 0, RPSAction.SCISSORS: 0}
        for action in self.own_history[-100:]:  # Last 100 actions
            counts[action] += 1

        total = sum(counts.values())
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log(p)
        return entropy


class OptimalRPSStrategy(RPSStrategy):
    """The Nash equilibrium strategy for RPS: uniform random.

    This strategy is unexploitable - any opponent will win exactly 1/3,
    lose 1/3, and tie 1/3 against it in the long run.
    """

    def __init__(self):
        super().__init__(
            prob_rock=1.0 / 3.0,
            prob_paper=1.0 / 3.0,
            prob_scissors=1.0 / 3.0,
            learning_rate=0.0,  # Optimal doesn't need to learn
        )

    def learn_from_result(self, result: SkillGameResult) -> None:
        """Optimal strategy doesn't change."""
        pass

    def set_parameters(self, params: Dict[str, float]) -> None:
        """Optimal strategy ignores parameter changes."""
        pass


class ExploitingRPSStrategy(RPSStrategy):
    """A strategy that tries to exploit non-uniform opponents.

    This strategy counts opponent's action frequencies and plays
    the counter to their most common action.
    """

    def choose_action(
        self, game_state: Dict[str, Any], rng: Optional[random.Random] = None
    ) -> RPSAction:
        """Choose the counter to opponent's most frequent action."""
        if len(self.opponent_history) < 5:
            # Not enough data, play randomly
            return super().choose_action(game_state, rng=rng)

        # Count opponent actions in recent history
        counts = {RPSAction.ROCK: 0, RPSAction.PAPER: 0, RPSAction.SCISSORS: 0}
        for action in self.opponent_history[-20:]:
            counts[action] += 1

        # Find most common and play counter
        most_common = max(counts, key=counts.__getitem__)
        action = self._get_counter(most_common)

        self.own_history.append(action)
        return action


class RockPaperScissorsGame(SkillGame):
    """Rock-Paper-Scissors implementation of SkillGame.

    This is the simplest non-trivial game for testing skill evolution.
    The optimal strategy (Nash equilibrium) is to play each action
    with equal probability (1/3 each).
    """

    # Energy/score stakes for each game
    stake: float = 10.0

    def __init__(self, stake: float = 10.0, rng: Optional[random.Random] = None):
        """Initialize the game with configurable stakes.

        Args:
            stake: Energy at stake per game (winner gets this much)
            rng: Optional RNG for deterministic play (stored but not used in this simple game)
        """
        self.stake = stake
        self._rng = rng  # Store for potential future use

    @property
    def game_type(self) -> SkillGameType:
        return SkillGameType.ROCK_PAPER_SCISSORS

    @property
    def name(self) -> str:
        return "Rock-Paper-Scissors"

    @property
    def description(self) -> str:
        return (
            "Classic Rock-Paper-Scissors. Rock beats Scissors, "
            "Scissors beats Paper, Paper beats Rock. "
            "Optimal play is uniform random (1/3 each action)."
        )

    @property
    def is_zero_sum(self) -> bool:
        return True

    @property
    def has_optimal_strategy(self) -> bool:
        return True

    @property
    def optimal_strategy_description(self) -> str:
        return (
            "Nash equilibrium: Play Rock, Paper, and Scissors each with "
            "probability 1/3. This strategy is unexploitable - no opponent "
            "can achieve better than 0 expected value against it."
        )

    def create_default_strategy(self, rng: Optional[random.Random] = None) -> RPSStrategy:
        """Create a new strategy with slight random bias.

        Fish start with slightly non-optimal strategies so evolution
        can improve them toward the Nash equilibrium.

        Args:
            rng: Optional random number generator for determinism
        """
        _rng = rng if rng is not None else random.Random()
        # Add some randomness to starting probabilities
        r = _rng.random() * 0.3 + 0.2  # 0.2 to 0.5
        p = _rng.random() * 0.3 + 0.2
        s = 1.0 - r - p

        return RPSStrategy(
            prob_rock=max(0.1, r),
            prob_paper=max(0.1, p),
            prob_scissors=max(0.1, s),
            learning_rate=_rng.uniform(0.05, 0.2),
        )

    def create_optimal_strategy(self) -> OptimalRPSStrategy:
        """Create the Nash equilibrium strategy."""
        return OptimalRPSStrategy()

    def create_exploiting_strategy(self) -> ExploitingRPSStrategy:
        """Create a strategy that exploits predictable opponents."""
        return ExploitingRPSStrategy()

    def play_round(
        self,
        player_strategy: SkillStrategy,
        opponent_strategy: Optional[SkillStrategy] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> SkillGameResult:
        """Play one round of Rock-Paper-Scissors.

        Args:
            player_strategy: The player's strategy
            opponent_strategy: The opponent's strategy (default: optimal)
            game_state: Not used for RPS

        Returns:
            Game result with detailed metrics
        """
        if opponent_strategy is None:
            opponent_strategy = self.create_optimal_strategy()

        state = game_state or {}
        player_action = player_strategy.choose_action(state)
        opponent_action = opponent_strategy.choose_action(state)

        # Determine outcome
        payoff = RPS_PAYOFFS[player_action][opponent_action]
        won = payoff > 0
        tied = payoff == 0

        # Optimal action against a random opponent is any action
        # But we track if player's distribution is close to optimal
        if isinstance(player_strategy, RPSStrategy):
            dist = player_strategy.get_action_distribution()
            # Check if probabilities are close to 1/3
            max_deviation = max(abs(p - 1 / 3) for p in dist.values())
            was_optimal = max_deviation < 0.05  # Within 5% of uniform
        else:
            was_optimal = False

        result = SkillGameResult(
            player_id=state.get("player_id", "player"),
            opponent_id=state.get("opponent_id", "opponent"),
            won=won,
            tied=tied,
            score_change=payoff * self.stake,
            optimal_action=None,  # In RPS, no single action is "optimal"
            actual_action=player_action,
            was_optimal=was_optimal,
            details={
                "player_action": player_action,
                "opponent_action": opponent_action,
                "payoff": payoff,
            },
        )

        return result

    def observe_strategy(
        self,
        strategy: SkillStrategy,
        num_games: int = 1000,
        opponent: Optional[SkillStrategy] = None,
    ) -> SkillEvaluationMetrics:
        """Observe a strategy's performance for reporting.

        This is for OBSERVATION ONLY - helps us understand what strategies
        are emerging. Does NOT drive selection (that's via energy flow).

        Args:
            strategy: Strategy to observe
            num_games: Number of games to play
            opponent: Opponent (default: optimal strategy)

        Returns:
            Observational metrics for reporting
        """
        if opponent is None:
            opponent = self.create_optimal_strategy()

        metrics = SkillEvaluationMetrics()

        # Track action frequencies for entropy/exploitability
        action_counts = {RPSAction.ROCK: 0, RPSAction.PAPER: 0, RPSAction.SCISSORS: 0}

        for i in range(num_games):
            result = self.play_round(strategy, opponent)
            metrics.update_from_result(result)

            # Track action distribution
            action = result.actual_action
            if action in action_counts:
                action_counts[action] += 1

        # Calculate exploitability from observed distribution
        total_actions = sum(action_counts.values())
        if total_actions > 0:
            probs = {a: c / total_actions for a, c in action_counts.items()}
            metrics.exploitability = self._calculate_exploitability_from_probs(probs)
            metrics.distance_from_optimal = self._calculate_distance_from_optimal(probs)

            # Calculate empirical entropy
            entropy = 0.0
            for p in probs.values():
                if p > 0:
                    entropy -= p * math.log(p)
            metrics.custom_metrics["entropy"] = entropy
            metrics.custom_metrics["max_entropy"] = math.log(3)  # ~1.099
            metrics.custom_metrics["entropy_ratio"] = entropy / math.log(3)

        # Store action distribution
        metrics.custom_metrics["prob_rock"] = action_counts[RPSAction.ROCK] / max(1, total_actions)
        metrics.custom_metrics["prob_paper"] = action_counts[RPSAction.PAPER] / max(
            1, total_actions
        )
        metrics.custom_metrics["prob_scissors"] = action_counts[RPSAction.SCISSORS] / max(
            1, total_actions
        )

        return metrics

    def _calculate_exploitability_from_probs(self, probs: Dict[RPSAction, float]) -> float:
        """Calculate how exploitable a strategy is.

        For RPS, exploitability = max expected value an exploiter can achieve.
        Against uniform random, this is 0.
        Against a biased strategy, an exploiter can win by playing the counter
        to the most likely action.

        Args:
            probs: Probability distribution over actions

        Returns:
            Exploitability (0 = unexploitable, up to ~0.67 for extreme bias)
        """
        # Find the most likely action
        p_rock = probs.get(RPSAction.ROCK, 1 / 3)
        p_paper = probs.get(RPSAction.PAPER, 1 / 3)
        p_scissors = probs.get(RPSAction.SCISSORS, 1 / 3)

        # Exploiter plays the counter to most common action
        # Expected value of playing Paper (beats Rock, loses to Scissors):
        ev_paper = p_rock * 1 + p_paper * 0 + p_scissors * (-1)
        # Expected value of playing Scissors:
        ev_scissors = p_rock * (-1) + p_paper * 1 + p_scissors * 0
        # Expected value of playing Rock:
        ev_rock = p_rock * 0 + p_paper * (-1) + p_scissors * 1

        # Exploitability is the max EV the exploiter can achieve
        max_ev = max(ev_rock, ev_paper, ev_scissors)
        return max(0.0, max_ev)  # Clamp to non-negative

    def _calculate_distance_from_optimal(self, probs: Dict[RPSAction, float]) -> float:
        """Calculate distance from optimal strategy.

        Uses total variation distance from uniform distribution.
        0 = optimal, 1 = maximally far from optimal.

        Args:
            probs: Probability distribution over actions

        Returns:
            Distance from optimal (0-1)
        """
        optimal_prob = 1.0 / 3.0
        total_variation = 0.0
        for action in RPSAction:
            total_variation += abs(probs.get(action, 0) - optimal_prob)
        # Normalize to [0, 1] (max TV is 4/3 for 3 actions)
        return total_variation / (4 / 3)

    def calculate_exploitability(self, strategy: SkillStrategy) -> float:
        """Calculate exploitability by analyzing strategy's action distribution.

        This is an observational metric - tells us how exploitable a strategy
        is by a perfect counter-player. Lower = better (0 = Nash equilibrium).

        Args:
            strategy: The strategy to analyze

        Returns:
            Exploitability score (0 = unexploitable)
        """
        if isinstance(strategy, RPSStrategy):
            probs = strategy.get_action_distribution()
            return self._calculate_exploitability_from_probs(
                {RPSAction[k.upper()]: v for k, v in probs.items()}
            )
        else:
            # Play many games to estimate distribution
            metrics = self.observe_strategy(strategy, num_games=500)
            return metrics.exploitability

    def get_difficulty_rating(self) -> float:
        """RPS is a simple game."""
        return 0.2

    def get_evaluation_summary(self, metrics: SkillEvaluationMetrics) -> Dict[str, Any]:
        """Get RPS-specific evaluation summary."""
        base = super().get_evaluation_summary(metrics)
        base.update(
            {
                "entropy_ratio": f"{metrics.custom_metrics.get('entropy_ratio', 0):.1%}",
                "action_distribution": {
                    "rock": f"{metrics.custom_metrics.get('prob_rock', 0):.1%}",
                    "paper": f"{metrics.custom_metrics.get('prob_paper', 0):.1%}",
                    "scissors": f"{metrics.custom_metrics.get('prob_scissors', 0):.1%}",
                },
            }
        )
        return base
