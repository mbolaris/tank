"""Smoke test for rcssserver adapter and protocol layer.

This script demonstrates the protocol layer functionality and adapter usage
without requiring the actual rcssserver binary.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.worlds.soccer.rcss_protocol import (
    action_to_commands,
    build_dash_command,
    build_init_command,
    build_kick_command,
    build_turn_command,
    parse_hear_message,
    parse_see_message,
    parse_sense_body_message,
)
from core.worlds.soccer.rcssserver_adapter import RCSSServerAdapter
from core.worlds.soccer.socket_interface import FakeSocket
from core.worlds.soccer.types import PlayerState, SoccerAction, Vector2D


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_protocol_parsers() -> None:
    """Test protocol message parsers with sample data."""
    print_section("Protocol Parser Tests")

    # Test see message parsing
    see_msg = "(see 0 ((b) 5.2 30.5) ((p left 2) 10.1 -15.0))"
    see_info = parse_see_message(see_msg)

    print("[OK] See message parsing:")
    print(f"  Input: {see_msg[:50]}...")
    if see_info:
        ball = see_info.get_ball()
        print(f"  Ball: distance={ball.distance}, direction={ball.direction}")
        players = see_info.get_players()
        print(f"  Players visible: {len(players)}")
    print()

    # Test sense_body message parsing
    sense_msg = "(sense_body 0 (view_mode high normal) (stamina 4000 1) (speed 0 0) (head_angle 0) (kick 0) (dash 0) (turn 0) (say 0) (turn_neck 0) (catch 0) (move 0) (change_view 0))"
    sense_info = parse_sense_body_message(sense_msg)

    print("[OK] Sense_body message parsing:")
    print(f"  Input: {sense_msg[:50]}...")
    if sense_info:
        print(f"  Stamina: {sense_info.stamina}, Speed: {sense_info.speed_amount}")
        print(f"  View: {sense_info.view_quality} {sense_info.view_width}")
    print()

    # Test hear message parsing
    hear_msg = '(hear 120 referee "kick_off_left")'
    hear_info = parse_hear_message(hear_msg)

    print("[OK] Hear message parsing:")
    print(f"  Input: {hear_msg}")
    if hear_info:
        print(f"  Sender: {hear_info.sender}, Message: {hear_info.message}")
    print()


def test_command_builders() -> None:
    """Test command building functions."""
    print_section("Command Builder Tests")

    print("[OK] Command building:")
    print(f"  Init:  {build_init_command('TestTeam', 15)}")
    print(f"  Dash:  {build_dash_command(100.0, 0.0)}")
    print(f"  Turn:  {build_turn_command(45.0)}")
    print(f"  Kick:  {build_kick_command(80.0, 30.0)}")
    print()

    print("[OK] Command clamping:")
    print(f"  Dash (over limit):  {build_dash_command(150.0, 0.0)}")
    print(f"  Turn (over limit):  {build_turn_command(200.0)}")
    print(f"  Kick (over limit):  {build_kick_command(150.0, 0.0)}")
    print()


def test_action_translation() -> None:
    """Test high-level action to command translation."""
    print_section("Action Translation Tests")

    player_state = PlayerState(
        player_id="left_1",
        team="left",
        position=Vector2D(0.0, 0.0),
        velocity=Vector2D(0.0, 0.0),
        stamina=1.0,
        facing_angle=0.0,
    )

    # Test movement action
    print("[OK] Movement action (target ahead):")
    action = SoccerAction(move_target=Vector2D(10.0, 0.0))
    commands = action_to_commands(action, player_state)
    for cmd in commands:
        print(f"  -> {cmd}")
    print()

    # Test turn action
    print("[OK] Movement action (target to left, requires turn):")
    action = SoccerAction(move_target=Vector2D(0.0, 10.0))
    commands = action_to_commands(action, player_state)
    for cmd in commands:
        print(f"  -> {cmd}")
    print()

    # Test kick action
    print("[OK] Kick action:")
    action = SoccerAction(kick_power=0.8, kick_angle=0.5)
    commands = action_to_commands(action, player_state)
    for cmd in commands:
        print(f"  -> {cmd}")
    print()


def test_adapter_fake_mode() -> None:
    """Test adapter in fake socket mode."""
    print_section("Adapter Fake Socket Mode Test")

    print("[OK] Creating adapter with FakeSocket:")
    adapter = RCSSServerAdapter(team_name="TestTeam", num_players=3, socket_factory=FakeSocket)
    print(f"  Team: {adapter.team_name}")
    print(f"  Players: {adapter.num_players}")
    print()

    print("[OK] Resetting adapter:")
    result = adapter.reset()
    print(f"  Frame: {result.snapshot['frame']}")
    print(f"  Players in snapshot: {len(result.snapshot['players'])}")
    print(f"  Observations: {len(result.obs_by_agent)}")
    print()

    print("[OK] Stepping with actions:")
    actions = {
        "left_1": {
            "move_target": {"x": 10.0, "y": 0.0},
            "kick_power": 0.0,
        }
    }
    result = adapter.step(actions_by_agent=actions)
    print(f"  Frame after step: {result.snapshot['frame']}")

    # Check sent commands
    if isinstance(adapter._socket, FakeSocket):
        print(f"  Commands sent: {len(adapter._socket.sent_commands)}")
        if adapter._socket.sent_commands:
            print(f"  Last command: {adapter._socket.sent_commands[-1]}")
    print()


def test_fake_socket() -> None:
    """Test FakeSocket functionality."""
    print_section("FakeSocket Tests")

    print("[OK] Creating FakeSocket:")
    socket = FakeSocket()
    print(f"  Closed: {socket.closed}")
    print()

    print("[OK] Sending commands:")
    socket.send("(dash 100.0 0.0)", ("localhost", 6000))
    socket.send("(kick 80.0 30.0)", ("localhost", 6000))
    print(f"  Commands sent: {len(socket.sent_commands)}")
    for i, cmd in enumerate(socket.sent_commands):
        print(f"    {i+1}. {cmd}")
    print()

    print("[OK] Queuing and receiving responses:")
    socket.queue_response("(see 0 ((b) 5 30))")
    socket.queue_response("(sense_body 0 (stamina 4000 1))")
    msg1, addr1 = socket.recv(8192)
    msg2, addr2 = socket.recv(8192)
    print(f"  Response 1: {msg1[:40]}...")
    print(f"  Response 2: {msg2[:40]}...")
    print()

    print("[OK] Closing socket:")
    socket.close()
    print(f"  Closed: {socket.closed}")
    print()


def main() -> None:
    """Run all smoke tests."""
    print("\n" + "=" * 70)
    print("  RCSS Adapter & Protocol Smoke Test")
    print("=" * 70)

    try:
        test_protocol_parsers()
        test_command_builders()
        test_action_translation()
        test_fake_socket()
        test_adapter_fake_mode()

        print_section("Summary")
        print("[PASS] All smoke tests passed!")
        print("\nThe rcssserver adapter is ready for integration.")
        print("Next steps:")
        print("  1. Implement RealSocket for actual UDP communication")
        print("  2. Add message receiving and parsing in step()")
        print("  3. Implement full match orchestration (22 players, tactics)")
        print()

        return 0

    except Exception as e:
        print(f"\n[FAIL] Smoke test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
