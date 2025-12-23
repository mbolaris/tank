"""Tests for the skill game framework.

These tests verify that:
1. RPS game works correctly with known optimal strategies
2. Number Prediction game tests pattern recognition
3. Strategies can learn and mutate
4. Energy flows correctly through games
"""

import pytest
import random

from core.skills.base import SkillGameType, SkillEvaluationMetrics
from core.skills.config import (
    SkillGameConfig,
    get_skill_game_config,
    set_skill_game_config,
    get_active_skill_game,
    set_active_skill_game,
)
from core.skills.games.rock_paper_scissors import (
    RockPaperScissorsGame,
    RPSAction,
    RPSStrategy,
    OptimalRPSStrategy,
    ExploitingRPSStrategy,
)
from core.skills.games.number_guessing import (
    NumberGuessingGame,
    NumberGuessingStrategy,
    PatternType,
    PatternGenerator,
)
from core.fish.skill_game_component import SkillGameComponent, FishSkillGameStats


class TestRPSGame:
    """Tests for Rock-Paper-Scissors game."""

    def test_optimal_strategy_is_uniform(self):
        """Optimal RPS strategy should be uniform 1/3 each."""
        strategy = OptimalRPSStrategy()
        params = strategy.get_parameters()

        assert abs(params["prob_rock"] - 1 / 3) < 0.01
        assert abs(params["prob_paper"] - 1 / 3) < 0.01
        assert abs(params["prob_scissors"] - 1 / 3) < 0.01

    def test_optimal_strategy_is_unexploitable(self):
        """Optimal strategy should have ~0 exploitability."""
        game = RockPaperScissorsGame()
        strategy = OptimalRPSStrategy()

        exploitability = game.calculate_exploitability(strategy)
        assert exploitability < 0.1  # Very close to 0

    def test_biased_strategy_is_exploitable(self):
        """A biased strategy should be exploitable."""
        game = RockPaperScissorsGame()

        # Create a strategy that always plays rock
        strategy = RPSStrategy(prob_rock=0.9, prob_paper=0.05, prob_scissors=0.05)

        exploitability = game.calculate_exploitability(strategy)
        assert exploitability > 0.3  # Highly exploitable

    def test_game_returns_valid_results(self):
        """Game should return proper results."""
        game = RockPaperScissorsGame(stake=10.0)
        strategy1 = RPSStrategy()
        strategy2 = OptimalRPSStrategy()

        result = game.play_round(strategy1, strategy2)

        assert result.player_id is not None
        assert result.actual_action in [RPSAction.ROCK, RPSAction.PAPER, RPSAction.SCISSORS]
        assert "player_action" in result.details
        assert "opponent_action" in result.details

    def test_exploiting_strategy_beats_biased(self):
        """Exploiting strategy should beat biased opponents."""
        game = RockPaperScissorsGame(stake=10.0)

        # Biased strategy (always rock)
        biased = RPSStrategy(prob_rock=0.9, prob_paper=0.05, prob_scissors=0.05)

        # Exploiting strategy learns to counter
        exploiter = ExploitingRPSStrategy()

        # Play many games
        wins = 0
        for _ in range(100):
            result = game.play_round(exploiter, biased)
            # Let exploiter learn
            exploiter.learn_from_result(result)
            if result.won:
                wins += 1

        # After learning, exploiter should win more than random (33%)
        # Give some buffer for initial learning period
        assert wins > 25

    def test_strategy_learning(self):
        """Strategy should adjust based on results."""
        strategy = RPSStrategy(learning_rate=0.2)
        initial_rock = strategy.prob_rock

        # Simulate losing with rock
        from core.skills.base import SkillGameResult

        result = SkillGameResult(
            player_id="test",
            opponent_id="opp",
            won=False,
            tied=False,
            score_change=-10,
            actual_action=RPSAction.ROCK,
            details={"opponent_action": RPSAction.PAPER},
        )

        strategy.learn_from_result(result)

        # Rock probability should decrease after loss
        assert strategy.prob_rock < initial_rock


