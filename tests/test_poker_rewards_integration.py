from types import SimpleNamespace
from unittest.mock import Mock

from backend.runner.command_handlers import CommandHandlerMixin


# Mock class that mimics SimulationRunner for testing the mixin
class MockRunner(CommandHandlerMixin):
    def __init__(self):
        self.world = Mock()
        self.human_poker_game = Mock()
        self.logger = Mock()


def test_apply_poker_rewards_human_win():
    runner = MockRunner()

    # Setup human win result
    result = {"fish_id": None, "pot": 100.0, "is_human": True}

    # Should safely return without error and presumably log/do nothing specific for human in this method
    runner._apply_poker_rewards(result)


def test_apply_poker_rewards_fish_win():
    runner = MockRunner()

    # Setup world entities
    fish1 = SimpleNamespace(fish_id=1, energy=100.0)
    fish2 = SimpleNamespace(fish_id=2, energy=100.0)

    # Mock world methods
    runner.world.get_entities_for_snapshot = Mock(return_value=[fish1, fish2])
    runner.world.engine = Mock()
    reproduction_service = Mock()
    reproduction_service.handle_post_poker_reproduction = Mock(return_value=None)
    runner.world.engine.reproduction_service = reproduction_service

    # Setup game players
    player1 = SimpleNamespace(is_human=False, fish_id=1)
    player2 = SimpleNamespace(is_human=False, fish_id=2)
    minnow_human = SimpleNamespace(is_human=True, fish_id=None)
    runner.human_poker_game.players = [minnow_human, player1, player2]

    # Simulate Fish #1 winning
    result = {"fish_id": 1, "pot": 50.0, "is_human": False}

    runner._apply_poker_rewards(result)

    # Assert energy reward
    assert fish1.energy == 150.0
    assert fish2.energy == 100.0

    # Assert reproduction attempt
    reproduction_service.handle_post_poker_reproduction.assert_called_once()
    # Check args
    mock_poker = reproduction_service.handle_post_poker_reproduction.call_args[0][0]
    assert mock_poker.result.winner_id == 1
    assert len(mock_poker.fish_players) == 2  # Only the two fish players


if __name__ == "__main__":
    # Manually run tests if executed as script
    try:
        test_apply_poker_rewards_human_win()
        test_apply_poker_rewards_fish_win()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
