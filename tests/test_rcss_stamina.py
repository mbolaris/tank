from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import RCSSParams


def test_stamina_consumption():
    """Verify dash consumes stamina."""
    env = RCSSLiteEngine()
    env.add_player("p1", "left")

    player = env.get_player("p1")
    assert player is not None
    initial_stamina = player.stamina

    # Dash 100
    env.queue_command("p1", RCSSCommand.dash(100))
    env.step_cycle()

    # Consumed: 100 * consume_rate - recovery
    # 100 * 1.0 - 45.0 * 1.0 = 55 net loss
    expected = initial_stamina - (100 * 1.0) + (45.0 * 1.0)
    # Clamp min/max handled by engine (8000 max)

    assert player.stamina < initial_stamina
    assert abs(player.stamina - expected) < 0.1


def test_effort_decay():
    """Verify effort decays when stamina is low."""
    # Custom params to trigger thresholds easily
    params = RCSSParams(stamina_max=4000)
    env = RCSSLiteEngine(params=params)
    env.add_player("p1", "left")

    player = env.get_player("p1")
    assert player is not None

    # Manually drain stamina below effort_dec_thr (4000 * 0.25 = 1000)
    player.stamina = 800.0
    initial_effort = player.effort  # 1.0

    env.step_cycle()  # Should decay effort

    assert player.effort < initial_effort
    assert player.effort == max(params.effort_min, initial_effort - params.effort_dec)


def test_recovery_decay():
    """Verify recovery decays when stamina is really low."""
    # Custom params
    params = RCSSParams(stamina_max=4000)
    env = RCSSLiteEngine(params=params)
    env.add_player("p1", "left")

    player = env.get_player("p1")
    assert player is not None

    # Drain stamina below recover_dec_thr (4000 * 0.25 = 1000)
    player.stamina = 800.0
    initial_recovery = player.recovery

    env.step_cycle()

    assert player.recovery < initial_recovery


def test_effort_refills():
    """Verify effort recovers when stamina is high."""
    params = RCSSParams(stamina_max=4000)
    env = RCSSLiteEngine(params=params)
    env.add_player("p1", "left")

    player = env.get_player("p1")
    assert player is not None
    player.effort = 0.8
    player.stamina = 3000.0  # > effort_inc_thr (4000 * 0.6 = 2400)

    env.step_cycle()

    assert player.effort > 0.8


def test_dash_effectiveness_with_effort():
    """Verify dash power is scaled by effort."""
    env = RCSSLiteEngine()
    env.add_player("fresh", "left", position=RCSSVector(0, 0))
    env.add_player("tired", "left", position=RCSSVector(0, 10))

    tired = env.get_player("tired")
    assert tired is not None
    tired.effort = 0.5

    env.queue_command("fresh", RCSSCommand.dash(100))
    env.queue_command("tired", RCSSCommand.dash(100))

    env.step_cycle()

    fresh = env.get_player("fresh")
    tired = env.get_player("tired")
    assert fresh is not None
    assert tired is not None

    # Fresh acceleration: 100 * 1.0 * power_rate
    # Tired acceleration: 100 * 0.5 * power_rate
    assert fresh.velocity.magnitude() > tired.velocity.magnitude()
    assert abs(tired.velocity.magnitude() - (fresh.velocity.magnitude() * 0.5)) < 0.01


def test_movement_noise():
    """Verify noise is applied when enabled."""
    params = RCSSParams(noise_enabled=True, player_rand=0.1)
    env = RCSSLiteEngine(params=params, seed=42)
    env.add_player("p1", "left")

    # Dash
    env.queue_command("p1", RCSSCommand.dash(100))
    env.step_cycle()  # Cycle 1

    # With noise, velocity vector should not be perfectly aligned with dash dir if noise > 0
    # But here dash is 0 deg.
    p1 = env.get_player("p1")
    assert p1 is not None
    # Dash direction is 0 (body angle 0). Expect pure X velocity without noise.
    # With noise, Y velocity might be non-zero.

    assert abs(p1.velocity.y) > 0.0  # Likely non-zero due to noise
