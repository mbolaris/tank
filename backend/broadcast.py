
import asyncio
import logging
import time
from contextlib import suppress
from typing import Dict

from backend.simulation_manager import SimulationManager
from core.config.display import FRAME_RATE

logger = logging.getLogger("backend.broadcast")


def _handle_task_exception(task: asyncio.Task) -> None:
    """Handle exceptions from background tasks."""
    try:
        exc = task.exception()
        if exc is not None:
            logger.error(
                f"Unhandled exception in task {task.get_name()}: {exc}",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
    except asyncio.CancelledError:
        logger.debug(f"Task {task.get_name()} was cancelled")
    except Exception as e:
        logger.error(f"Error getting task exception: {e}", exc_info=True)


async def broadcast_updates_for_tank(manager: SimulationManager):
    """Broadcast simulation updates to all clients connected to a specific tank.

    Args:
        manager: The SimulationManager to broadcast updates for
    """
    tank_id = manager.tank_id
    logger.info("broadcast_updates[%s]: Task started", tank_id[:8])

    # Keep simulation paused until at least one client connects.
    # This avoids running multiple tanks at full speed in the background
    # (important for maintaining 30 FPS on the active tank).

    frame_count = 0
    last_sent_frame = -1

    try:
        while True:
            try:
                frame_count += 1
                clients = manager.connected_clients

                if clients:
                    if frame_count % 60 == 0:  # Log every 60 frames (~2 seconds)
                        logger.debug(
                            "broadcast_updates[%s]: Frame %d, clients: %d",
                            tank_id[:8],
                            frame_count,
                            len(clients),
                        )

                    try:
                        # Get current state (delta compression handled by manager)
                        state = await manager.get_state_async()
                    except Exception as e:
                        logger.error(
                            "broadcast_updates[%s]: Error getting simulation state: %s",
                            tank_id[:8],
                            e,
                            exc_info=True,
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    if state.frame == last_sent_frame:
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    last_sent_frame = state.frame

                    try:
                        serialize_start = time.perf_counter()
                        state_payload = manager.serialize_state(state)
                        serialize_ms = (time.perf_counter() - serialize_start) * 1000
                        if serialize_ms > 10:
                            logger.warning(
                                "broadcast_updates[%s]: Serialization exceeded budget %.2f ms (frame %s)",
                                tank_id[:8],
                                serialize_ms,
                                state.frame,
                            )
                    except Exception as e:
                        logger.error(
                            "broadcast_updates[%s]: Error serializing state to JSON: %s",
                            tank_id[:8],
                            e,
                            exc_info=True,
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    # Broadcast to all clients of this tank
                    disconnected = set()
                    send_start = time.perf_counter()
                    for client in list(clients):  # Copy to avoid modification during iteration
                        try:
                            await client.send_bytes(state_payload)
                        except Exception as e:
                            logger.warning(
                                "broadcast_updates[%s]: Error sending to client, marking for removal: %s",
                                tank_id[:8],
                                e,
                            )
                            disconnected.add(client)

                    send_ms = (time.perf_counter() - send_start) * 1000
                    if send_ms > 100:
                        logger.warning(
                            "broadcast_updates[%s]: Broadcasting to %s clients took %.2f ms",
                            tank_id[:8],
                            len(clients),
                            send_ms,
                        )

                    # Remove disconnected clients
                    if disconnected:
                        logger.info(
                            "broadcast_updates[%s]: Removing %d disconnected clients",
                            tank_id[:8],
                            len(disconnected),
                        )
                        for client in disconnected:
                            manager.remove_client(client)

            except asyncio.CancelledError:
                logger.info("broadcast_updates[%s]: Task cancelled", tank_id[:8])
                raise
            except Exception as e:
                logger.error(
                    "broadcast_updates[%s]: Unexpected error in main loop: %s",
                    tank_id[:8],
                    e,
                    exc_info=True,
                )
                # Continue running even if there's an error
                await asyncio.sleep(1 / FRAME_RATE)
                continue

            # Wait for next frame
            try:
                await asyncio.sleep(1 / FRAME_RATE)
            except asyncio.CancelledError:
                logger.info("broadcast_updates[%s]: Task cancelled during sleep", tank_id[:8])
                raise

    except asyncio.CancelledError:
        logger.info("broadcast_updates[%s]: Task cancelled (outer handler)", tank_id[:8])
        raise
    except Exception as e:
        logger.error(
            "broadcast_updates[%s]: Fatal error, task exiting: %s",
            tank_id[:8],
            e,
            exc_info=True,
        )
        raise
    finally:
        logger.info("broadcast_updates[%s]: Task ended", tank_id[:8])


# Track broadcast tasks per tank
_broadcast_tasks: Dict[str, asyncio.Task] = {}
# Locks to prevent race conditions when creating broadcast tasks
_broadcast_locks: Dict[str, asyncio.Lock] = {}


async def start_broadcast_for_tank(manager: SimulationManager) -> asyncio.Task:
    """Start a broadcast task for a tank.

    Args:
        manager: The SimulationManager to broadcast for

    Returns:
        The asyncio Task for the broadcast loop
    """
    tank_id = manager.tank_id

    # Create lock for this tank if it doesn't exist
    if tank_id not in _broadcast_locks:
        _broadcast_locks[tank_id] = asyncio.Lock()

    async with _broadcast_locks[tank_id]:
        # Check again inside the lock to avoid creating duplicate tasks
        if tank_id in _broadcast_tasks and not _broadcast_tasks[tank_id].done():
            return _broadcast_tasks[tank_id]

        task = asyncio.create_task(
            broadcast_updates_for_tank(manager),
            name=f"broadcast_{tank_id[:8]}",
        )
        task.add_done_callback(_handle_task_exception)
        _broadcast_tasks[tank_id] = task
        return task


async def stop_broadcast_for_tank(tank_id: str) -> None:
    """Stop the broadcast task for a tank.

    Args:
        tank_id: The tank ID to stop broadcasting for
    """
    task = _broadcast_tasks.pop(tank_id, None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