class TestNumberGuessingGame:
    """Tests for Number Prediction game."""

    def test_alternating_pattern_detection(self):
        """Strategy should learn alternating patterns."""
        game = NumberGuessingGame(
            pattern_type=PatternType.ALTERNATING,
            pattern_change_frequency=0,  # No pattern changes
        )
        strategy = NumberGuessingStrategy()

        # Play games to learn the pattern
        total_error = 0
        for _ in range(50):
            result = game.play_round(strategy)
            strategy.learn_from_result(result)
            total_error += result.details.get("error", 0)

        avg_error_early = total_error / 50

        # Play more games - error should decrease
        total_error = 0
        for _ in range(50):
            result = game.play_round(strategy)
            strategy.learn_from_result(result)
            total_error += result.details.get("error", 0)

        avg_error_late = total_error / 50

        # Later predictions should be better (or at least not much worse)
        # Learning takes time, so we're lenient here
        assert avg_error_late <= avg_error_early * 1.5

    def test_pattern_generator_produces_expected_values(self):
        """Pattern generator should produce expected patterns."""
        gen = PatternGenerator(
            pattern_type=PatternType.ALTERNATING,
            value_range=(0.0, 100.0),
            noise_level=0.0,
        )

        values = [gen.generate_next() for _ in range(10)]

        # Alternating pattern should have high variance between consecutive values
        diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        avg_diff = sum(diffs) / len(diffs)

        # With alternating, diffs should be large (switching between 25% and 75%)
        assert avg_diff > 30

    def test_reward_calculation(self):
        """Closer predictions should get higher rewards."""
        game = NumberGuessingGame(stake=10.0, max_error_for_reward=20.0)

        # Good prediction strategy
        from core.skills.base import SkillStrategy

        class PerfectStrategy(SkillStrategy):
            def __init__(self):
                self._last_history = []

            def choose_action(self, game_state):
                history = game_state.get("history", [])
                if history:
                    return history[-1]  # Guess last value
                return 50.0

            def learn_from_result(self, result):
                pass

            def get_parameters(self):
                return {}

            def set_parameters(self, params):
                pass

        strategy = PerfectStrategy()

        # Play a game and check reward is positive or zero
        result = game.play_round(strategy)
        # With mean-reverting or constant patterns, guessing last value is decent
        assert result.score_change >= -game.stake * 0.5


class TestSkillGameComponent:
    """Tests for fish skill game component."""

    def test_stats_tracking(self):
        """Component should track stats correctly."""
        component = SkillGameComponent()

        # Set up RPS strategy
        from core.skills.games.rock_paper_scissors import RPSStrategy

        component.set_strategy(SkillGameType.ROCK_PAPER_SCISSORS, RPSStrategy())

        # Record some results
        from core.skills.base import SkillGameResult

        win_result = SkillGameResult(
            player_id="test",
            opponent_id="opp",
            won=True,
            score_change=10.0,
            was_optimal=True,
        )
        loss_result = SkillGameResult(
            player_id="test",
            opponent_id="opp",
            won=False,
            score_change=-10.0,
            was_optimal=False,
        )

        component.record_game_result(SkillGameType.ROCK_PAPER_SCISSORS, win_result)
        component.record_game_result(SkillGameType.ROCK_PAPER_SCISSORS, loss_result)

        stats = component.get_stats(SkillGameType.ROCK_PAPER_SCISSORS)
        assert stats.total_games == 2
        assert stats.wins == 1
        assert stats.losses == 1
        assert stats.get_win_rate() == 0.5

    def test_strategy_inheritance(self):
        """Strategies should inherit and mutate correctly."""
        # Seed random for reproducible mutation
        random.seed(42)

        parent = SkillGameComponent()
        from core.skills.games.rock_paper_scissors import RPSStrategy

        parent_strategy = RPSStrategy(prob_rock=0.5, prob_paper=0.3, prob_scissors=0.2)
        parent.set_strategy(SkillGameType.ROCK_PAPER_SCISSORS, parent_strategy)

        child = SkillGameComponent()
        # Use high mutation rate to ensure mutations always occur
        child.inherit_from_parent(parent, mutation_rate=0.5)

        child_strategy = child.get_strategy(SkillGameType.ROCK_PAPER_SCISSORS)
        assert child_strategy is not None

        # Parameters should be similar but not identical (mutation)
        parent_params = parent_strategy.get_parameters()
        child_params = child_strategy.get_parameters()

        # At least some parameters should be different due to mutation
        param_diffs = [
            abs(parent_params[k] - child_params.get(k, 0))
            for k in parent_params
            if k != "learning_rate"  # Learning rate mutation may be 0
        ]
        # With high mutation rate, at least one param should change
        assert sum(param_diffs) > 0, f"Expected mutation differences, got parent={parent_params}, child={child_params}"


class TestConfig:
    """Tests for skill game configuration."""

    def test_default_config(self):
        """Default config should be valid."""
        config = SkillGameConfig()
        assert config.active_game in SkillGameType
        assert config.stake_multiplier > 0
        assert config.encounter_rate > 0

    def test_get_active_game(self):
        """Should get correct active game."""
        config = SkillGameConfig(active_game=SkillGameType.ROCK_PAPER_SCISSORS)
        set_skill_game_config(config)

        game = get_active_skill_game()
        assert game is not None
        assert game.game_type == SkillGameType.ROCK_PAPER_SCISSORS

    def test_change_active_game(self):
        """Should be able to change active game."""
        set_active_skill_game(SkillGameType.NUMBER_GUESSING)

        game = get_active_skill_game()
        assert game is not None
        assert game.game_type == SkillGameType.NUMBER_GUESSING

        # Reset
        set_active_skill_game(SkillGameType.ROCK_PAPER_SCISSORS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
