"""Tests for rcssserver protocol parsing and command building.

This module contains golden tests using real-ish message samples
based on the rcssserver protocol documentation.
"""

import math

import pytest

from core.policies.soccer_interfaces import PlayerState, SoccerAction, Vector2D
from core.worlds.soccer.rcss_protocol import (
    HearInfo,
    ObjectInfo,
    SeeInfo,
    SenseBodyInfo,
    action_to_commands,
    build_dash_command,
    build_init_command,
    build_kick_command,
    build_move_command,
    build_turn_command,
    estimate_position_from_polar,
    parse_hear_message,
    parse_see_message,
    parse_sense_body_message,
)


# ============================================================================
# Golden test fixtures - real-ish message samples
# ============================================================================


SAMPLE_SEE_MESSAGE = """(see 0 ((f c) 58.7 0) ((f c t) 64.1 -7) ((f c b) 64.1 7) 
((f l t) 64.8 -39) ((f l b) 41.1 39) ((f r t) 64.8 39) ((f r b) 41.1 -39) 
((f g l t) 58.3 -20) ((f g l b) 58.3 20) ((f p l t) 41.6 -45) ((f p l b) 41.6 45) 
((g l) 58.3 0) ((f t l 50) 47.6 -11) ((f t l 40) 42.4 -17) ((f t l 30) 37.1 -24) 
((f t l 20) 31.8 -33) ((f t l 10) 26.5 -45) ((f t 0) 58.7 -90) ((f t r 10) 26.5 45) 
((f t r 20) 31.8 33) ((f t r 30) 37.1 24) ((f t r 40) 42.4 17) ((f t r 50) 47.6 11) 
((f b l 50) 47.6 11) ((f b l 40) 42.4 17) ((f b l 30) 37.1 24) ((f b l 20) 31.8 33) 
((f b l 10) 26.5 45) ((f b 0) 58.7 90) ((f b r 10) 26.5 -45) ((f b r 20) 31.8 -33) 
((f b r 30) 37.1 -24) ((f b r 40) 42.4 -17) ((f b r 50) 47.6 -11) ((g r) 58.3 -180) 
((f g r t) 58.3 160) ((f g r b) 58.3 -160) ((f p r t) 41.6 135) ((f p r b) 41.6 -135) 
((b) 5.2 30.5) ((p left 2) 10.1 -15.0 0.5 -2.0 45.0 90.0) ((p right 5) 20.3 60))"""

SAMPLE_SENSE_BODY_MESSAGE = """(sense_body 0 (view_mode high normal) (stamina 4000 1) 
(speed 0 0) (head_angle 0) (kick 0) (dash 0) (turn 0) (say 0) (turn_neck 0) 
(catch 0) (move 0) (change_view 0))"""

SAMPLE_HEAR_REFEREE = '(hear 120 referee "kick_off_left")'
SAMPLE_HEAR_PLAYER = '(hear 125 -45 "pass to center")'
SAMPLE_HEAR_SELF = '(hear 130 self "test message")'


# ============================================================================
# Parser tests
# ============================================================================


class TestSeeMessageParser:
    """Tests for see message parsing."""

    def test_parse_see_message_basic(self):
        """Test parsing a basic see message."""
        result = parse_see_message(SAMPLE_SEE_MESSAGE)

        assert result is not None
        assert isinstance(result, SeeInfo)
        assert result.time == 0
        assert len(result.objects) > 0

    def test_parse_see_message_extracts_ball(self):
        """Test that ball is correctly extracted."""
        result = parse_see_message(SAMPLE_SEE_MESSAGE)

        ball = result.get_ball()
        assert ball is not None
        assert ball.obj_type == "ball"
        assert ball.distance == 5.2
        assert ball.direction == 30.5

    def test_parse_see_message_extracts_players(self):
        """Test that players are correctly extracted."""
        result = parse_see_message(SAMPLE_SEE_MESSAGE)

        players = result.get_players()
        assert len(players) >= 2

        # Check left team player
        left_players = result.get_players(team="left")
        assert len(left_players) >= 1
        left_player = left_players[0]
        assert left_player.obj_type == "player"
        assert left_player.team == "left"
        assert left_player.uniform_number == 2
        assert left_player.distance == 10.1
        assert left_player.direction == -15.0

    def test_parse_see_message_with_detailed_player_info(self):
        """Test parsing player with full detail (dist_change, dir_change, body/head dir)."""
        result = parse_see_message(SAMPLE_SEE_MESSAGE)

        left_players = result.get_players(team="left")
        player = left_players[0]

        # This player has full detail in the sample
        assert player.dist_change == 0.5
        assert player.dir_change == -2.0
        assert player.body_facing_dir == 45.0
        assert player.head_facing_dir == 90.0

    def test_parse_see_message_with_direction_only(self):
        """Test parsing objects with only direction (too far for distance)."""
        # Create a message with direction-only object
        msg = "(see 10 ((g r) 45))"
        result = parse_see_message(msg)

        assert result is not None
        assert result.time == 10
        assert len(result.objects) == 1
        obj = result.objects[0]
        assert obj.obj_type == "goal"
        assert obj.distance is None
        assert obj.direction == 45

    def test_parse_see_message_invalid(self):
        """Test that invalid messages return None."""
        assert parse_see_message("") is None
        assert parse_see_message("(invalid message)") is None
        assert parse_see_message("(hear 0 referee \"test\")") is None


