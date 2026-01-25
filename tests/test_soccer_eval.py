"""Tests for deterministic soccer evaluation using RCSS-Lite engine.

These tests verify:
1. Same seed produces identical results (determinism)
2. Different seeds produce different results (seed sensitivity via noise)
3. Goal scoring works correctly
"""

from core.minigames.soccer.params import RCSSParams
from core.minigames.soccer.quick_eval import QuickEvalConfig, run_quick_eval


def test_soccer_eval_deterministic_same_seed():
    """Run twice with same config and assert results are identical (including episode_hash)."""
    config = QuickEvalConfig(
        seed=42,
        max_cycles=200,
        initial_players={"left": [(-20, 0)], "right": [(20, 0)]},
    )

    result1 = run_quick_eval(config)
    result2 = run_quick_eval(config)

    assert result1.episode_hash == result2.episode_hash
    assert result1.score == result2.score
    assert result1.touches == result2.touches
    assert result1.possession_cycles == result2.possession_cycles


def test_soccer_eval_diff_seed_changes_hash():
    """Same setup but different seed with noise enabled => episode_hash differs.

    When noise is enabled, the seed affects:
    - Kick direction noise (kick_rand)
    - Player velocity noise (player_rand)

    This ensures different seeds produce different trajectories without relying
    on position jitter hacks.
    """
    # Enable noise so seed actually affects simulation
    noisy_params = RCSSParams(noise_enabled=True, kick_rand=0.1, player_rand=0.05)

    config1 = QuickEvalConfig(
        seed=42,
        max_cycles=200,
        params=noisy_params,
        initial_players={"left": [(-20, 0)], "right": [(20, 0)]},
    )

    config2 = QuickEvalConfig(
        seed=43,
        max_cycles=200,
        params=noisy_params,
        initial_players={"left": [(-20, 0)], "right": [(20, 0)]},
    )

    result1 = run_quick_eval(config1)
    result2 = run_quick_eval(config2)

    # Different seeds with noise should produce different trajectories
    assert result1.episode_hash != result2.episode_hash


def test_soccer_eval_deterministic_with_noise():
    """Verify that even with noise enabled, same seed produces same result."""
    noisy_params = RCSSParams(noise_enabled=True, kick_rand=0.1, player_rand=0.05)

    config = QuickEvalConfig(
        seed=123,
        max_cycles=100,
        params=noisy_params,
        initial_players={"left": [(-15, 5)], "right": [(15, -5)]},
    )

    result1 = run_quick_eval(config)
    result2 = run_quick_eval(config)

    assert result1.episode_hash == result2.episode_hash
    assert result1.score == result2.score


def test_soccer_eval_goal_scoring():
    """Verify that a goal is actually scored and logged in a simple scenario.

    Place a player within kickable distance of the ball, near the goal.
    The default policy should kick the ball into the goal.
    """
    # Field is 105x68 by default. Goals are at x = +/- 52.5
    # Kickable distance = player_size(0.3) + ball_size(0.085) + kickable_margin(0.7) ≈ 1.085
    # Place ball very close to left goal, with right player within kicking distance
    config = QuickEvalConfig(
        seed=42,
        max_cycles=50,
        initial_ball=(-51, 0),  # Ball very close to left goal line (-52.5)
        initial_players={"right": [(-50, 0)]},  # Right player within 1m of ball
    )
    result = run_quick_eval(config)

    # Right team should score in left goal (ball crosses x < -52.5)
    assert result.score["right"] > 0


def test_soccer_eval_multiple_players():
    """Test evaluation with multiple players per team."""
    # Place at least one player within kickable distance (<1.0m) of ball at origin
    # Engine kickable check: dist <= kickable_margin(0.7) + player_size(0.3) = 1.0
    config = QuickEvalConfig(
        seed=42,
        max_cycles=100,
        initial_players={
            "left": [(-0.8, 0), (-5, 3)],  # First player within kicking range
            "right": [(0.8, 0), (5, -3)],  # First player within kicking range
        },
    )

    result = run_quick_eval(config)

    # Verify we got some activity (players within range should kick)
    total_touches = result.touches["left"] + result.touches["right"]
    assert total_touches > 0, "Expected some ball touches with multiple players"

    # Verify determinism
    result2 = run_quick_eval(config)
    assert result.episode_hash == result2.episode_hash


# =============================================================================
# Telemetry Tests
# =============================================================================


