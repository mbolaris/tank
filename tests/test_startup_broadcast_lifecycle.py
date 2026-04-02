"""End-to-end test: worlds created after startup have broadcasts stopped on shutdown."""

from __future__ import annotations

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


def _make_startup_manager() -> StartupManager:
    """Create a StartupManager wired to the real broadcast helpers."""
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
        start_broadcast_callback=start_broadcast_for_world,
        stop_broadcast_callback=stop_broadcast_for_world,
    )


@pytest.mark.asyncio
async def test_runtime_world_broadcast_stopped_on_shutdown() -> None:
    """A world created *after* startup must have its broadcast stopped on shutdown.

    Sequence:
      1. initialize() — starts broadcast for the default world
      2. create a second world at runtime
      3. verify its broadcast task exists
      4. shutdown()
      5. verify the broadcast task is gone
    """
    sm = _make_startup_manager()
    await sm.initialize(MagicMock(return_value={}))

    try:
        # Create a world after startup has completed.
        instance = sm.world_manager.create_world(
            world_type="petri",
            name="Late World",
            persistent=False,
            seed=99,
            start_paused=True,
        )
        world_id = instance.world_id

        # Give the fire-and-forget create_task a chance to register.
        await asyncio.sleep(0.05)

        # The broadcast task should now exist in the module-level registry.
        assert any(
            k[0] == world_id for k in _broadcast_tasks
        ), f"broadcast task should exist for runtime world {world_id[:8]}"

        # The world should also be tracked in StartupManager's shutdown set.
        assert world_id in sm._broadcast_task_ids, "runtime world should be in _broadcast_task_ids"
    finally:
        await sm.shutdown()

    # After shutdown, broadcast tasks for all worlds should be cleaned up.
    assert not any(
        k[0] == world_id for k in _broadcast_tasks
    ), f"broadcast task for {world_id[:8]} should be gone after shutdown"

    assert len(sm._broadcast_task_ids) == 0, "_broadcast_task_ids should be empty after shutdown"