class TestSenseBodyMessageParser:
    """Tests for sense_body message parsing."""

    def test_parse_sense_body_basic(self):
        """Test parsing a basic sense_body message."""
        result = parse_sense_body_message(SAMPLE_SENSE_BODY_MESSAGE)

        assert result is not None
        assert isinstance(result, SenseBodyInfo)
        assert result.time == 0

    def test_parse_sense_body_view_mode(self):
        """Test view mode extraction."""
        result = parse_sense_body_message(SAMPLE_SENSE_BODY_MESSAGE)

        assert result.view_quality == "high"
        assert result.view_width == "normal"

    def test_parse_sense_body_stamina(self):
        """Test stamina and effort extraction."""
        result = parse_sense_body_message(SAMPLE_SENSE_BODY_MESSAGE)

        assert result.stamina == 4000.0
        assert result.effort == 1.0

    def test_parse_sense_body_speed(self):
        """Test speed extraction."""
        result = parse_sense_body_message(SAMPLE_SENSE_BODY_MESSAGE)

        assert result.speed_amount == 0.0
        assert result.speed_direction == 0.0

    def test_parse_sense_body_action_counts(self):
        """Test action count extraction."""
        result = parse_sense_body_message(SAMPLE_SENSE_BODY_MESSAGE)

        assert result.kick_count == 0
        assert result.dash_count == 0
        assert result.turn_count == 0
        assert result.say_count == 0

    def test_parse_sense_body_with_movement(self):
        """Test parsing sense_body with non-zero speed."""
        msg = "(sense_body 10 (view_mode high normal) (stamina 3500 0.9) (speed 1.5 45) (head_angle 30) (kick 1) (dash 5) (turn 2) (say 0) (turn_neck 1) (catch 0) (move 0) (change_view 0))"
        result = parse_sense_body_message(msg)

        assert result is not None
        assert result.time == 10
        assert result.stamina == 3500.0
        assert result.effort == 0.9
        assert result.speed_amount == 1.5
        assert result.speed_direction == 45.0
        assert result.head_angle == 30.0
        assert result.kick_count == 1
        assert result.dash_count == 5
        assert result.turn_count == 2

    def test_parse_sense_body_invalid(self):
        """Test that invalid messages return None."""
        assert parse_sense_body_message("") is None
        assert parse_sense_body_message("(invalid)") is None
        assert parse_sense_body_message("(see 0 ((b) 5 30))") is None


class TestHearMessageParser:
    """Tests for hear message parsing."""

    def test_parse_hear_referee(self):
        """Test parsing referee message."""
        result = parse_hear_message(SAMPLE_HEAR_REFEREE)

        assert result is not None
        assert isinstance(result, HearInfo)
        assert result.time == 120
        assert result.sender == "referee"
        assert result.message == "kick_off_left"

    def test_parse_hear_player(self):
        """Test parsing player message with direction."""
        result = parse_hear_message(SAMPLE_HEAR_PLAYER)

        assert result is not None
        assert result.time == 125
        assert result.sender == "-45"
        assert result.message == "pass to center"

    def test_parse_hear_self(self):
        """Test parsing self message."""
        result = parse_hear_message(SAMPLE_HEAR_SELF)

        assert result is not None
        assert result.time == 130
        assert result.sender == "self"
        assert result.message == "test message"

    def test_parse_hear_invalid(self):
        """Test that invalid messages return None."""
        assert parse_hear_message("") is None
        assert parse_hear_message("(invalid)") is None
        assert parse_hear_message("(see 0 ((b) 5 30))") is None


# ============================================================================
# Command builder tests
# ============================================================================


class TestCommandBuilders:
    """Tests for command building functions."""

    def test_build_dash_command(self):
        """Test dash command building."""
        cmd = build_dash_command(100.0, 0.0)
        assert cmd == "(dash 100.0 0.0)"

        cmd = build_dash_command(50.0, 45.0)
        assert cmd == "(dash 50.0 45.0)"

    def test_build_dash_command_clamping(self):
        """Test that dash power is clamped."""
        cmd = build_dash_command(150.0, 0.0)
        assert cmd == "(dash 100.0 0.0)"

        cmd = build_dash_command(-150.0, 0.0)
        assert cmd == "(dash -100.0 0.0)"

        cmd = build_dash_command(50.0, 200.0)
        assert cmd == "(dash 50.0 180.0)"

    def test_build_turn_command(self):
        """Test turn command building."""
        cmd = build_turn_command(45.0)
        assert cmd == "(turn 45.0)"

        cmd = build_turn_command(-30.0)
        assert cmd == "(turn -30.0)"

    def test_build_turn_command_clamping(self):
        """Test that turn moment is clamped."""
        cmd = build_turn_command(200.0)
        assert cmd == "(turn 180.0)"

        cmd = build_turn_command(-200.0)
        assert cmd == "(turn -180.0)"

    def test_build_kick_command(self):
        """Test kick command building."""
        cmd = build_kick_command(80.0, 0.0)
        assert cmd == "(kick 80.0 0.0)"

        cmd = build_kick_command(50.0, 45.0)
        assert cmd == "(kick 50.0 45.0)"

    def test_build_kick_command_clamping(self):
        """Test that kick power is clamped."""
        cmd = build_kick_command(150.0, 0.0)
        assert cmd == "(kick 100.0 0.0)"

        cmd = build_kick_command(-10.0, 0.0)
        assert cmd == "(kick 0.0 0.0)"

    def test_build_move_command(self):
        """Test move command building."""
        cmd = build_move_command(10.5, -5.3)
        assert cmd == "(move 10.50 -5.30)"

    def test_build_init_command(self):
        """Test init command building."""
        cmd = build_init_command("TestTeam", 15)
        assert cmd == "(init TestTeam (version 15))"


