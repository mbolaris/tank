"""Tests for runtime auto-save enrollment of persistent worlds."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("pytest_asyncio")

from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.server_client import ServerClient
from backend.startup_manager import StartupManager
from backend.world_manager import WorldManager


@pytest.fixture
def startup_manager() -> StartupManager:
    """Create a startup manager with mocked external services."""
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
    )


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

        assert startup_manager.world_manager.delete_world(instance.world_id) is True
        await asyncio.sleep(0.05)

        assert instance.world_id not in startup_manager.auto_save_service._tasks
    finally:
        await startup_manager.shutdown()
