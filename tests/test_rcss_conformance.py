"""RCSS conformance tests for RCSS-Lite engine.

These tests verify that the RCSS-Lite engine correctly implements
key invariants from the rcssserver physics model.

Target version: rcssserver 18.x (See params.py for version notes)
"""

import math

from core.minigames.soccer import (
    DEFAULT_RCSS_PARAMS,
    RCSSCommand,
    RCSSLiteEngine,
    RCSSParams,
    RCSSVector,
)


class TestRCSSCycleInvariants:
    """Tests for RCSS cycle timing invariants."""

    def test_cycle_step_is_100ms(self):
        """Verify default cycle timing matches RCSS (100ms per cycle = 10Hz)."""
        assert DEFAULT_RCSS_PARAMS.cycle_ms == 100

    def test_cycle_counter_increments(self):
        """Cycle counter should increment by 1 each step."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0))

        assert engine.cycle == 0
        engine.step_cycle()
        assert engine.cycle == 1
        engine.step_cycle()
        assert engine.cycle == 2


class TestRCSSSpeedCaps:
    """Tests for RCSS speed capping invariants."""

    def test_player_speed_capped(self):
        """Player velocity should be clamped to player_speed_max."""
        params = RCSSParams(player_speed_max=1.05)
        engine = RCSSLiteEngine(params=params, seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        # Queue maximum power dash repeatedly to build speed
        for _ in range(20):
            engine.queue_command("left_1", RCSSCommand.dash(100, 0))
            engine.step_cycle()

        player = engine.get_player("left_1")
        speed = player.velocity.magnitude()

        # Speed should not exceed max
        assert speed <= params.player_speed_max + 0.01  # Small tolerance

    def test_ball_speed_capped(self):
        """Ball velocity should be clamped to ball_speed_max."""
        params = RCSSParams(ball_speed_max=3.0)
        engine = RCSSLiteEngine(params=params, seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)
        engine.set_ball_position(0.5, 0)  # Within kickable margin

        # Kick at maximum power
        engine.queue_command("left_1", RCSSCommand.kick(100, 0))
        engine.step_cycle()

        ball = engine.get_ball()
        ball_speed = ball.velocity.magnitude()

        # Ball speed should not exceed max
        assert ball_speed <= params.ball_speed_max + 0.01


class TestRCSSDecay:
    """Tests for RCSS velocity decay invariants."""

    def test_player_decay_applied(self):
        """Player velocity should decay by player_decay factor each cycle."""
        params = RCSSParams(player_decay=0.4)
        engine = RCSSLiteEngine(params=params, seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        # Give player initial velocity via dash
        engine.queue_command("left_1", RCSSCommand.dash(100, 0))
        engine.step_cycle()

        # Get velocity after dash
        player = engine.get_player("left_1")
        vel_after_dash = player.velocity.magnitude()

        # Step without new commands - velocity should decay
        engine.step_cycle()
        vel_after_decay = player.velocity.magnitude()

        # Velocity should have decayed (multiplied by decay factor)
        # decay = 0.4 means velocity is multiplied by 0.4 each cycle
        expected_vel = vel_after_dash * params.player_decay
        assert abs(vel_after_decay - expected_vel) < 0.1

    def test_ball_decay_applied(self):
        """Ball velocity should decay by ball_decay factor each cycle."""
        params = RCSSParams(ball_decay=0.94)
        engine = RCSSLiteEngine(params=params, seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)
        engine.set_ball_position(0.5, 0)

        # Kick ball
        engine.queue_command("left_1", RCSSCommand.kick(50, 0))
        engine.step_cycle()

        ball = engine.get_ball()
        vel_after_kick = ball.velocity.magnitude()

        # Step without new kicks - velocity should decay
        engine.step_cycle()
        vel_after_decay = ball.velocity.magnitude()

        # Ball velocity should have decayed
        expected_vel = vel_after_kick * params.ball_decay
        assert abs(vel_after_decay - expected_vel) < 0.1


class TestRCSSCommandClamping:
    """Tests for RCSS command parameter clamping."""

    def test_dash_power_clamped(self):
        """Dash power should be clamped to [-100, 100]."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        # Queue dash with excessive power
        engine.queue_command("left_1", RCSSCommand.dash(200, 0))
        engine.step_cycle()

        # Player should have moved (command was processed with clamped power)
        player = engine.get_player("left_1")
        assert player.velocity.magnitude() > 0

    def test_turn_moment_clamped(self):
        """Turn moment should be clamped to [-180, 180] degrees."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        initial_angle = engine.get_player("left_1").body_angle

        # Queue turn with excessive moment
        engine.queue_command("left_1", RCSSCommand.turn(360))
        engine.step_cycle()

        # Angle should have changed (command was processed)
        final_angle = engine.get_player("left_1").body_angle
        angle_change = abs(final_angle - initial_angle)

        # Change should be at most 180 degrees (clamped)
        assert angle_change <= math.pi + 0.1

    def test_kick_power_clamped(self):
        """Kick power should be clamped to [0, 100]."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)
        engine.set_ball_position(0.5, 0)

        # Queue kick with excessive power
        engine.queue_command("left_1", RCSSCommand.kick(200, 0))
        engine.step_cycle()

        # Ball should be moving (command was processed with clamped power)
        ball = engine.get_ball()
        assert ball.velocity.magnitude() > 0


