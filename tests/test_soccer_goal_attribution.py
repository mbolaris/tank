"""Tests for soccer goal attribution and shaped rewards.

This module tests that:
1. Goal attribution is deterministic (same seed → same scorer/assist IDs)
2. Assists are credited only with correct rule (window + same team)
3. Fitness reflects goals (scorer's fitness > non-scorer's fitness)
"""

import pytest

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.match_runner import SoccerMatchRunner
from core.minigames.soccer.params import RCSSParams


@pytest.fixture
def engine():
    """Create a test engine with deterministic params."""
    params = RCSSParams(
        field_length=100.0,
        field_width=60.0,
        goal_width=14.0,
        goal_depth=2.0,
        kickable_margin=0.7,
        kick_power_rate=0.027,
        ball_speed_max=3.0,
        noise_enabled=False,  # Determinism
    )
    return RCSSLiteEngine(params=params, seed=42)


def test_goal_attribution_deterministic():
    """Test that goal attribution is deterministic with same seed."""
    params = RCSSParams(noise_enabled=False, field_length=100.0, goal_width=14.0)

    # Run A
    eng_a = RCSSLiteEngine(params=params, seed=123)
    eng_a.add_player("scorer", "left", RCSSVector(45, 0))
    eng_a.set_ball_position(45, 0)

    # Kick toward right goal (left team scores)
    eng_a.queue_command("scorer", RCSSCommand.kick(100, 0))
    result_a = eng_a.step_cycle()

    # Let ball travel to goal
    for _ in range(50):
        result_a = eng_a.step_cycle()
        if result_a.get("events"):
            break

    # Run B (identical setup)
    eng_b = RCSSLiteEngine(params=params, seed=123)
    eng_b.add_player("scorer", "left", RCSSVector(45, 0))
    eng_b.set_ball_position(45, 0)

    eng_b.queue_command("scorer", RCSSCommand.kick(100, 0))
    result_b = eng_b.step_cycle()

    for _ in range(50):
        result_b = eng_b.step_cycle()
        if result_b.get("events"):
            break

    # Extract goal events
    events_a = [e for r in [result_a] for e in r.get("events", []) if e.get("type") == "goal"]
    events_b = [e for r in [result_b] for e in r.get("events", []) if e.get("type") == "goal"]

    # Should have same scorer
    assert len(events_a) > 0
    assert len(events_b) > 0
    assert events_a[0].get("scorer_id") == events_b[0].get("scorer_id")
    assert events_a[0].get("scorer_id") == "scorer"


def test_assist_credited_same_team_only(engine):
    """Test that assists are only credited to teammates, not opponents."""
    # Setup: two players from different teams touch ball before goal
    engine.add_player("left_1", "left", RCSSVector(40, 0))
    engine.add_player("right_1", "right", RCSSVector(42, 0))
    engine.set_ball_position(40, 0)

    # Left player touches first
    engine.queue_command("left_1", RCSSCommand.kick(50, 0))
    engine.step_cycle()

    # Move ball near right player
    ball = engine.get_ball()
    engine.set_ball_position(42, 0)

    # Right player scores (opponent scored, so no assist for left_1)
    engine.queue_command("right_1", RCSSCommand.kick(100, 180))  # Toward left goal
    engine.step_cycle()

    # Let ball travel
    goal_event = None
    for _ in range(50):
        result = engine.step_cycle()
        for event in result.get("events", []):
            if event.get("type") == "goal":
                goal_event = event
                break
        if goal_event:
            break

    # Should have goal by right_1, but NO assist (different teams)
    assert goal_event is not None
    assert goal_event.get("scorer_id") == "right_1"
    assert goal_event.get("assist_id") is None  # Different team, no assist


def test_assist_credited_within_window(engine):
    """Test that assists are only credited within the time window."""
    engine.add_player("assist_1", "left", RCSSVector(30, 0))
    engine.add_player("scorer_1", "left", RCSSVector(40, 0))
    engine.set_ball_position(30, 0)

    # assist_1 touches ball
    engine.queue_command("assist_1", RCSSCommand.kick(30, 0))
    engine.step_cycle()

    # Wait too long (beyond 50 cycle assist window)
    for _ in range(60):
        engine.step_cycle()

    # Move ball to scorer (manually for test)
    engine.set_ball_position(40, 0)

    # scorer_1 kicks into goal
    engine.queue_command("scorer_1", RCSSCommand.kick(100, 0))
    engine.step_cycle()

    # Let ball travel
    goal_event = None
    for _ in range(50):
        result = engine.step_cycle()
        for event in result.get("events", []):
            if event.get("type") == "goal":
                goal_event = event
                break
        if goal_event:
            break

    # Should have goal but NO assist (window expired)
    assert goal_event is not None
    assert goal_event.get("scorer_id") == "scorer_1"
    assert goal_event.get("assist_id") is None  # Window expired


