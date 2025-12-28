
import pytest
from unittest.mock import MagicMock, patch
from backend.simulation_runner import SimulationRunner

class TestSimulationRunnerCommands:
    @pytest.fixture
    def runner(self):
        """Create a SimulationRunner with mocked world."""
        with patch('backend.simulation_runner.TankWorld') as MockWorld:
            import random
            # Configure mock world
            mock_world_instance = MockWorld.return_value
            # Use a real RNG for Food creation (require_rng needs environment.rng)
            mock_world_instance.rng = random.Random(42)
            mock_world_instance.environment = MagicMock()
            mock_world_instance.environment._rng = random.Random(42)
            mock_world_instance.ecosystem = MagicMock()
            mock_world_instance.entities_list = []
            
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
        runner.world.entities_list = [] # No fish
        result = runner.handle_command("start_poker")
        assert result["success"] is False
        assert "Need at least 3 fish" in result["error"]

    def test_poker_action_no_game(self, runner):
        runner.handle_command("poker_action", {"action": "fold"})
        # Should return error as no game is active
        # The result depends on implementation, but likely no error dict
        # Actually my implementation returns _create_error_response
        pass # If it doesn't crash it's good, checking return value:
        result = runner.handle_command("poker_action", {"action": "fold"})
        assert result["success"] is False
        assert "No poker game active" in result["error"]
