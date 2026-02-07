"""Unified broadcast system for all world types.

This module provides broadcast functionality for sending real-time updates
to connected WebSocket clients using world-aware broadcast adapters.

The broadcast system uses a single loop pattern for all world types,
with world-type-specific behavior delegated to the adapter/runner.
"""

import asyncio
import logging
import os
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union

from backend.runner.runner_protocol import RunnerProtocol
from core.config.display import FRAME_RATE

if TYPE_CHECKING:
    from backend.world_broadcast_adapter import WorldBroadcastAdapter

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


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_flag(name: str) -> bool:
    return os.getenv(name, "0").strip().lower() in ("1", "true", "yes", "on")


# =============================================================================
# Unified broadcast for world adapters
# =============================================================================


async def broadcast_updates_for_world(
    adapter: "WorldBroadcastAdapter",
    world_id: Optional[str] = None,
    stream_id: str = "default",
) -> None:
    """Broadcast simulation updates to all clients connected to a world.

    This is the unified broadcast function that works with any broadcast adapter.

    Args:
        adapter: The broadcast adapter to send updates for
        world_id: Optional world ID for logging
        stream_id: Identifier for the broadcast stream (default "default")
    """
    resolved_world_id = world_id or getattr(adapter, "world_id", None) or "unknown"
    logger.info(
        "broadcast_updates[%s:%s]: Task started",
        resolved_world_id[:8],
        stream_id,
    )

    frame_count = 0
    last_sent_frame = -1
    last_sent_at = 0.0
    last_debug_log = time.perf_counter()
    slow_send_windows: Dict[object, Tuple[int, float]] = {}
    send_time_total_ms = 0.0
    send_time_count = 0
    timeout_count = 0
    dropped_frames = 0

    broadcast_hz = _get_env_float("BROADCAST_HZ", 15.0)
    if broadcast_hz <= 0:
        broadcast_hz = 15.0
    broadcast_interval = 1.0 / broadcast_hz
    idle_sleep = max(0.05, _get_env_float("BROADCAST_IDLE_SLEEP", 0.35))
    send_timeout = max(0.05, _get_env_float("BROADCAST_SEND_TIMEOUT", 0.15))
    slow_send_strikes = max(1, _get_env_int("BROADCAST_SLOW_SEND_STRIKES", 10))
    slow_send_window = max(1.0, _get_env_float("BROADCAST_SLOW_SEND_WINDOW_SECONDS", 30.0))
    debug_enabled = _env_flag("BROADCAST_DEBUG")

    try:
        while True:
            try:
                frame_count += 1
                clients = adapter.connected_clients
                if not clients:
                    await asyncio.sleep(idle_sleep)
                    continue

                for client in list(slow_send_windows):
                    if client not in clients:
                        slow_send_windows.pop(client, None)

                now = time.perf_counter()
                time_since_last = now - last_sent_at
                if time_since_last < broadcast_interval:
                    dropped_frames += 1
                    await asyncio.sleep(min(broadcast_interval - time_since_last, 1 / FRAME_RATE))
                    continue

                if frame_count % 60 == 0:
                    logger.debug(
                        "broadcast_updates[%s]: Frame %d, clients: %d",
                        resolved_world_id[:8],
                        frame_count,
                        len(clients),
                    )

                try:
                    get_start = time.perf_counter()
                    state = await adapter.get_state_async(force_full=False, allow_delta=True)
                    get_ms = (time.perf_counter() - get_start) * 1000
                except Exception as e:
                    logger.error(
                        "broadcast_updates[%s]: Error getting simulation state: %s",
                        resolved_world_id[:8],
                        e,
                        exc_info=True,
                    )
                    await asyncio.sleep(1 / FRAME_RATE)
                    continue

                if state.frame == last_sent_frame:
                    dropped_frames += 1
                    await asyncio.sleep(1 / FRAME_RATE)
                    continue

                last_sent_frame = state.frame

                try:
                    serialize_start = time.perf_counter()
                    state_payload = adapter.serialize_state(state)
                    serialize_ms = (time.perf_counter() - serialize_start) * 1000
                except Exception as e:
                    logger.error(
                        "broadcast_updates[%s]: Error serializing state to JSON: %s",
                        resolved_world_id[:8],
                        e,
                        exc_info=True,
                    )
                    await asyncio.sleep(1 / FRAME_RATE)
                    continue

                async def _send_with_timeout(client):
                    try:
                        await asyncio.wait_for(
                            client.send_bytes(state_payload),  # noqa: B023
                            timeout=send_timeout,
                        )
                        return None
                    except asyncio.TimeoutError:
                        return "timeout"
                    except RuntimeError as exc:
                        # Starlette raises RuntimeError if sending to a closed socket
                        if 'Cannot call "send" once a close message has been sent' in str(exc):
                            return "disconnected"
                        return exc
                    except Exception as exc:
                        return exc

                disconnected = set()
                send_start = time.perf_counter()
                clients_snapshot = list(clients)
                send_results = await asyncio.gather(
                    *(_send_with_timeout(client) for client in clients_snapshot),
                    return_exceptions=False,
                )
                send_ms = (time.perf_counter() - send_start) * 1000
                last_sent_at = time.perf_counter()

                now = time.perf_counter()
                for client, result in zip(clients_snapshot, send_results):
                    if result is None:
                        if client in slow_send_windows:
                            strikes, window_start = slow_send_windows[client]
                            if (now - window_start) > slow_send_window:
                                slow_send_windows.pop(client, None)
                        continue

                    if result == "timeout":
                        timeout_count += 1
                        strikes, window_start = slow_send_windows.get(client, (0, now))
                        if (now - window_start) > slow_send_window:
                            window_start = now
                            strikes = 0
                        strikes += 1
                        slow_send_windows[client] = (strikes, window_start)
                        if strikes >= slow_send_strikes:
                            disconnected.add(client)
                        continue

                    if result == "disconnected":
                        disconnected.add(client)
                        continue

                    logger.warning(
                        "broadcast_updates[%s]: Error sending to client, marking for removal: %s",
                        resolved_world_id[:8],
                        result,
                    )
                    disconnected.add(client)

                send_time_total_ms += send_ms
                send_time_count += 1

                total_ms = get_ms + serialize_ms + send_ms
                if total_ms > 50:
                    logger.warning(
                        "broadcast_updates[%s]: SLOW get=%.0fms ser=%.0fms send=%.0fms (payload: %d bytes, clients: %d)",
                        resolved_world_id[:8],
                        get_ms,
                        serialize_ms,
                        send_ms,
                        len(state_payload),
                        len(clients),
                    )

                if debug_enabled and (now - last_debug_log) >= 5.0:
                    avg_send_ms = send_time_total_ms / send_time_count if send_time_count else 0.0
                    logger.info(
                        "broadcast_updates[%s]: perf avg_send=%.1fms timeouts=%d dropped_frames=%d clients=%d",
                        resolved_world_id[:8],
                        avg_send_ms,
                        timeout_count,
                        dropped_frames,
                        len(clients),
                    )
                    last_debug_log = now
                    send_time_total_ms = 0.0
                    send_time_count = 0
                    timeout_count = 0
                    dropped_frames = 0

                if disconnected:
                    logger.info(
                        "broadcast_updates[%s]: Removing %d disconnected clients",
                        resolved_world_id[:8],
                        len(disconnected),
                    )
                    for client in disconnected:
                        adapter.remove_client(client)
                        slow_send_windows.pop(client, None)
                        close_task = asyncio.create_task(client.close())
                        close_task.add_done_callback(_handle_task_exception)

            except asyncio.CancelledError:
                logger.info("broadcast_updates[%s]: Task cancelled", resolved_world_id[:8])
                raise
            except Exception as e:
                logger.error(
                    "broadcast_updates[%s]: Unexpected error in main loop: %s",
                    resolved_world_id[:8],
                    e,
                    exc_info=True,
                )
                await asyncio.sleep(1 / FRAME_RATE)
                continue

            try:
                await asyncio.sleep(1 / FRAME_RATE)
            except asyncio.CancelledError:
                logger.info(
                    "broadcast_updates[%s]: Task cancelled during sleep", resolved_world_id[:8]
                )
                raise

    except asyncio.CancelledError:
        logger.info("broadcast_updates[%s]: Task cancelled (outer handler)", resolved_world_id[:8])
        raise
    except Exception as e:
        logger.error(
            "broadcast_updates[%s]: Fatal error, task exiting: %s",
            resolved_world_id[:8],
            e,
            exc_info=True,
        )
        raise
    finally:
        logger.info("broadcast_updates[%s]: Task ended", resolved_world_id[:8])


