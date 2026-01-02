"""WebSocket endpoints for real-time simulation updates.

This module provides WebSocket endpoints for all world types:
- /ws and /ws/{tank_id}: Legacy tank-specific endpoints (backward compatible)
- /ws/world/{world_id}: Unified endpoint for any world type

All endpoints now work through the TankWorldAdapter for tank worlds,
ensuring consistent behavior across the codebase.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.security import websocket_limiter

if TYPE_CHECKING:
    from backend.tank_registry import TankRegistry
    from backend.world_broadcast_adapter import WorldBroadcastAdapter
    from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket connection."""
    forwarded_for = websocket.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if websocket.client:
        return websocket.client.host
    return "unknown"


async def _handle_websocket_for_adapter(
    websocket: WebSocket,
    adapter: "WorldBroadcastAdapter",
    world_id: str,
) -> None:
    """Handle WebSocket connection using TankWorldAdapter interface.

    This is the core handler that works with any world type through
    the broadcast adapter interface.

    Args:
        websocket: The WebSocket connection
        adapter: The broadcast adapter for the world
        world_id: The world ID for logging
    """
    client_ip = _get_client_ip(websocket)
    limiter_connected = False
    client_added = False

    try:
        await websocket.accept()

        if not websocket_limiter.connect(client_ip):
            await websocket.send_json(
                {"success": False, "error": "Too many WebSocket connections from this IP."}
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        limiter_connected = True

        adapter.add_client(websocket)
        client_added = True

        # Send an initial full state snapshot so new clients render immediately
        try:
            state = await adapter.get_state_async(force_full=True, allow_delta=False)
            await websocket.send_bytes(adapter.serialize_state(state))
        except Exception as exc:
            logger.warning("Failed to send initial state to %s: %s", client_ip, exc)

        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if message["type"] == "websocket.disconnect":
                break
            if message["type"] != "websocket.receive":
                continue

            raw_text = message.get("text")
            if raw_text is None and message.get("bytes"):
                try:
                    raw_text = message["bytes"].decode("utf-8")
                except UnicodeDecodeError:
                    await websocket.send_json(
                        {"success": False, "error": "Invalid message encoding."}
                    )
                    continue

            if not raw_text:
                continue

            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"success": False, "error": "Invalid JSON payload."})
                continue

            command = payload.get("command")
            if not command:
                continue

            data = payload.get("data")
            response = await adapter.handle_command_async(command, data)
            if response is not None:
                await websocket.send_text(json.dumps(response))

    except Exception:
        logger.exception("WebSocket error for client %s on world %s", client_ip, world_id[:8])
    finally:
        if client_added:
            adapter.remove_client(websocket)
        if limiter_connected:
            websocket_limiter.disconnect(client_ip)


async def _handle_websocket(
    websocket: WebSocket,
    tank_registry: "TankRegistry",
    tank_id: Optional[str] = None,
) -> None:
    """Handle WebSocket connection for tank worlds (legacy interface).

    This function wraps the tank's SimulationManager in a TankWorldAdapter
    and delegates to the unified handler.

    Args:
        websocket: The WebSocket connection
        tank_registry: The TankRegistry to get tanks from
        tank_id: Optional tank ID (uses default if not specified)
    """
    from backend.tank_world_adapter import TankWorldAdapter

    manager = tank_registry.get_tank_or_default(tank_id)

    if manager is None:
        try:
            await websocket.accept()
            await websocket.send_json({"success": False, "error": "Tank not found."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass
        return

    # Wrap in adapter for unified handling
    adapter = TankWorldAdapter(manager)
    await _handle_websocket_for_adapter(websocket, adapter, manager.tank_id)


async def _handle_websocket_for_world(
    websocket: WebSocket,
    world_manager: "WorldManager",
    world_id: str,
) -> None:
    """Handle WebSocket connection for any world type.

    This is the unified handler that works with WorldManager to support
    all world types (tank, petri, soccer).

    Args:
        websocket: The WebSocket connection
        world_manager: The WorldManager to get worlds from
        world_id: The world ID to connect to
    """
    instance = world_manager.get_world(world_id)
    if instance is None:
        try:
            await websocket.accept()
            await websocket.send_json({"success": False, "error": f"World not found: {world_id}"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass
        return

    adapter = world_manager.get_broadcast_adapter(world_id)
    if adapter is None:
        try:
            await websocket.accept()
            await websocket.send_json(
                {
                    "success": False,
                    "error": f"World type '{instance.world_type}' does not support WebSocket connections.",
                }
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass
        return

    from backend.broadcast import start_broadcast_for_world

    await start_broadcast_for_world(adapter, world_id=world_id, stream_id="world")
    await _handle_websocket_for_adapter(websocket, adapter, world_id)


def setup_router(
    tank_registry: "TankRegistry",
    world_manager: Optional["WorldManager"] = None,
) -> APIRouter:
    """Create the websocket router with registry dependencies.

    Args:
        tank_registry: The TankRegistry for legacy tank endpoints
        world_manager: Optional WorldManager for unified world endpoints

    Returns:
        Configured APIRouter
    """

    # =========================================================================
    # Legacy tank-specific endpoints (backward compatible)
    # =========================================================================

    @router.websocket("/ws")
    async def websocket_default(websocket: WebSocket) -> None:
        """WebSocket endpoint for default tank.

        This is the legacy endpoint maintained for backward compatibility.
        Connects to the default tank in the registry.
        """
        await _handle_websocket(websocket, tank_registry)

    @router.websocket("/ws/{tank_id}")
    async def websocket_tank(websocket: WebSocket, tank_id: str) -> None:
        """WebSocket endpoint for specific tank.

        This is the legacy endpoint maintained for backward compatibility.
        Connects to a specific tank by ID.
        """
        await _handle_websocket(websocket, tank_registry, tank_id=tank_id)

    # =========================================================================
    # Unified world endpoint (works with any world type)
    # =========================================================================

    if world_manager is not None:

        @router.websocket("/ws/world/{world_id}")
        async def websocket_world(websocket: WebSocket, world_id: str) -> None:
            """Unified WebSocket endpoint for any world type.

            This endpoint works with all world types (tank, petri, soccer)
            through the WorldManager interface.
            """
            await _handle_websocket_for_world(websocket, world_manager, world_id)

    return router
