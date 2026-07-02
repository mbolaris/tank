"""Tests for WorldManager broadcast scheduling."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _close_dangling_coroutines(mock_loop: MagicMock) -> None:
    """Close any unawaited coroutines captured by a mocked event-loop's create_task.

    When production code passes an AsyncMock-produced coroutine to
    ``loop.create_task()``, the mock captures but never awaits it, provoking a
    ``RuntimeWarning: coroutine ... was never awaited`` during GC.
    This helper finds those captured coroutines and closes them explicitly.
    """
    for call in mock_loop.create_task.call_args_list:
        if call.args:
            coro = call.args[0]
            if inspect.iscoroutine(coro):
                coro.close()


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

            # Close the unawaited coroutine that AsyncMock produced for the
            # mocked create_task call, preventing 'coroutine was never awaited'.
            _close_dangling_coroutines(mock_loop)

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

            # Close the unawaited coroutine that AsyncMock produced.
            _close_dangling_coroutines(mock_loop)

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

    @pytest.mark.asyncio
    async def test_delete_world_async_waits_for_broadcast_shutdown(self) -> None:
        """Async deletion should not return until broadcast shutdown finishes."""
        from backend.world_manager import WorldManager

        manager = WorldManager()
        mock_start = AsyncMock()
        stop_started = asyncio.Event()
        allow_stop = asyncio.Event()

        async def mock_stop(_world_id: str) -> None:
            stop_started.set()
            await allow_stop.wait()

        manager.set_broadcast_callbacks(mock_start, mock_stop)
        instance = manager.create_world(
            world_type="petri",
            name="Delete Test Petri",
            seed=42,
        )

        delete_task = asyncio.create_task(manager.delete_world_async(instance.world_id))
        await stop_started.wait()

        assert not delete_task.done()

        allow_stop.set()
        assert await delete_task is True