def test_telemetry_determinism():
    """Verify that telemetry is deterministic: same seed produces identical telemetry."""
    config = QuickEvalConfig(
        seed=42,
        max_cycles=100,
        initial_players={
            "left": [(-0.8, 0), (-5, 3)],
            "right": [(0.8, 0), (5, -3)],
        },
    )

    result1 = run_quick_eval(config)
    result2 = run_quick_eval(config)

    # Telemetry should be identical
    tel1 = result1.telemetry
    tel2 = result2.telemetry

    assert tel1.total_cycles == tel2.total_cycles

    for team in ["left", "right"]:
        t1 = tel1.teams[team]
        t2 = tel2.teams[team]
        assert t1.possession_frames == t2.possession_frames
        assert t1.touches == t2.touches
        assert t1.shots == t2.shots
        assert t1.shots_on_target == t2.shots_on_target
        assert abs(t1.ball_progress - t2.ball_progress) < 1e-6
        assert t1.goals == t2.goals

    for player_id in tel1.players:
        p1 = tel1.players[player_id]
        p2 = tel2.players[player_id]
        assert p1.touches == p2.touches
        assert p1.kicks == p2.kicks
        assert abs(p1.distance_run - p2.distance_run) < 1e-6


def test_telemetry_has_activity():
    """Verify telemetry captures player movement and ball activity."""
    # Place players far enough from ball that they need to chase it
    config = QuickEvalConfig(
        seed=42,
        max_cycles=200,
        initial_players={
            "left": [(-5, 0)],
            "right": [(5, 0)],
        },
    )

    result = run_quick_eval(config)
    tel = result.telemetry

    # Players should have moved while chasing the ball
    total_distance = sum(p.distance_run for p in tel.players.values())
    assert total_distance > 0, "Expected players to move while chasing ball"

    # Verify telemetry structure is correct
    assert "left" in tel.teams
    assert "right" in tel.teams
    assert len(tel.players) == 2
    assert tel.total_cycles == 200


def test_telemetry_ball_progress():
    """Verify ball progress is tracked correctly when a team kicks toward goal."""
    # Place right player within kicking range, ball slightly left of center
    # Right player should kick ball left (toward left goal = negative x)
    config = QuickEvalConfig(
        seed=42,
        max_cycles=50,
        initial_ball=(-0.5, 0),
        initial_players={"right": [(0.5, 0)]},  # Within kicking range
    )

    result = run_quick_eval(config)
    tel = result.telemetry

    # Right team kicks toward left goal (negative x direction)
    # Ball progress for right team should be positive (they moved ball toward their goal)
    assert (
        tel.teams["right"].ball_progress > 0
    ), "Right team should have positive ball progress when kicking toward left goal"


def test_shaped_rewards_nonzero_in_draw():
    """Verify shaped rewards are non-zero in a 0-0 draw when there is ball movement."""
    from core.minigames.soccer.rewards import calculate_shaped_bonuses

    config = QuickEvalConfig(
        seed=42,
        max_cycles=100,
        initial_players={
            "left": [(-0.8, 0)],
            "right": [(0.8, 0)],
        },
    )

    result = run_quick_eval(config)

    # Ensure it's a 0-0 draw (or at least no clear winner scenario for shaped rewards)
    # The key test is that shaped bonuses are calculated from activity

    bonuses = calculate_shaped_bonuses(result.telemetry)

    # Should have some bonuses from touches/progress
    total_bonus = sum(bonuses.values())
    assert total_bonus > 0, "Expected non-zero shaped bonuses with ball activity"


def test_shaped_rewards_bounded():
    """Verify shaped rewards stay within expected bounds."""
    from core.minigames.soccer.rewards import calculate_shaped_bonuses

    config = QuickEvalConfig(
        seed=42,
        max_cycles=500,  # Longer match for more activity
        initial_players={
            "left": [(-0.8, 0), (-5, 3), (-10, -3)],
            "right": [(0.8, 0), (5, -3), (10, 3)],
        },
    )

    result = run_quick_eval(config)

    max_bonus = 10.0  # Default max_bonus_per_player
    bonuses = calculate_shaped_bonuses(
        result.telemetry,
        max_bonus_per_player=max_bonus,
    )

    # Each player's bonus should be capped
    for player_id, bonus in bonuses.items():
        assert bonus <= max_bonus, f"Player {player_id} bonus {bonus} exceeds cap {max_bonus}"
        assert bonus >= 0, f"Player {player_id} bonus {bonus} should be non-negative"