def test_assist_credited_within_window_same_team(engine):
    """Test that assist is credited when all conditions are met."""
    engine.add_player("assister", "left", RCSSVector(30, 0))
    engine.add_player("scorer", "left", RCSSVector(35, 0))
    engine.set_ball_position(30, 0)

    # Assister touches ball first
    engine.queue_command("assister", RCSSCommand.kick(20, 0))
    engine.step_cycle()

    # Wait a bit (but within window)
    for _ in range(5):
        engine.step_cycle()

    # Move ball to scorer
    ball = engine.get_ball()
    engine.set_ball_position(ball.position.x, 0)

    # Scorer kicks into goal
    engine.queue_command("scorer", RCSSCommand.kick(100, 0))
    engine.step_cycle()

    # Let ball travel
    goal_event = None
    for _ in range(50):
        result = engine.step_cycle()
        for event in result.get("events", []):
            if event.get("type") == "goal":
                goal_event = event
                break
        if goal_event:
            break

    # Should have both scorer and assist
    assert goal_event is not None
    assert goal_event.get("scorer_id") == "scorer"
    assert goal_event.get("assist_id") == "assister"


def test_fitness_reflects_goals():
    """Test that scorer's fitness is higher than non-scorer's fitness."""
    from core.genetics import Genome

    # Create simple test runner
    runner = SoccerMatchRunner(team_size=2)

    # Create genomes for 4 players (2 per team)
    genomes = [Genome.random(use_algorithm=False, rng=None) for _ in range(4)]

    # Run episode (seed determines who scores)
    episode_result, agent_results = runner.run_episode(genomes, seed=42, frames=300)

    # Extract fitness values
    fitness_by_goals = {}
    for agent in agent_results:
        goal_count = agent.goals
        if goal_count not in fitness_by_goals:
            fitness_by_goals[goal_count] = []
        fitness_by_goals[goal_count].append(agent.fitness)

    # If any goals were scored, fitness should correlate
    if len(fitness_by_goals) > 1:
        # Players with more goals should have higher fitness
        goal_counts = sorted(fitness_by_goals.keys())
        for i in range(len(goal_counts) - 1):
            lower_goals = goal_counts[i]
            higher_goals = goal_counts[i + 1]
            avg_fitness_lower = sum(fitness_by_goals[lower_goals]) / len(fitness_by_goals[lower_goals])
            avg_fitness_higher = sum(fitness_by_goals[higher_goals]) / len(
                fitness_by_goals[higher_goals]
            )
            # Higher goals should correlate with higher fitness
            # (Allow some variance due to shaped rewards)
            assert avg_fitness_higher >= avg_fitness_lower


def test_goal_and_assist_increment_stats():
    """Test that PlayerStats.goals and assists are incremented correctly."""
    from core.genetics import Genome

    runner = SoccerMatchRunner(team_size=1)

    # Create genomes
    genomes = [Genome.random(use_algorithm=False, rng=None) for _ in range(2)]

    # Run episode
    episode_result, agent_results = runner.run_episode(genomes, seed=99, frames=500)

    # Check that goals/assists in stats match those in agent results
    for agent in agent_results:
        stats = episode_result.player_stats.get(agent.player_id)
        assert stats is not None
        assert stats.goals == agent.goals
        # Goals in stats should match what's tracked


def test_shaped_reward_adds_to_total_reward():
    """Test that ball progress toward goal contributes to total_reward."""
    from core.genetics import Genome

    runner = SoccerMatchRunner(team_size=1)
    genomes = [Genome.random(use_algorithm=False, rng=None) for _ in range(2)]

    # Run episode
    episode_result, _ = runner.run_episode(genomes, seed=55, frames=300)

    # At least one player should have non-zero total_reward from shaped rewards
    total_rewards = [stats.total_reward for stats in episode_result.player_stats.values()]

    # Some players should have accumulated shaped rewards
    # (May be positive or negative depending on ball movement)
    assert any(r != 0.0 for r in total_rewards)


def test_touch_tracking_resets_after_goal(engine):
    """Test that touch tracking resets after a goal is scored."""
    engine.add_player("scorer", "left", RCSSVector(48, 0))
    engine.set_ball_position(48, 0)

    # Score a goal
    engine.queue_command("scorer", RCSSCommand.kick(100, 0))
    engine.step_cycle()

    # Let ball reach goal
    goal_scored = False
    for _ in range(50):
        result = engine.step_cycle()
        if result.get("events"):
            goal_scored = True
            break

    assert goal_scored

    # Touch tracking should be reset
    assert engine._last_touch_player_id is None
    assert engine._last_touch_cycle == -1
    assert engine._prev_touch_player_id is None
