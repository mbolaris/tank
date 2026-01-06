"""Tests for soccer world backend and components.

This module tests the SoccerWorldBackendAdapter, physics engine,
and soccer-specific interfaces.
"""

import pytest

from core.worlds import StepResult, WorldRegistry
from core.worlds.soccer.backend import SoccerWorldBackendAdapter
from core.worlds.soccer.config import SoccerWorldConfig
from core.worlds.soccer.physics import Ball, FieldBounds, Player, SoccerPhysics
from core.worlds.soccer.types import (
    LegacySoccerAction,
    SoccerAction,
    Vector2D,
)


class TestSoccerWorldBackendAdapter:
    """Tests for SoccerWorldBackendAdapter."""

    def test_adapter_initialization(self):
        """Test basic adapter initialization."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        assert adapter._seed == 42
        assert adapter._ball is None
        assert adapter._frame == 0

    def test_reset_returns_step_result(self):
        """Test that reset() returns a valid StepResult."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        result = adapter.reset(seed=42)

        assert isinstance(result, StepResult)
        assert isinstance(result.obs_by_agent, dict)
        assert result.done is False
        assert "frame" in result.snapshot
        assert "ball" in result.snapshot
        assert "players" in result.snapshot

    def test_reset_creates_players_and_ball(self):
        """Test that reset() creates players and ball."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        adapter.reset(seed=42)

        # Should have 3 players per team = 6 total
        assert len(adapter._players) == 6
        assert adapter._ball is not None

        # Check player IDs
        left_players = [p for p in adapter._players.values() if p.team == "left"]
        right_players = [p for p in adapter._players.values() if p.team == "right"]
        assert len(left_players) == 3
        assert len(right_players) == 3

    def test_reset_with_different_team_sizes(self):
        """Test reset with various team sizes."""
        for team_size in [1, 3, 5, 11]:
            adapter = SoccerWorldBackendAdapter(seed=42, team_size=team_size)
            adapter.reset(seed=42)
            assert len(adapter._players) == team_size * 2

    def test_step_without_actions(self):
        """Test that step() works without any actions."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        adapter.reset(seed=42)
        result = adapter.step()

        assert isinstance(result, StepResult)
        assert result.snapshot["frame"] == 1

    def test_step_with_movement_action(self):
        """Test step with player movement actions."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        initial_snapshot = adapter.get_current_snapshot()
        initial_player = initial_snapshot["players"][0]
        initial_x = initial_player["x"]

        # Move player right (using normalized format: turn=0 to face right, dash=1 to move)
        actions = {
            "left_1": {
                "turn": 0.0,  # Already facing right
                "dash": 1.0,  # Full speed ahead
                "kick_power": 0.0,
            }
        }

        # Step several times to allow movement
        for _ in range(10):
            adapter.step(actions_by_agent=actions)

        final_snapshot = adapter.get_current_snapshot()
        final_player = final_snapshot["players"][0]
        final_x = final_player["x"]

        # Player should have moved right
        assert final_x > initial_x

    def test_step_with_kick_action(self):
        """Test step with ball kick action."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        # Position player near ball
        player = list(adapter._players.values())[0]
        player.position = Vector2D(0.0, 0.0)
        adapter._ball.position = Vector2D(0.3, 0.0)

        initial_ball_vel = adapter._ball.velocity.magnitude()

        # Kick the ball
        actions = {
            "left_1": {
                "kick_power": 1.0,
                "kick_angle": 0.0,
            }
        }
        result = adapter.step(actions_by_agent=actions)

        # Ball should be moving now
        final_ball_vel = adapter._ball.velocity.magnitude()
        assert final_ball_vel > initial_ball_vel

        # Should have kick event
        kick_events = [e for e in result.events if e["type"] == "kick"]
        assert len(kick_events) > 0

    def test_invalid_action_bounds(self):
        """Test that invalid action bounds are handled gracefully."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        # Try invalid kick power (> 1.0)
        actions = {
            "left_1": {
                "kick_power": 2.0,  # Invalid
                "kick_angle": 0.0,
            }
        }

        # Should not crash, just ignore invalid action
        result = adapter.step(actions_by_agent=actions)
        assert isinstance(result, StepResult)

    def test_goal_scoring(self):
        """Test that goals are detected and scored."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        # Place ball past the right goal line (left team scores)
        field_width = adapter._config.field_width
        adapter._ball.position = Vector2D(field_width / 2 + 1, 0.0)

        result = adapter.step()

        # Check score updated
        assert adapter._score["left"] == 1
        assert adapter._score["right"] == 0

        # Check goal event
        goal_events = [e for e in result.events if e["type"] == "goal"]
        assert len(goal_events) == 1
        assert goal_events[0]["team"] == "left"

        # Ball should be reset to center
        assert abs(adapter._ball.position.x) < 1.0
        assert abs(adapter._ball.position.y) < 1.0

    def test_observations_structure(self):
        """Test that observations have correct structure."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        result = adapter.reset(seed=42)

        # Should have observations for all 6 players
        assert len(result.obs_by_agent) == 6

        # Check observation structure for one player
        obs_dict = result.obs_by_agent["left_1"]
        assert "position" in obs_dict
        assert "velocity" in obs_dict
        assert "stamina" in obs_dict
        assert "ball_position" in obs_dict
        assert "teammates" in obs_dict
        assert "opponents" in obs_dict
        assert "game_time" in obs_dict
        assert "play_mode" in obs_dict

        # Teammates and opponents should be correct
        assert len(obs_dict["teammates"]) == 2  # 3 total - 1 self = 2
        assert len(obs_dict["opponents"]) == 3

    def test_stamina_consumption(self):
        """Test that stamina is consumed during actions."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        player = list(adapter._players.values())[0]
        initial_stamina = player.stamina

        # Position player near ball and kick
        player.position = Vector2D(0.0, 0.0)
        adapter._ball.position = Vector2D(0.3, 0.0)

        actions = {
            "left_1": {
                "kick_power": 1.0,
                "kick_angle": 0.0,
            }
        }
        adapter.step(actions_by_agent=actions)

        # Stamina should be reduced after kick
        assert player.stamina < initial_stamina

    def test_stamina_recovery(self):
        """Test that stamina recovers when not sprinting."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        player = list(adapter._players.values())[0]
        player.stamina = 50.0  # Reduce stamina
        player.velocity = Vector2D(0.0, 0.0)  # Not moving

        # Step without actions (resting)
        for _ in range(10):
            adapter.step()

        # Stamina should recover
        assert player.stamina > 50.0

    def test_calculate_rewards(self):
        """Test reward calculation for players."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        adapter.reset(seed=42)

        # Position ball in goal (left team scores)
        field_width = adapter._config.field_width
        adapter._ball.position = Vector2D(field_width / 2 + 1, 0.0)
        adapter.step()

        # Calculate rewards
        rewards = adapter.calculate_rewards()

        # Left team should get goal reward
        assert "left_1" in rewards
        assert rewards["left_1"].goal_scored > 0

    def test_deterministic_reset(self):
        """Test that reset with same seed produces identical results."""
        adapter1 = SoccerWorldBackendAdapter(seed=42, team_size=3)
        adapter2 = SoccerWorldBackendAdapter(seed=42, team_size=3)

        result1 = adapter1.reset(seed=42)
        result2 = adapter2.reset(seed=42)

        # Ball positions should match
        assert result1.snapshot["ball"]["x"] == result2.snapshot["ball"]["x"]
        assert result1.snapshot["ball"]["y"] == result2.snapshot["ball"]["y"]

        # Player count and initial positions should match
        assert len(result1.snapshot["players"]) == len(result2.snapshot["players"])

    def test_get_current_metrics(self):
        """Test get_current_metrics returns valid data."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        adapter.reset(seed=42)

        metrics = adapter.get_current_metrics()
        assert "frame" in metrics
        assert "score_left" in metrics
        assert "score_right" in metrics
        assert "num_players" in metrics
        assert metrics["num_players"] == 6

    def test_match_duration(self):
        """Test that match ends after configured duration."""
        adapter = SoccerWorldBackendAdapter(
            seed=42,
            team_size=1,
            half_time_duration=10,  # 10 frames per half = 20 total
        )
        adapter.reset(seed=42)

        result = None
        for _ in range(30):
            result = adapter.step()
            if result.done:
                break

        assert result is not None
        assert result.done is True
        assert adapter._frame >= 20

    def test_supports_fast_step(self):
        """Test that adapter supports fast step mode."""
        adapter = SoccerWorldBackendAdapter(seed=42, team_size=1)
        assert adapter.supports_fast_step is True


class TestSoccerPhysics:
    """Tests for soccer physics engine."""

    def test_ball_movement_with_friction(self):
        """Test that ball slows down due to friction."""
        ball = Ball(position=Vector2D(0, 0), velocity=Vector2D(5, 0))
        initial_speed = ball.velocity.magnitude()

        # Update with friction
        ball.update_position(friction=0.9)

        final_speed = ball.velocity.magnitude()
        assert final_speed < initial_speed
        assert ball.position.x > 0  # Ball moved

    def test_ball_stops_at_low_velocity(self):
        """Test that ball stops when velocity is very small."""
        ball = Ball(position=Vector2D(0, 0), velocity=Vector2D(0.005, 0))

        ball.update_position(friction=0.9)

        assert ball.velocity.x == 0.0
        assert ball.velocity.y == 0.0

    def test_field_bounds_goal_detection(self):
        """Test goal detection in field bounds."""
        field = FieldBounds(width=100, height=60)

        # Ball in left goal (right team scores)
        ball_pos = Vector2D(-51, 0)
        assert field.is_goal(ball_pos) == "right"

        # Ball in right goal (left team scores)
        ball_pos = Vector2D(51, 0)
        assert field.is_goal(ball_pos) == "left"

        # Ball on field (no goal)
        ball_pos = Vector2D(0, 0)
        assert field.is_goal(ball_pos) is None

        # Ball outside goal width (no goal)
        ball_pos = Vector2D(51, 50)
        assert field.is_goal(ball_pos) is None

    def test_player_can_kick_ball(self):
        """Test player kick range detection."""
        player = Player(
            player_id="test_1",
            team="left",
            position=Vector2D(0, 0),
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
        )
        ball = Ball(position=Vector2D(0.3, 0), velocity=Vector2D(0, 0))

        # Ball is within kick range
        assert player.can_kick_ball(ball, kick_range=0.5) is True

        # Ball is too far
        ball.position = Vector2D(10, 0)
        assert player.can_kick_ball(ball, kick_range=0.5) is False

    def test_physics_update_player_movement(self):
        """Test physics engine updates player movement."""
        field = FieldBounds(width=100, height=60)
        physics = SoccerPhysics(field_bounds=field)

        player = Player(
            player_id="test_1",
            team="left",
            position=Vector2D(0, 0),
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
        )

        target = Vector2D(10, 0)
        initial_x = player.position.x

        # Update movement towards target
        for _ in range(10):
            physics.update_player_movement(player, target, None)

        # Player should move towards target
        assert player.position.x > initial_x

    def test_physics_kick_ball(self):
        """Test physics engine ball kick."""
        field = FieldBounds(width=100, height=60)
        physics = SoccerPhysics(field_bounds=field)

        player = Player(
            player_id="test_1",
            team="left",
            position=Vector2D(0, 0),
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
        )
        ball = Ball(position=Vector2D(0.3, 0), velocity=Vector2D(0, 0))

        # Kick ball
        success = physics.kick_ball(player, ball, kick_power=1.0, kick_angle=0)

        assert success is True
        assert ball.velocity.magnitude() > 0

    def test_physics_kick_ball_too_far(self):
        """Test that kick fails if ball is too far."""
        field = FieldBounds(width=100, height=60)
        physics = SoccerPhysics(field_bounds=field)

        player = Player(
            player_id="test_1",
            team="left",
            position=Vector2D(0, 0),
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
        )
        ball = Ball(position=Vector2D(10, 0), velocity=Vector2D(0, 0))

        # Try to kick ball that's too far
        success = physics.kick_ball(player, ball, kick_power=1.0, kick_angle=0)

        assert success is False

    def test_player_collisions(self):
        """Test player-player collision separation."""
        field = FieldBounds(width=100, height=60)
        physics = SoccerPhysics(field_bounds=field)

        player1 = Player(
            player_id="left_1",
            team="left",
            position=Vector2D(0, 0),
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
            radius=0.3,
        )
        player2 = Player(
            player_id="right_1",
            team="right",
            position=Vector2D(0.2, 0),  # Overlapping
            velocity=Vector2D(0, 0),
            facing_angle=0,
            stamina=100,
            radius=0.3,
        )

        initial_distance = player1.distance_to(player2.position)

        # Handle collision
        physics.check_player_collisions([player1, player2])

        # Players should be separated
        final_distance = player1.distance_to(player2.position)
        assert final_distance > initial_distance


class TestSoccerInterfaces:
    """Tests for soccer interfaces and data structures."""

    def test_vector2d_magnitude(self):
        """Test Vector2D magnitude calculation."""
        v = Vector2D(3, 4)
        assert v.magnitude() == 5.0

    def test_vector2d_normalized(self):
        """Test Vector2D normalization."""
        v = Vector2D(3, 4)
        normalized = v.normalized()
        assert abs(normalized.magnitude() - 1.0) < 0.001

    def test_soccer_action_validation(self):
        """Test SoccerAction validation."""
        # Valid action
        action = SoccerAction(kick_power=0.5, kick_angle=0.5)
        assert action.is_valid() is True

        # Invalid action (kick power out of bounds)
        action = SoccerAction(kick_power=1.5, kick_angle=0)
        assert action.is_valid() is False

        action = SoccerAction(kick_power=-0.1, kick_angle=0)
        assert action.is_valid() is False

    def test_soccer_action_to_from_dict(self):
        """Test SoccerAction serialization (normalized format)."""
        action = SoccerAction(
            turn=0.5,
            dash=1.0,
            kick_power=0.8,
            kick_angle=0.5,
        )

        action_dict = action.to_dict()
        assert action_dict["kick_power"] == 0.8
        assert action_dict["turn"] == 0.5
        assert action_dict["dash"] == 1.0

        # Round trip
        restored = SoccerAction.from_dict(action_dict)
        assert restored.kick_power == action.kick_power
        assert restored.turn == action.turn

    def test_legacy_soccer_action_to_from_dict(self):
        """Test LegacySoccerAction serialization (move_target format)."""
        action = LegacySoccerAction(
            move_target=Vector2D(10, 5),
            face_angle=1.57,
            kick_power=0.8,
            kick_angle=0.5,
        )

        action_dict = action.to_dict()
        assert action_dict["kick_power"] == 0.8
        assert action_dict["move_target"]["x"] == 10
        assert action_dict["face_angle"] == 1.57

        # Round trip
        restored = LegacySoccerAction.from_dict(action_dict)
        assert restored.kick_power == action.kick_power
        assert restored.move_target.x == action.move_target.x


class TestSoccerWorldConfig:
    """Tests for soccer world configuration."""

    def test_config_defaults(self):
        """Test that config has sensible defaults."""
        config = SoccerWorldConfig()
        assert config.team_size == 11
        assert config.field_width == 105.0
        assert config.field_height == 68.0
        assert config.frame_rate == 60

    def test_config_validation(self):
        """Test config validation."""
        # Valid config
        config = SoccerWorldConfig(team_size=5)
        config.validate()  # Should not raise

        # Invalid team size
        config = SoccerWorldConfig(team_size=0)
        with pytest.raises(ValueError, match="team_size must be 1-11"):
            config.validate()

        config = SoccerWorldConfig(team_size=12)
        with pytest.raises(ValueError, match="team_size must be 1-11"):
            config.validate()

    def test_config_to_from_dict(self):
        """Test config serialization."""
        config = SoccerWorldConfig(team_size=5, field_width=80)
        config_dict = config.to_dict()

        assert config_dict["team_size"] == 5
        assert config_dict["field_width"] == 80

        # Round trip
        restored = SoccerWorldConfig.from_dict(config_dict)
        assert restored.team_size == 5
        assert restored.field_width == 80


class TestSoccerModePackIntegration:
    """Tests for soccer mode pack integration."""

    def test_create_soccer_world_via_registry(self):
        """Test creating soccer world through WorldRegistry."""
        world = WorldRegistry.create_world("soccer", seed=42, team_size=3)
        assert isinstance(world, SoccerWorldBackendAdapter)

    def test_soccer_mode_pack_config_normalization(self):
        """Test that soccer mode pack normalizes config."""
        mode_pack = WorldRegistry.get_mode_pack("soccer")
        assert mode_pack is not None

        # Test legacy key aliases
        normalized = mode_pack.configure(
            {
                "width": 120,
                "height": 80,
                "fps": 30,
                "players_per_team": 5,
            }
        )

        assert normalized["field_width"] == 120
        assert normalized["field_height"] == 80
        assert normalized["frame_rate"] == 30
        assert normalized["team_size"] == 5

        # Test defaults
        defaults_only = mode_pack.configure({})
        assert defaults_only["team_size"] == 11
        assert defaults_only["headless"] is True
