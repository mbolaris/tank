"""WebSocket endpoints for real-time simulation updates."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.security import websocket_limiter
from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client_ip(websocket: WebSocket) -> str:
    forwarded_for = websocket.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if websocket.client:
        return websocket.client.host
    return "unknown"


async def _handle_websocket(
    websocket: WebSocket,
    tank_registry: TankRegistry,
    tank_id: Optional[str] = None,
) -> None:
    client_ip = _get_client_ip(websocket)
    manager = tank_registry.get_tank_or_default(tank_id)
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

        if manager is None:
            await websocket.send_json({"success": False, "error": "Tank not found."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        manager.add_client(websocket)
        client_added = True

        # Send an initial full state snapshot so new clients render immediately.
        try:
            state = await manager.get_state_async(force_full=True, allow_delta=False)
            await websocket.send_bytes(manager.serialize_state(state))
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
            response = await manager.handle_command_async(command, data)
            if response is not None:
                await websocket.send_text(json.dumps(response))
    except Exception:
        logger.exception("WebSocket error for client %s", client_ip)
    finally:
        if client_added and manager is not None:
            manager.remove_client(websocket)
        if limiter_connected:
            websocket_limiter.disconnect(client_ip)


def setup_router(tank_registry: TankRegistry) -> APIRouter:
    """Create the websocket router with registry dependencies."""

    @router.websocket("/ws")
    async def websocket_default(websocket: WebSocket) -> None:
        await _handle_websocket(websocket, tank_registry)

    @router.websocket("/ws/{tank_id}")
    async def websocket_tank(websocket: WebSocket, tank_id: str) -> None:
        await _handle_websocket(websocket, tank_registry, tank_id=tank_id)

    return router
