"""Socket interface abstraction for dependency injection in rcssserver adapter.

This module provides the socket protocol and a fake implementation for testing,
separated from the main adapter to keep modules focused and under size limits.
"""

import logging
from typing import List, Protocol, Tuple

logger = logging.getLogger(__name__)


class SocketInterface(Protocol):
    """Protocol for socket communication (allows fake sockets for testing)."""

    def send(self, data: str, addr: Tuple[str, int]) -> None:
        """Send data to address."""
        ...

    def recv(self, bufsize: int) -> Tuple[str, Tuple[str, int]]:
        """Receive data from socket."""
        ...

    def close(self) -> None:
        """Close the socket."""
        ...


class FakeSocket:
    """Fake socket implementation for testing without server.

    This allows testing the adapter logic without requiring rcssserver.
    It stores sent commands and can be configured to return canned responses.
    """

    def __init__(self):
        """Initialize fake socket."""
        self.sent_commands: List[str] = []
        self.response_queue: List[str] = []
        self.closed = False

    def send(self, data: str, addr: Tuple[str, int]) -> None:
        """Store sent command."""
        if self.closed:
            raise RuntimeError("Socket is closed")
        self.sent_commands.append(data)
        logger.debug(f"FakeSocket.send: {data} to {addr}")

    def recv(self, bufsize: int) -> Tuple[str, Tuple[str, int]]:
        """Return next queued response or empty string."""
        if self.closed:
            raise RuntimeError("Socket is closed")

        if self.response_queue:
            response = self.response_queue.pop(0)
            return (response, ("localhost", 6000))
        return ("", ("localhost", 6000))

    def close(self) -> None:
        """Mark socket as closed."""
        self.closed = True
        logger.debug("FakeSocket closed")

    def queue_response(self, response: str) -> None:
        """Queue a response to be returned by recv()."""
        self.response_queue.append(response)
