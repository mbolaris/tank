"""WebSocket endpoints for real-time simulation updates.

This module provides WebSocket endpoints for all world types:
- /ws/world/{world_id}: Unified endpoint for all world types
"""

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from backend.world_broadcast_adapter import WorldBroadcastAdapter
    from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def _get_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket connection."""
    client = websocket.client
    if client:
        return f"{client.host}:{client.port}"
    return "unknown"


async def _handle_websocket_for_adapter(
    websocket: WebSocket,
    adapter: "WorldBroadcastAdapter",
    world_id: str,
) -> None:
    """Handle WebSocket connection using WorldBroadcastAdapter interface.

    This is the core handler that works with any world type through
    the broadcast adapter interface.

    Args:
        websocket: The WebSocket connection
        adapter: The broadcast adapter for the world
        world_id: The world ID for logging
    """
    client_ip = _get_client_ip(websocket)
    logger.info("World %s: WebSocket connected from %s", world_id[:8], client_ip)

    await websocket.accept()

    try:
        # Add client to the adapter
        adapter.add_client(websocket)

        # Send initial full state
        try:
            state = await adapter.get_state_async(force_full=True, allow_delta=False)
            if state is not None:
                serialized = adapter.serialize_state(state)
                await websocket.send_bytes(serialized)
        except Exception as e:
            logger.error(
                "World %s: Error sending initial state: %s",
                world_id[:8],
                e,
                exc_info=True,
            )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                message = await websocket.receive()

                if message.get("type") == "websocket.disconnect":
                    logger.info(
                        "World %s: WebSocket disconnected from %s",
                        world_id[:8],
                        client_ip,
                    )
                    break

                # Handle text messages (commands)
                if "text" in message:
                    text = message["text"]
                    try:
                        import orjson

                        data = orjson.loads(text)
                        command = data.get("command")
                        command_data = data.get("data")

                        if command and hasattr(adapter, "handle_command_async"):
                            result = await adapter.handle_command_async(command, command_data)
                            if result is not None:
                                response = orjson.dumps(result)
                                await websocket.send_bytes(response)
                    except Exception as e:
                        logger.warning(
                            "World %s: Error processing command: %s",
                            world_id[:8],
                            e,
                        )

            except WebSocketDisconnect:
                logger.info(
                    "World %s: WebSocket disconnected from %s",
                    world_id[:8],
                    client_ip,
                )
                break
            except Exception as e:
                logger.error(
                    "World %s: WebSocket error: %s",
                    world_id[:8],
                    e,
                    exc_info=True,
                )
                break

    finally:
        adapter.remove_client(websocket)
        logger.info(
            "World %s: WebSocket cleanup complete for %s",
            world_id[:8],
            client_ip,
        )


async def _handle_websocket_for_world(
    websocket: WebSocket,
    world_manager: "WorldManager",
    world_id: str,
) -> None:
    """Handle WebSocket connection for any world type.

    This is the unified handler that works with WorldManager to support
    all world types (tank, petri).

    Args:
        websocket: The WebSocket connection
        world_manager: The WorldManager to get worlds from
        world_id: The world ID to connect to
    """
    # Handle "default" as special case
    if world_id == "default":
        default_id = world_manager.default_world_id
        if default_id is None:
            logger.warning("No default world available, rejecting connection")
            await websocket.close(code=4004)
            return
        world_id = default_id

    # Get the broadcast adapter for this world
    adapter = world_manager.get_broadcast_adapter(world_id)

    if adapter is None:
        logger.warning(
            "World not found: %s, rejecting connection",
            world_id[:8] if len(world_id) >= 8 else world_id,
        )
        await websocket.close(code=4004)
        return

    # Register client with world manager for tracking
    world_manager.add_client(world_id, websocket)

    try:
        await _handle_websocket_for_adapter(websocket, adapter, world_id)
    finally:
        world_manager.remove_client(world_id, websocket)


def setup_router(
    world_manager: "WorldManager",
) -> APIRouter:
    """Create the websocket router with WorldManager dependency.

    Args:
        world_manager: The WorldManager for unified world endpoints

    Returns:
        Configured APIRouter
    """
    router = APIRouter()

    @router.websocket("/ws/world/{world_id}")
    async def websocket_world(websocket: WebSocket, world_id: str):
        """Unified WebSocket endpoint for any world type.

        This endpoint works with all world types (tank, petri)
        through the WorldManager interface.

        Use world_id="default" to connect to the default world.
        """
        await _handle_websocket_for_world(websocket, world_manager, world_id)

    return router