# ============================================================================
# Translation tests
# ============================================================================


class TestActionTranslation:
    """Tests for action to command translation."""

    def test_action_to_commands_move_target_forward(self):
        """Test translating move_target to dash command when facing target."""
        player_state = PlayerState(
            player_id="test_1",
            team="left",
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(0.0, 0.0),
            stamina=1.0,
            facing_angle=0.0,  # Facing right
        )

        action = SoccerAction(move_target=Vector2D(10.0, 0.0))

        commands = action_to_commands(action, player_state)

        # Should dash forward (no turn needed)
        assert len(commands) == 1
        assert commands[0].startswith("(dash")

    def test_action_to_commands_move_target_requires_turn(self):
        """Test translating move_target to turn command when not facing target."""
        player_state = PlayerState(
            player_id="test_1",
            team="left",
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(0.0, 0.0),
            stamina=1.0,
            facing_angle=0.0,  # Facing right
        )

        # Target is to the left (90 degrees)
        action = SoccerAction(move_target=Vector2D(0.0, 10.0))

        commands = action_to_commands(action, player_state)

        # Should turn first
        assert len(commands) == 1
        assert commands[0].startswith("(turn")

    def test_action_to_commands_face_angle(self):
        """Test translating face_angle to turn command."""
        player_state = PlayerState(
            player_id="test_1",
            team="left",
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(0.0, 0.0),
            stamina=1.0,
            facing_angle=0.0,
        )

        # Turn 45 degrees
        action = SoccerAction(face_angle=math.radians(45))

        commands = action_to_commands(action, player_state)

        assert len(commands) == 1
        assert commands[0].startswith("(turn")
        assert "45" in commands[0]

    def test_action_to_commands_kick(self):
        """Test translating kick to kick command."""
        player_state = PlayerState(
            player_id="test_1",
            team="left",
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(0.0, 0.0),
            stamina=1.0,
            facing_angle=0.0,
        )

        action = SoccerAction(kick_power=0.8, kick_angle=math.radians(30))

        commands = action_to_commands(action, player_state)

        assert len(commands) == 1
        assert commands[0].startswith("(kick")
        assert "80" in commands[0]  # 0.8 * 100 = 80

    def test_action_to_commands_combined(self):
        """Test action with both movement and kick."""
        player_state = PlayerState(
            player_id="test_1",
            team="left",
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(0.0, 0.0),
            stamina=1.0,
            facing_angle=0.0,
        )

        action = SoccerAction(
            move_target=Vector2D(10.0, 0.0),
            kick_power=0.5,
            kick_angle=0.0,
        )

        commands = action_to_commands(action, player_state)

        # Should have dash and kick
        assert len(commands) == 2
        assert any("dash" in cmd for cmd in commands)
        assert any("kick" in cmd for cmd in commands)


# ============================================================================
# Utility function tests
# ============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_estimate_position_from_polar(self):
        """Test position estimation from polar coordinates."""
        observer_pos = Vector2D(0.0, 0.0)
        observer_facing = 0.0  # Facing right

        # Object 10 meters ahead
        pos = estimate_position_from_polar(observer_pos, observer_facing, 10.0, 0.0)
        assert abs(pos.x - 10.0) < 0.01
        assert abs(pos.y - 0.0) < 0.01

        # Object 10 meters to the left (90 degrees)
        pos = estimate_position_from_polar(observer_pos, observer_facing, 10.0, 90.0)
        assert abs(pos.x - 0.0) < 0.01
        assert abs(pos.y - 10.0) < 0.01

    def test_estimate_position_from_polar_with_observer_rotation(self):
        """Test position estimation when observer is rotated."""
        observer_pos = Vector2D(5.0, 5.0)
        observer_facing = math.radians(45)  # Facing northeast

        # Object 10 meters ahead (relative to observer)
        pos = estimate_position_from_polar(observer_pos, observer_facing, 10.0, 0.0)

        # Should be northeast of observer
        assert pos.x > observer_pos.x
        assert pos.y > observer_pos.y