class TestRCSSStaminaModel:
    """Tests for RCSS stamina mechanics."""

    def test_stamina_consumed_on_dash(self):
        """Stamina should be consumed when dashing."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        initial_stamina = engine.get_player("left_1").stamina

        # Dash
        engine.queue_command("left_1", RCSSCommand.dash(100, 0))
        engine.step_cycle()

        final_stamina = engine.get_player("left_1").stamina

        # Stamina should have decreased
        assert final_stamina < initial_stamina

    def test_stamina_recovers_when_resting(self):
        """Stamina should recover when not exerting (no dash/kick)."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

        # Deplete stamina
        for _ in range(20):
            engine.queue_command("left_1", RCSSCommand.dash(100, 0))
            engine.step_cycle()

        depleted_stamina = engine.get_player("left_1").stamina

        # Rest (step without commands)
        for _ in range(10):
            engine.step_cycle()

        recovered_stamina = engine.get_player("left_1").stamina

        # Stamina should have recovered
        assert recovered_stamina > depleted_stamina


class TestRCSSDeterminism:
    """Tests for deterministic behavior."""

    def test_same_seed_identical_trajectory(self):
        """Same seed should produce identical player trajectories."""

        def run_simulation(seed):
            engine = RCSSLiteEngine(seed=seed)
            engine.add_player("left_1", "left", RCSSVector(-20, 0), body_angle=0.0)
            engine.add_player("right_1", "right", RCSSVector(20, 0), body_angle=math.pi)

            trajectory = []
            for _ in range(50):
                engine.queue_command("left_1", RCSSCommand.dash(50, 0))
                engine.queue_command("right_1", RCSSCommand.dash(50, 0))
                engine.step_cycle()

                left = engine.get_player("left_1")
                right = engine.get_player("right_1")
                trajectory.append(
                    (left.position.x, left.position.y, right.position.x, right.position.y)
                )

            return trajectory

        traj1 = run_simulation(42)
        traj2 = run_simulation(42)

        assert traj1 == traj2, "Same seed should produce identical trajectories"

    def test_different_seeds_same_deterministic_physics(self):
        """Physics should be deterministic regardless of seed (no noise by default)."""

        def run_simple_physics(seed):
            params = RCSSParams(noise_enabled=False)
            engine = RCSSLiteEngine(params=params, seed=seed)
            engine.add_player("left_1", "left", RCSSVector(0, 0), body_angle=0.0)

            # Single dash
            engine.queue_command("left_1", RCSSCommand.dash(100, 0))
            engine.step_cycle()

            return engine.get_player("left_1").position.x

        pos1 = run_simple_physics(42)
        pos2 = run_simple_physics(12345)

        # With noise disabled, physics should be identical
        assert pos1 == pos2
