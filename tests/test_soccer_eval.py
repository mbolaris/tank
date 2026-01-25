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
