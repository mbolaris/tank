"""Tests for WorldManager broadcast scheduling."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestWorldManagerBroadcastScheduling:
    """Verify broadcast callbacks are scheduled for all world types."""

    def test_generic_world_schedules_broadcast(self) -> None:
        """Creating a petri world should call start_broadcast_callback."""
        from backend.world_manager import WorldManager

        manager = WorldManager()
        mock_start = AsyncMock()
        mock_stop = AsyncMock()
        manager.set_broadcast_callbacks(mock_start, mock_stop)

        # Mock the event loop
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Create a petri world (soccer is now a minigame, not a world mode)
            _instance = manager.create_world(
                world_type="petri",
                name="Test Petri",
                seed=42,
            )

            # Verify create_task was called for broadcast
            assert mock_loop.create_task.called
            call_args = mock_loop.create_task.call_args
            assert "broadcast_start" in call_args.kwargs.get("name", "")

    def test_tank_world_schedules_broadcast(self) -> None:
        """Creating a tank world should also call start_broadcast_callback."""
        from backend.world_manager import WorldManager

        manager = WorldManager()
        mock_start = AsyncMock()
        mock_stop = AsyncMock()
        manager.set_broadcast_callbacks(mock_start, mock_stop)

        # Mock the event loop
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Create a tank world
            instance = manager.create_world(
                world_type="tank",
                name="Test Tank",
                seed=42,
            )

            # Cleanup - stop the simulation thread
            if hasattr(instance.runner, "stop"):
                instance.runner.stop()

            # Verify create_task was called for broadcast
            assert mock_loop.create_task.called

    def test_broadcast_not_scheduled_without_callback(self) -> None:
        """If no callback is set, world creation should still succeed."""
        from backend.world_manager import WorldManager

        manager = WorldManager()
        # Don't set broadcast callbacks

        # Create a petri world - should not raise
        # (soccer is now a minigame, not a world mode)
        instance = manager.create_world(
            world_type="petri",
            name="Test Petri",
            seed=42,
        )

        assert instance is not None
        assert instance.world_type == "petri"
