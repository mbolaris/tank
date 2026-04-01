"""Tests for runtime auto-save enrollment of persistent worlds."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("pytest_asyncio")

from backend.broadcast import (
    _broadcast_tasks,
    start_broadcast_for_world,
    stop_broadcast_for_world,
)
from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.server_client import ServerClient
from backend.startup_manager import StartupManager
from backend.world_manager import WorldManager


def _make_startup_manager(*, with_broadcast: bool = False) -> StartupManager:
    connection_manager = MagicMock(spec=ConnectionManager)

    discovery_service = MagicMock(spec=DiscoveryService)
    discovery_service.start = AsyncMock()
    discovery_service.stop = AsyncMock()

    server_client = MagicMock(spec=ServerClient)
    server_client.start = AsyncMock()
    server_client.close = AsyncMock()

    return StartupManager(
        world_manager=WorldManager(),
        connection_manager=connection_manager,
        discovery_service=discovery_service,
        server_client=server_client,
        server_id="test-server",
        start_broadcast_callback=start_broadcast_for_world if with_broadcast else None,
        stop_broadcast_callback=stop_broadcast_for_world if with_broadcast else None,
    )


@pytest.fixture
def startup_manager() -> StartupManager:
    """Create a startup manager with mocked external services."""
    return _make_startup_manager()


@pytest.mark.asyncio
async def test_new_persistent_world_is_enrolled_in_autosave(
    startup_manager: StartupManager,
) -> None:
    """Persistent worlds created after startup should get their own auto-save loop."""
    await startup_manager.initialize(MagicMock(return_value={}))

    try:
        assert startup_manager.auto_save_service is not None

        instance = startup_manager.world_manager.create_world(
            world_type="petri",
            name="Late Persistent World",
            persistent=True,
            seed=42,
            start_paused=True,
        )

        await asyncio.sleep(0.05)

        assert instance.world_id in startup_manager.auto_save_service._tasks
    finally:
        await startup_manager.shutdown()


@pytest.mark.asyncio
async def test_deleted_world_is_removed_from_autosave(startup_manager: StartupManager) -> None:
    """Deleting a world should cancel its dedicated auto-save task."""
    await startup_manager.initialize(MagicMock(return_value={}))

    try:
        assert startup_manager.auto_save_service is not None

        instance = startup_manager.world_manager.create_world(
            world_type="petri",
            name="Temporary Persistent World",
            persistent=True,
            seed=42,
            start_paused=True,
        )
        await asyncio.sleep(0.05)
        assert instance.world_id in startup_manager.auto_save_service._tasks

        assert await startup_manager.world_manager.delete_world_async(instance.world_id) is True

        assert instance.world_id not in startup_manager.auto_save_service._tasks
    finally:
        await startup_manager.shutdown()


@pytest.mark.asyncio
async def test_deleted_world_broadcast_task_is_stopped() -> None:
    """Deleting a world should cancel its broadcast task."""
    sm = _make_startup_manager(with_broadcast=True)
    await sm.initialize(MagicMock(return_value={}))

    try:
        instance = sm.world_manager.create_world(
            world_type="petri",
            name="Broadcast Test World",
            persistent=False,
            seed=42,
            start_paused=True,
        )
        world_id = instance.world_id

        await asyncio.sleep(0.05)
        assert any(k[0] == world_id for k in _broadcast_tasks), (
            "broadcast task should exist after world creation"
        )

        assert await sm.world_manager.delete_world_async(world_id) is True

        assert not any(k[0] == world_id for k in _broadcast_tasks), (
            "broadcast task should be gone after world deletion"
        )
    finally:
        await sm.shutdown()
