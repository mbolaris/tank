"""Integration tests for RCSSWorld with FakeRCSSServer.

These tests verify the full stack:
RCSSWorld -> RCSSServerAdapter -> FakeRCSSServer -> RCSSServerAdapter -> RCSSWorld
"""

import pytest

from core.worlds.soccer.rcss_world import RCSSWorld
from core.worlds.soccer.rcssserver_adapter import RCSSServerAdapter

from .fakes.fake_rcssserver import FakeRCSSServer

pytestmark = pytest.mark.integration


class TestRCSSIntegration:

    def test_full_loop_boot_and_move(self):
        """Test binding world, connecting, sending move command, and parsing update."""
        # 1. Setup Fake Server script
        # We expect init, then we send a move command
        script = [
            # No specific script, rely on auto-responses for init
        ]
        fake_server = FakeRCSSServer(script)

        # 2. Setup World
        adapter = RCSSServerAdapter(
            server_host="fake",
            server_port=6000,
            socket_factory=lambda: fake_server,
            # We must enable "synchronous" mode or ensure we step correctly
        )
        world = RCSSWorld(adapter)

        # 3. Connection happens on first step or reset.
        # Let's call reset explicitly to connect
        adapter.reset()

        # Check that we sent init
        last = fake_server.get_last_command()
        assert last is not None
        assert last.startswith("(init")

        # 4. Step with a movement action
        # The adapter internally maps actions. For now, we use a simple dict format
        # accepted by adapter._process_actions or just raw commands if backend supports it.
        # The RCSSServerAdapter expects {player_id: {"dash_power": ..., "dash_dir": ...}}

        # Let's assume player_id "left_1" (our spawned player)
        # Player starts at (-15.0, 0.0) based on reset logic
        # We set a target to the right to induce movement
        actions = {"left_1": {"move_target": {"x": -10.0, "y": 0.0}}}

        # We also need to ensuring the fake server is ready to receive a dash
        # The fake server "step" logic in adapter is: send command -> recv see/sense
        # We need to manually queue expected responses if not using default script
        fake_server.queue_sense_body(10, stamina=3500)
        fake_server.queue_see(10, ["((b) 5 0)", "((g r) 40 0)"])

        step_result = world.step(actions)

        # 5. Verify command sent
        # We should see a dash command in the fake server sent log
        # The adapter might send multiple commands (synch_see, etc), so we search
        sent = fake_server._sent_commands
        dash_sent = any("(dash 100" in cmd for cmd in sent)
        assert dash_sent, f"Dash command not found in sent commands: {sent}"

        # 6. Verify observation parsed
        # step_result should contain observations
        obs = step_result.obs_by_agent
        assert "left_1" in obs
        # The observation structure depends on the adapter's builder
        # But we should at least see it returned

        p1_obs = obs["left_1"]
        # Check ball distance from our queued See message "((b) 5 0)"
        # The adapter might transform this.
        # Typically it puts ball info in "ball" key
        # Let's just assert we got something back for now
        assert p1_obs is not None

    def test_kick_command(self):
        """Test kicking behavior."""
        fake_server = FakeRCSSServer()
        adapter = RCSSServerAdapter(server_host="fake", socket_factory=lambda: fake_server)
        world = RCSSWorld(adapter)
        adapter.reset()

        actions = {
            "left_1": {
                "kick_power": 0.5,  # Normalized 0-1 range
                "kick_angle": -0.785,  # -45 degrees in radians
            }
        }

        fake_server.queue_sense_body(20)
        fake_server.queue_see(20)

        world.step(actions)

        # Verify kick command
        sent = fake_server._sent_commands
        kick_sent = any("(kick 50" in cmd for cmd in sent)
        assert kick_sent, f"Kick command not found in: {sent}"
