import math

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS


def test_kick_impacts_ball_position_within_same_cycle():
    """A kick should affect ball velocity and position during the same cycle."""
    engine = RCSSLiteEngine(params=DEFAULT_RCSS_PARAMS, seed=42)
    engine.add_player("left_1", "left")

    # Ensure the ball starts at the center and stationary.
    engine.set_ball_position(0.0, 0.0)

    # Queue a straightforward kick with enough power to move the ball.
    engine.queue_command("left_1", RCSSCommand.kick(power=50.0, direction=0.0))

    engine.step_cycle()
    ball = engine.get_ball()

    expected_acceleration = 50.0 * DEFAULT_RCSS_PARAMS.kick_power_rate
    expected_position = expected_acceleration
    expected_velocity = expected_acceleration * DEFAULT_RCSS_PARAMS.ball_decay

    assert math.isclose(ball.position.x, expected_position, rel_tol=1e-6)
    assert math.isclose(ball.velocity.x, expected_velocity, rel_tol=1e-6)
    assert math.isclose(ball.position.y, 0.0, abs_tol=1e-6)
    assert math.isclose(ball.velocity.y, 0.0, abs_tol=1e-6)
