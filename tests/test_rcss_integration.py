"""End-to-end integration test for RCSS loop.

This test verifies the full cycle:
Action -> Adapter -> UDP -> FakeServer -> UDP -> Adapter -> Observation
"""

import socket
import threading
import time
import pytest
from typing import cast

from core.policies.soccer_interfaces import SoccerAction, Vector2D
from core.worlds.soccer.rcssserver_adapter import RCSSServerAdapter, SocketInterface
from tests.fakes.fake_rcssserver import FakeRCSSServer


class RealSocketAdapter:
    """Real UDP socket wrapper for testing adapter against FakeServer."""
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set timeout to match what adapter expects (non-blockingish)
        self.sock.settimeout(0.1)
        
    def send(self, data: str, addr: tuple[str, int]) -> None:
        self.sock.sendto(data.encode('utf-8'), addr)
        
    def recv(self, bufsize: int) -> tuple[str, tuple[str, int]]:
        data, addr = self.sock.recvfrom(bufsize)
        return data.decode('utf-8'), addr
        
    def close(self):
        self.sock.close()


@pytest.fixture
def fake_server():
    """Fixture that starts a FakeRCSSServer."""
    server = FakeRCSSServer(port=6000)
    server.start()
    yield server
    server.stop()


def test_rcss_integration_loop(fake_server):
    """Test the full action-command-observation loop."""
    
    # 1. Initialize Adapter with RealSocket (connecting to localhost:6000)
    adapter = RCSSServerAdapter(
        team_name="TestTeam",
        num_players=1,
        server_port=6000,
        socket_factory=lambda: cast(SocketInterface, RealSocketAdapter())
    )
    
    # 2. Reset (connects socket)
    adapter.reset()
    
    # Give it a moment to stabilize
    time.sleep(0.1)
    
    # 3. Send an action
    # Move forward and kick
    actions = {
        "left_1": {
            "move_target": {"x": 10.0, "y": 0.0},
            "kick_power": 0.5,
            "kick_angle": 0.0
        }
    }
    
    # 4. Step adapter (sends commands, tries to recv)
    result = adapter.step(actions)
    
    # Assert commands were received by server
    # Expected: (dash ...) and (kick ...)
    # Note: init command might also be in the list if we implemented it fully
    time.sleep(0.1) # Wait for UDP
    
    received = fake_server.received_commands
    assert any("dash" in cmd for cmd in received), f"Server didn't receive dash: {received}"
    assert any("kick" in cmd for cmd in received), f"Server didn't receive kick: {received}"
    
    # 5. Make server send an observation
    # Ball is at (10, 0), player is at (0, 0) facing 0
    # Relative ball pos: distance 10, dir 0
    fake_server.send_see(time_step=1, objects_str="((b) 10 0)")
    
    # 6. Step adapter again to receive observation
    result2 = adapter.step(actions)
    
    # 7. Assert observation updated global state
    # Adapter should have updated ball state
    # obs_by_agent[...] returns a dict from SoccerObservation.to_dict()
    # Keys include: position, velocity, ball_position, ball_velocity...
    ball_pos = result2.obs_by_agent["left_1"]["ball_position"]
    
    # Ball should be roughly at (10, 0)
    # The adapter estimates absolute position from estimated player position + polar observation
    # Player starts at (-20, 0) by default in adapter.reset() for player 1
    # So if ball is 10 ahead, it should be at (-10, 0)
    
    assert abs(ball_pos["x"] - (-10.0)) < 1.0, f"Ball X wrong: {ball_pos}"
    assert abs(ball_pos["y"] - 0.0) < 1.0, f"Ball Y wrong: {ball_pos}"
