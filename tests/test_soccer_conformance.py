import math

import pytest

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import RCSSParams
from core.minigames.soccer.policy_adapter import (
    MAX_KICK_POWER,
    action_to_command,
    build_observation,
)


@pytest.fixture
def engine():
    params = RCSSParams(
        player_decay=0.4, max_moment=180.0, dash_power_rate=0.006, field_length=100.0
    )
    return RCSSLiteEngine(params=params, seed=42)


def test_determinism(engine):
    """Test that the engine replay is deterministic given the same seed."""
    engine.add_player("left_1", "left", RCSSVector(-10, 0))
    engine.add_player("right_1", "right", RCSSVector(10, 0))
    engine.set_ball_position(0, 0)

    # Run 100 cycles with random commands (but same seed)
    # Actually, we need to feed commands.
    # Let's run two separate engines with same seed and same command inputs.

    params = RCSSParams(noise_enabled=False)

    # Run A
    eng_a = RCSSLiteEngine(params=params, seed=123)
    eng_a.add_player("p1", "left", RCSSVector(0, 0))
    eng_a.queue_command("p1", RCSSCommand.dash(100, 0))
    res_a = eng_a.step_cycle()

    # Run B
    eng_b = RCSSLiteEngine(params=params, seed=123)
    eng_b.add_player("p1", "left", RCSSVector(0, 0))
    eng_b.queue_command("p1", RCSSCommand.dash(100, 0))
    res_b = eng_b.step_cycle()

    assert eng_a.get_player("p1").position.x == eng_b.get_player("p1").position.x
    assert eng_a.get_player("p1").velocity.x == eng_b.get_player("p1").velocity.x
    assert res_a["cycle"] == res_b["cycle"]


def test_command_timing_and_decay(engine):
    """Test that commands affect state in correct order and decay is applied."""
    # Setup
    pid = "p1"
    engine.add_player(pid, "left", RCSSVector(0, 0))
    player = engine.get_player(pid)

    # Cycle 0: Dash 100
    # Accel = 100 * 0.006 = 0.6
    # Vel(1) = Vel(0) + Accel = 0 + 0.6 = 0.6
    # Pos(1) = Pos(0) + Vel(1) = 0 + 0.6 = 0.6
    # Vel(1) = Vel(1) * Decay = 0.6 * 0.4 = 0.24 (at end of cycle)

    engine.queue_command(pid, RCSSCommand.dash(100, 0))
    engine.step_cycle()  # t=0 -> t=1

    # Check state at t=1
    assert math.isclose(player.position.x, 0.6, abs_tol=1e-5)
    assert math.isclose(player.velocity.x, 0.24, abs_tol=1e-5)


def test_kickable_gating(engine):
    """Test that kick commands are ignored if ball is out of range."""
    pid = "kicker"
    engine.add_player(pid, "left", RCSSVector(0, 0))

    # Ball far away (at 10,0)
    engine.set_ball_position(10, 0)

    # Try to kick
    engine.queue_command(pid, RCSSCommand.kick(100, 0))
    engine.step_cycle()

    ball = engine.get_ball()
    # Ball should not move
    assert ball.velocity.magnitude() == 0.0

    # Move ball close (within kickable margin 0.7 + sizes)
    # Player radius 0.3 + Ball 0.085 + Margin 0.7 ~= 1.085
    engine.set_ball_position(0.5, 0)

    engine.queue_command(pid, RCSSCommand.kick(100, 0))
    engine.step_cycle()

    # Ball should move
    assert ball.velocity.magnitude() > 0.0


def test_policy_adapter_conformance():
    """Test that policy adapter clamps values and builds valid commands."""
    params = RCSSParams()

    # Test Kick Clamping
    action_kick_huge = {"kick": [9999, 0]}
    cmd = action_to_command(action_kick_huge, params)
    assert cmd.cmd_type.value == "kick"
    assert cmd.power == MAX_KICK_POWER

    # Test Turn Clamping
    action_turn_huge = {"turn": [1000]}
    cmd = action_to_command(action_turn_huge, params)
    assert cmd.cmd_type.value == "turn"
    # Note: params.max_moment might be 180 or config dependent.
    # Default RCSSParams has max_moment=180
    assert cmd.direction == params.max_moment

    # Test Priority (Kick > Turn > Dash)
    action_mix = {"kick": [50, 0], "dash": [100]}
    cmd = action_to_command(action_mix, params)
    assert cmd.cmd_type.value == "kick"


def test_observation_schema(engine):
    """Test that build_observation returns expected schema."""
    pid = "obs_p"
    engine.add_player(pid, "left", RCSSVector(10, 10))
    engine.set_ball_position(20, 10)  # 10m to right

    obs = build_observation(engine, pid)

    assert "self_x" in obs
    assert "ball_rel_x" in obs
    assert "is_kickable" in obs

    # Check calculation correctness
    assert math.isclose(obs["ball_rel_x"], 10.0)
    assert math.isclose(obs["ball_rel_y"], 0.0)
    assert obs["is_kickable"] == 0.0  # Too far
