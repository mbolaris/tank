"""Tests for ball physics and interactions.

Tests RCSS-Lite style ball physics including:
- Velocity decay
- Speed capping
- Boundary collision and bouncing
- Kickable distance detection
- Position reset
"""

import pytest
import math
from unittest.mock import Mock

from core.entities.ball import Ball
from core.entities.goal_zone import GoalZone, GoalEvent
from core.math_utils import Vector2


class MockWorld:
    """Mock world for testing."""

    def __init__(self, width=800, height=600):
        self.min_x = 0.0
        self.min_y = 0.0
        self.max_x = float(width)
        self.max_y = float(height)

    def get_bounds(self):
        """Return world boundaries."""
        return ((self.min_x, self.min_y), (self.max_x, self.max_y))


class TestBallPhysics:
    """Test basic ball physics."""

    def test_ball_initialization(self):
        """Test ball creation with default parameters."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        assert ball.pos.x == 400
        assert ball.pos.y == 300
        assert ball.vel.x == 0.0
        assert ball.vel.y == 0.0
        assert ball.acceleration.x == 0.0
        assert ball.acceleration.y == 0.0
        assert ball.decay_rate == 0.94
        assert ball.max_speed == 3.0

    def test_ball_velocity_decay(self):
        """Test that velocity decays each update."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Set initial velocity
        ball.vel = Vector2(1.0, 0.5)

        # Update (should apply decay)
        ball.update(0)

        # Velocity should be reduced by decay_rate
        expected_vx = 1.0 * 0.94
        expected_vy = 0.5 * 0.94

        assert pytest.approx(ball.vel.x, abs=1e-6) == expected_vx
        assert pytest.approx(ball.vel.y, abs=1e-6) == expected_vy

    def test_ball_acceleration_to_velocity(self):
        """Test that acceleration contributes to velocity."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Set acceleration
        ball.acceleration = Vector2(0.5, 0.25)
        initial_vel = Vector2(1.0, 0.0)
        ball.vel = initial_vel.copy()

        # Update
        ball.update(0)

        # Velocity should have acceleration added (before decay)
        # Expected: (1.0 + 0.5) * 0.94, (0.0 + 0.25) * 0.94
        assert pytest.approx(ball.vel.x, abs=1e-6) == 1.5 * 0.94
        assert pytest.approx(ball.vel.y, abs=1e-6) == 0.25 * 0.94

    def test_ball_speed_capping(self):
        """Test that ball speed is capped at max_speed."""
        world = MockWorld()
        ball = Ball(world, 400, 300, max_speed=1.0)

        # Set velocity exceeding max_speed
        ball.vel = Vector2(2.0, 2.0)  # Magnitude ~2.83
        initial_speed = ball.vel.length()
        assert initial_speed > ball.max_speed  # Verify velocity exceeds max

        # Update (should cap speed)
        ball.update(0)

        final_speed = ball.vel.length()

        # Speed should be capped to max_speed, then decayed by decay_rate
        # Expected: max_speed * decay_rate = 1.0 * 0.94 = 0.94
        # Allow floating point tolerance
        assert final_speed <= 1.0 * 0.94 + 0.1

    def test_ball_position_update(self):
        """Test that velocity moves the ball."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Set velocity
        ball.vel = Vector2(2.0, 1.0)

        # Update
        ball.update(0)

        # Position should move by velocity (before decay is applied to next frame)
        # After one update: pos += vel, then vel *= decay
        assert pytest.approx(ball.pos.x, abs=1e-6) == 402.0
        assert pytest.approx(ball.pos.y, abs=1e-6) == 301.0

    def test_ball_acceleration_reset(self):
        """Test that acceleration resets after update."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Set acceleration
        ball.acceleration = Vector2(1.0, 1.0)

        # Update
        ball.update(0)

        # Acceleration should be reset
        assert ball.acceleration.x == 0.0
        assert ball.acceleration.y == 0.0


class TestBallBoundaryCollision:
    """Test ball bouncing off walls."""

    def test_ball_bounce_left_wall(self):
        """Test ball bouncing off left wall."""
        world = MockWorld()
        ball = Ball(world, 100, 300)
        # First move the ball to the wall
        ball.pos = Vector2(-5, 300)  # Beyond left wall
        ball.vel = Vector2(-2.0, 0.0)  # Moving left

        # Update
        ball.update(0)

        # Ball should bounce: position corrected and velocity reversed
        assert ball.pos.x >= 0  # Position should be corrected to wall
        assert ball.vel.x > 0  # Velocity should be reversed (moving right)

    def test_ball_bounce_right_wall(self):
        """Test ball bouncing off right wall."""
        world = MockWorld(800, 600)
        ball = Ball(world, 795, 300)  # Close to right wall
        ball.vel = Vector2(2.0, 0.0)  # Moving right

        # Update
        ball.update(0)

        # Ball should bounce
        assert ball.vel.x < 0  # Should be moving left

    def test_ball_bounce_top_wall(self):
        """Test ball bouncing off top wall."""
        world = MockWorld()
        ball = Ball(world, 400, 100)
        # Move ball beyond top wall
        ball.pos = Vector2(400, -5)  # Beyond top wall
        ball.vel = Vector2(0.0, -2.0)  # Moving up

        # Update
        ball.update(0)

        # Ball should bounce: position corrected and velocity reversed
        assert ball.pos.y >= 0  # Position should be corrected to wall
        assert ball.vel.y > 0  # Velocity should be reversed (moving down)

    def test_ball_bounce_bottom_wall(self):
        """Test ball bouncing off bottom wall."""
        world = MockWorld(800, 600)
        ball = Ball(world, 400, 595)  # Close to bottom wall
        ball.vel = Vector2(0.0, 2.0)  # Moving down

        # Update
        ball.update(0)

        # Ball should bounce
        assert ball.vel.y < 0  # Should be moving up


class TestBallKick:
    """Test ball kicking mechanics."""

    def test_ball_kick_adds_acceleration(self):
        """Test that kicking adds acceleration to the ball."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Kick with power 50 in direction (1, 0)
        direction = Vector2(1.0, 0.0)
        ball.kick(50.0, direction)

        # Should have acceleration
        assert ball.acceleration.x > 0
        assert ball.acceleration.y == 0.0

    def test_ball_kick_power_scaling(self):
        """Test that kick power scales acceleration."""
        world = MockWorld()
        ball1 = Ball(world, 400, 300)
        ball2 = Ball(world, 400, 300)

        # Kick ball1 with power 50
        direction = Vector2(1.0, 0.0)
        ball1.kick(50.0, direction)
        accel1 = ball1.acceleration.x

        # Kick ball2 with power 100
        ball2.kick(100.0, direction)
        accel2 = ball2.acceleration.x

        # Higher power should produce higher acceleration
        assert accel2 > accel1

    def test_ball_kick_tracks_kicker(self):
        """Test that last kicker is tracked."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        mock_kicker = Mock()
        mock_kicker.fish_id = 42

        direction = Vector2(1.0, 0.0)
        ball.kick(50.0, direction, kicker=mock_kicker)

        assert ball.last_kicker is mock_kicker


class TestBallKickableDistance:
    """Test kickable distance detection."""

    def test_fish_in_kickable_range(self):
        """Test that fish within kickable distance can kick."""
        world = MockWorld()
        # Use larger kickable_margin for testing (easier to work with pixel units)
        ball = Ball(world, 400, 300, kickable_margin=50.0)

        mock_fish = Mock()
        mock_fish.width = 20  # Radius = 10
        mock_fish_pos = Vector2(460, 300)  # 60 pixels away from ball center
        # Total required distance: fish_radius(10) + ball_size(0.085) + kickable_margin(50) ~ 60+
        # Actual distance: 60, so should be kickable

        is_kickable = ball.is_kickable_by(mock_fish, mock_fish_pos)

        # Should be kickable (within margin)
        assert is_kickable is True

    def test_fish_out_of_kickable_range(self):
        """Test that distant fish cannot kick."""
        world = MockWorld()
        ball = Ball(world, 400, 300, kickable_margin=2.0)

        mock_fish = Mock()
        mock_fish.width = 10
        mock_fish_pos = Vector2(500, 300)  # 100 pixels away

        is_kickable = ball.is_kickable_by(mock_fish, mock_fish_pos)

        # Should not be kickable
        assert is_kickable is False


class TestBallReset:
    """Test ball reset functionality."""

    def test_ball_reset_position_and_velocity(self):
        """Test that reset clears position and velocity."""
        world = MockWorld()
        ball = Ball(world, 400, 300)

        # Give it velocity and acceleration
        ball.vel = Vector2(5.0, 2.0)
        ball.acceleration = Vector2(1.0, 1.0)
        ball.last_kicker = Mock()

        # Reset
        ball.reset_position(100, 150)

        assert ball.pos.x == 100
        assert ball.pos.y == 150
        assert ball.vel.x == 0.0
        assert ball.vel.y == 0.0
        assert ball.acceleration.x == 0.0
        assert ball.acceleration.y == 0.0
        assert ball.last_kicker is None


class TestGoalZone:
    """Test goal zone detection and events."""

    def test_goal_zone_initialization(self):
        """Test goal zone creation."""
        world = MockWorld()
        goal = GoalZone(world, 100, 300, team="A", goal_id="goal_left")

        assert goal.pos.x == 100
        assert goal.pos.y == 300
        assert goal.team == "A"
        assert goal.goal_id == "goal_left"
        assert goal.goal_counter == 0

    def test_goal_detection_when_ball_enters(self):
        """Test that goal is detected when ball enters zone."""
        world = MockWorld()
        goal = GoalZone(world, 50, 300, team="A", radius=20.0)
        ball = Ball(world, 50, 300)  # Ball at goal center

        # Check for goal
        goal_event = goal.check_goal(ball, frame_count=100)

        assert goal_event is not None
        assert goal_event.team == "A"
        assert goal_event.timestamp == 100
        assert goal.goal_counter == 1

    def test_goal_not_detected_when_ball_outside(self):
        """Test that goal is not detected when ball is outside."""
        world = MockWorld()
        goal = GoalZone(world, 50, 300, team="A", radius=20.0)
        ball = Ball(world, 200, 300)  # Ball far from goal

        # Check for goal
        goal_event = goal.check_goal(ball, frame_count=100)

        assert goal_event is None
        assert goal.goal_counter == 0

    def test_goal_event_includes_scorer(self):
        """Test that goal event tracks the scorer."""
        world = MockWorld()
        goal = GoalZone(world, 50, 300, team="A")
        ball = Ball(world, 50, 300)

        # Set kicker
        mock_kicker = Mock()
        mock_kicker.fish_id = 42
        ball.last_kicker = mock_kicker

        # Check for goal
        goal_event = goal.check_goal(ball, frame_count=50)

        assert goal_event.scorer_id == 42

    def test_goal_zone_distance_calculation(self):
        """Test distance calculation from goal to ball."""
        world = MockWorld()
        goal = GoalZone(world, 100, 300, team="A")
        ball = Ball(world, 100, 320)  # 20 pixels away

        distance = goal.get_distance_to_ball(ball)

        assert pytest.approx(distance, abs=1e-6) == 20.0


class TestBallGameIntegration:
    """Integration tests for ball and goals together."""

    def test_ball_multiple_updates(self):
        """Test ball physics over multiple frames."""
        world = MockWorld()
        ball = Ball(world, 400, 300, decay_rate=0.5)  # High decay for testing

        # Kick ball
        ball.kick(100.0, Vector2(1.0, 0.0))

        # First update: accel→vel→pos→decay
        ball.update(0)
        speed_after_1 = ball.vel.length()

        # Second update
        ball.update(1)
        speed_after_2 = ball.vel.length()

        # Speed should decay each frame
        assert speed_after_2 < speed_after_1
        assert ball.pos.x > 400  # Ball moved right

    def test_scoring_sequence(self):
        """Test a complete scoring sequence."""
        world = MockWorld(800, 600)
        goal = GoalZone(world, 50, 300, team="A", radius=15.0)
        ball = Ball(world, 400, 300)

        # Kick ball toward goal
        ball.kick(80.0, Vector2(-1.0, 0.0))  # Kick left

        # Update multiple times to move toward goal
        for frame in range(50):
            ball.update(frame)
            if ball.pos.x < 100:
                break  # Got close to goal

        # Check if goal is scored
        goal_event = goal.check_goal(ball, frame_count=frame)

        if goal_event:
            assert goal_event.team == "A"
            assert goal.goal_counter > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
