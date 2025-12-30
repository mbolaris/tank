import pytest
from unittest.mock import MagicMock, patch
from backend.simulation_runner import SimulationRunner


class TestSimulationRunnerCommands:
    @pytest.fixture
    def runner(self):
        """Create a SimulationRunner with mocked world via registry."""
        # Patch create_world to return mock world and snapshot builder
        with patch("backend.simulation_runner.create_world") as mock_create_world, patch(
            "backend.simulation_runner.get_world_metadata"
        ) as mock_get_metadata:
            import random

            # Configure mock world
            mock_world = MagicMock()
            mock_snapshot_builder = MagicMock()
            mock_create_world.return_value = (mock_world, mock_snapshot_builder)

            # Configure mock metadata
            mock_metadata = MagicMock()
            mock_metadata.view_mode = "side"
            mock_get_metadata.return_value = mock_metadata

            # Configure mock world properties
            mock_world.rng = MagicMock()
            mock_world.rng.randint.return_value = 100
            mock_world.rng.choices.return_value = ["algae"]  # Valid food type
            mock_world.environment = MagicMock()
            mock_world.environment.rng = mock_world.rng
            mock_world.ecosystem = MagicMock()
            mock_world.entities_list = []
            mock_world.paused = False
            mock_world.frame_count = 0

            runner = SimulationRunner(seed=123)
            # Mock the invalidate_state_cache method to avoid side effects
            runner._invalidate_state_cache = MagicMock()

            return runner

    def test_handle_unknown_command(self, runner):
        result = runner.handle_command("unknown_command")
        assert result["success"] is False
        assert "Unknown command" in result["error"]

    def test_pause_resume(self, runner):
        # Pause
        runner.handle_command("pause")
        assert runner.world.paused is True

        # Resume
        runner.handle_command("resume")
        assert runner.world.paused is False

    def test_add_food(self, runner):
        runner.world.rng.randint.return_value = 100
        runner.handle_command("add_food")

        # Verify entity added
        runner.world.add_entity.assert_called_once()
        args, _ = runner.world.add_entity.call_args
        entity = args[0]
        assert entity.__class__.__name__ == "Food"
        assert runner._invalidate_state_cache.called

    def test_spawn_fish(self, runner):
        runner.handle_command("spawn_fish")

        # Verify fish added
        runner.world.add_entity.assert_called_once()
        args, _ = runner.world.add_entity.call_args
        entity = args[0]
        assert entity.__class__.__name__ == "Fish"
        assert runner._invalidate_state_cache.called

    def test_reset(self, runner):
        runner.handle_command("reset")
        if hasattr(runner.world, "reset"):
            runner.world.reset.assert_called_once()
        else:
            runner.world.setup.assert_called()

        assert runner._invalidate_state_cache.called
        assert runner.world.paused is False
        assert runner.fast_forward is False

    def test_fast_forward(self, runner):
        runner.handle_command("fast_forward", {"enabled": True})
        assert runner.fast_forward is True

        runner.handle_command("fast_forward", {"enabled": False})
        assert runner.fast_forward is False

    def test_start_poker_insufficient_fish(self, runner):
        runner.world.entities_list = []  # No fish
        result = runner.handle_command("start_poker")
        assert result["success"] is False
        assert "Need at least 3 fish" in result["error"]

    def test_poker_action_no_game(self, runner):
        runner.handle_command("poker_action", {"action": "fold"})
        # Should return error as no game is active
        # The result depends on implementation, but likely no error dict
        # Actually my implementation returns _create_error_response
        pass  # If it doesn't crash it's good, checking return value:
        result = runner.handle_command("poker_action", {"action": "fold"})
        assert result["success"] is False
        assert "No poker game active" in result["error"]