# =============================================================================
# Broadcast task management
# =============================================================================

# Track broadcast tasks per world/stream
_broadcast_tasks: Dict[Tuple[str, str], asyncio.Task] = {}
# Locks to prevent race conditions when creating broadcast tasks
_broadcast_locks: Dict[Tuple[str, str], asyncio.Lock] = {}


async def start_broadcast_for_world(
    runner_or_adapter: Union[RunnerProtocol, "WorldBroadcastAdapter"],
    world_id: Optional[str] = None,
    stream_id: str = "default",
) -> asyncio.Task:
    """Start a broadcast task for a world.

    Args:
        runner_or_adapter: Either a RunnerProtocol (will be wrapped) or a WorldBroadcastAdapter
        world_id: Optional world ID (required if passing a runner)
        stream_id: Identifier for the broadcast stream (default "default")

    Returns:
        The asyncio Task for the broadcast loop
    """
    from backend.world_broadcast_adapter import (WorldBroadcastAdapter,
                                                 WorldSnapshotAdapter)

    # If we got a runner, wrap it in an adapter
    if isinstance(runner_or_adapter, RunnerProtocol) and not isinstance(
        runner_or_adapter, WorldBroadcastAdapter
    ):
        if world_id is None:
            world_id = getattr(runner_or_adapter, "world_id", None)
        if world_id is None:
            raise ValueError("world_id is required when passing a runner")

        adapter = WorldSnapshotAdapter(
            world_id=world_id,
            runner=runner_or_adapter,
            world_type=getattr(runner_or_adapter, "world_type", "tank"),
            mode_id=getattr(runner_or_adapter, "mode_id", "tank"),
            view_mode=getattr(runner_or_adapter, "view_mode", "side"),
            step_on_access=False,  # Tank worlds run their own loop
        )
    else:
        adapter = runner_or_adapter  # type: ignore

    resolved_world_id = world_id or getattr(adapter, "world_id", None) or "unknown"
    key = (resolved_world_id, stream_id)

    if key not in _broadcast_locks:
        _broadcast_locks[key] = asyncio.Lock()

    async with _broadcast_locks[key]:
        if key in _broadcast_tasks and not _broadcast_tasks[key].done():
            return _broadcast_tasks[key]

        task = asyncio.create_task(
            broadcast_updates_for_world(
                adapter,
                world_id=resolved_world_id,
                stream_id=stream_id,
            ),
            name=f"broadcast_{resolved_world_id[:8]}_{stream_id}",
        )
        task.add_done_callback(_handle_task_exception)
        _broadcast_tasks[key] = task
        return task


async def stop_broadcast_for_world(world_id: str, stream_id: Optional[str] = None) -> None:
    """Stop the broadcast task for a world.

    Args:
        world_id: The world ID to stop broadcasting for
        stream_id: Optional stream ID (stops all streams if omitted)
    """
    if stream_id is None:
        keys = [key for key in _broadcast_tasks if key[0] == world_id]
    else:
        keys = [(world_id, stream_id)]

    for key in keys:
        task = _broadcast_tasks.pop(key, None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def get_broadcast_task(world_id: str, stream_id: Optional[str] = None) -> Optional[asyncio.Task]:
    """Get the broadcast task for a world if it exists.

    Args:
        world_id: The world ID
        stream_id: Optional stream ID

    Returns:
        The broadcast task if exists and running, None otherwise
    """
    if stream_id is None:
        for key, task in _broadcast_tasks.items():
            if key[0] == world_id and not task.done():
                return task
        return None

    existing_task = _broadcast_tasks.get((world_id, stream_id))
    if existing_task and not existing_task.done():
        return existing_task
    return None


def get_active_broadcast_count() -> int:
    """Get the number of active broadcast tasks.

    Returns:
        Number of running broadcast tasks
    """
    return sum(1 for task in _broadcast_tasks.values() if not task.done())
