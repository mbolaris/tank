"""Fake RCSS Server for testing.

This module provides a deterministic fake implementation of the rcssserver
network protocol to allow end-to-end testing of the RCSS adapter and world
without requiring a real server process.

NOTE: This fake server is currently NOT USED because the legacy soccer world
stack (core/worlds/soccer/) was removed in the RCSS-Lite consolidation.
It can be restored if real rcssserver integration is needed later.
"""

import logging
from collections import deque
from typing import Protocol

logger = logging.getLogger(__name__)


class SocketInterface(Protocol):
    """Protocol for socket-like objects (needed for type hints)."""

    def send(self, data: str, addr: tuple[str, int]) -> None: ...

    def recv(self, bufsize: int) -> str: ...

    def close(self) -> None: ...


class FakeRCSSServer:
    """A fake RCSS server that responds to client commands deterministically.

    It implements the SocketInterface explicitly so it can be injected into
    RCSSServerAdapter.
    """

    def __init__(self, script: list[tuple[str, str]] | None = None):
        """Initialize the fake server.

        Args:
            script: Optional list of (expected_command_prefix, response) tuples.
                    If provided, verifies commands match expectations.
        """
        self._sent_commands: list[str] = []
        self._response_queue: deque[str] = deque()
        self._script = deque(script) if script else None
        self._connected = True
        self._time = 0

    def send(self, data: str, addr: tuple[str, int]) -> None:
        """Receive data from client (adapter)."""
        if not self._connected:
            raise BrokenPipeError("Fake socket closed")

        decoded = data
        self._sent_commands.append(decoded)
        logger.debug(f"FakeServer received: {decoded}")

        # Verify against script if one exists
        if self._script:
            if not self._script:
                logger.warning(f"Unexpected command received after script end: {decoded}")
            else:
                prefix, response = self._script.popleft()
                # Basic prefix check (e.g. "(init" matches "(init TankTeam ...)")
                if not decoded.startswith(prefix):
                    logger.error(
                        f"Script mismatch! Expected startswith '{prefix}', " f"got '{decoded}'"
                    )

                if response:
                    self._response_queue.append(response)
        else:
            # Default auto-responses for basic protocol handshake
            if decoded.startswith("(init"):
                # Respond with init confirmation + server/player params + see
                self._response_queue.append(self._build_init_response(decoded))
                self._response_queue.append(self._build_server_param_response())
                self._response_queue.append(self._build_player_param_response())
                self._response_queue.append(self._build_sense_body(0))
                self._response_queue.append(self._build_see(0))
            elif decoded.startswith("(move"):
                # Move command just gets a sense/see update
                # (Actual server wouldn't send see immediately, but for test
                # speed we do)
                pass
            else:
                # Regular step
                pass

    def recv(self, bufsize: int) -> str:
        """Send data to client (adapter)."""
        if not self._connected:
            return ""

        if self._response_queue:
            return self._response_queue.popleft()
        return ""

    def close(self) -> None:
        self._connected = False

    # --- Test Helpers ---

    def queue_sense_body(self, time: int, stamina: float = 4000) -> None:
        self._response_queue.append(self._build_sense_body(time, stamina))

    def queue_see(self, time: int, objects: list[str] | None = None) -> None:
        self._response_queue.append(self._build_see(time, objects))

    def get_last_command(self) -> str | None:
        return self._sent_commands[-1] if self._sent_commands else None

    # --- Response Builders ---

    def _build_init_response(self, init_cmd: str) -> str:
        side = "l"  # Always assign to left side in fake server
        unum = 1  # Simple hardcoded unum
        play_mode = "before_kick_off"
        return f"(init {side} {unum} {play_mode})"

    def _build_server_param_response(self) -> str:
        return "(server_param (goal_width 14.02) (stamina_max 4000))"

    def _build_player_param_response(self) -> str:
        return "(player_param (player_speed_max 1.05) (stamina_inc_max 45))"

    def _build_sense_body(self, time: int, stamina: float = 4000) -> str:
        return (
            f"(sense_body {time} (view_mode high normal) (stamina {stamina} 1) "
            f"(speed 0 0) (head_angle 0) (kick 0) (dash 0) (turn 0) (say 0) "
            f"(turn_neck 0) (catch 0) (move 0) (change_view 0))"
        )

    def _build_see(self, time: int, objects: list[str] | None = None) -> str:
        if objects is None:
            # Default: ball + goal
            objects = ["((b) 10 0)", "((g r) 50 0)"]

        objs_str = " ".join(objects)
        return f"(see {time} {objs_str})"
