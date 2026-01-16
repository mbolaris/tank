"""World broadcast adapter for unified WebSocket updates."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from backend.runner.runner_protocol import RunnerProtocol
from core.worlds.interfaces import FAST_STEP_ACTION

if TYPE_CHECKING:
    pass  # RunnerProtocol is imported directly above

logger = logging.getLogger(__name__)


@runtime_checkable
class WorldBroadcastAdapter(Protocol):
    """Protocol for broadcast adapters used by the WebSocket loop."""

    world_id: str
    world_type: str
    mode_id: str
    view_mode: str

    @property
    def connected_clients(self) -> set[WebSocket]:
        ...

    def add_client(self, websocket: WebSocket) -> None:
        ...

    def remove_client(self, websocket: WebSocket) -> None:
        ...

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True) -> Any:
        ...

    def serialize_state(self, state: Any) -> bytes:
        ...

    async def handle_command_async(
        self, command: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        ...


class WorldSnapshotAdapter:
    """Adapter that emits world-agnostic snapshots for WebSocket broadcast.

    All runners (SimulationRunner, WorldRunner) now implement get_state()
    with a unified interface, so this adapter simply delegates to the runner.
    """

    def __init__(
        self,
        world_id: str,
        runner: RunnerProtocol,
        *,
        world_type: str,
        mode_id: str,
        view_mode: str,
        step_on_access: bool,
    ) -> None:
        self.world_id = world_id
        self.world_type = world_type
        self.mode_id = mode_id
        self.view_mode = view_mode
        self._runner = runner
        self._step_on_access = step_on_access
        self._clients: set[WebSocket] = set()
        self._state_lock = threading.Lock()

    @property
    def connected_clients(self) -> set[WebSocket]:
        self._prune_closed_clients()
        return self._clients

    def add_client(self, websocket: WebSocket) -> None:
        self._prune_closed_clients()
        self._clients.add(websocket)

    def remove_client(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        self._prune_closed_clients()

    def _prune_closed_clients(self) -> None:
        stale = {
            ws
            for ws in self._clients
            if ws.client_state not in {WebSocketState.CONNECTED, WebSocketState.CONNECTING}
        }
        if stale:
            self._clients.difference_update(stale)

    def _step_world(self) -> None:
        if not self._step_on_access:
            return
        if getattr(self._runner, "paused", False):
            return
        world = getattr(self._runner, "world", None)
        if world is not None and getattr(world, "supports_fast_step", False):
            self._runner.step(actions_by_agent={FAST_STEP_ACTION: True})
        else:
            self._runner.step()

    def get_state(self, force_full: bool = False, allow_delta: bool = True) -> Any:
        """Get current state for broadcast.

        All runners implement get_state() with the unified FullStatePayload/
        DeltaStatePayload schema, so we simply delegate to the runner.

        Args:
            force_full: Force a full snapshot (no delta)
            allow_delta: Allow delta compression if supported

        Returns:
            State payload (FullStatePayload or DeltaStatePayload)
        """
        with self._state_lock:
            if self._step_on_access:
                self._step_world()
            return self._runner.get_state(force_full=force_full, allow_delta=allow_delta)

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_state, force_full, allow_delta)

    def serialize_state(self, state: Any) -> bytes:
        """Serialize state payload to bytes for WebSocket transmission.

        All runners now return FullStatePayload or DeltaStatePayload,
        which implement to_json() for fast serialization.
        """
        # All unified payloads implement to_json()
        result = state.to_json()
        if isinstance(result, bytes):
            return result
        return result.encode("utf-8")

    async def handle_command_async(
        self, command: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        if hasattr(self._runner, "handle_command_async"):
            return await self._runner.handle_command_async(command, data)

        response = self.handle_command(command, data or {})
        return response

    def handle_command(self, command: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if command == "pause":
            if hasattr(self._runner, "paused"):
                self._runner.paused = True
            return None
        if command == "resume":
            if hasattr(self._runner, "paused"):
                self._runner.paused = False
            return None
        if command == "reset":
            seed = data.get("seed")
            config = data.get("config")
            self._runner.reset(seed=seed, config=config)
            return None
        if command == "step":
            actions = data.get("actions")
            self._runner.step(actions_by_agent=actions)
            return None

        logger.debug("Unsupported command for world %s: %s", self.world_id[:8], command)
        return {"success": False, "error": f"Unsupported command: {command}"}
