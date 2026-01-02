"""Fake rcssserver implementation for testing.

This module provides a deterministic, scriptable server that mimics rcssserver
behavior over UDP or direct python calls. It is designed for integration testing
without requiring a compiled rcssserver binary.
"""

import logging
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FakeRCSSServer:
    """Fake rcssserver that speaks the Robocup Soccer Protocol.
    
    This server listens on a local UDP port and responds to standard commands.
    It can be scripted to send specific observations sequence.
    """
    
    def __init__(self, port: int = 6000):
        self.port = port
        self.running = False
        self.clients: Dict[Tuple[str, int], str] = {}  # (ip, port) -> team_name
        self.socket: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.received_commands: List[str] = []
        
        # Scripted behavior
        self.auto_response_enabled = True
        self.time_step = 0
        
    def start(self):
        """Start the server in a background thread."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("localhost", self.port))
        self.socket.settimeout(0.1)
        self.running = True
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"FakeRCSSServer started on port {self.port}")

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.socket:
            self.socket.close()
        logger.info("FakeRCSSServer stopped")

    def _run_loop(self):
        """Main server loop."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = data.decode("utf-8").strip()
                self._handle_message(message, addr)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in FakeRCSSServer loop: {e}")

    def _handle_message(self, message: str, addr: Tuple[str, int]):
        """Handle incoming message."""
        self.received_commands.append(message)
        
        # Parse minimal commands needed for handshake
        if message.startswith("(init"):
            # Format: (init TeamName (version V))
            parts = message.split()
            team_name = parts[1]
            self.clients[addr] = team_name
            
            # Send init response
            # (init Side UniformNum PlayMode)
            side = "l" if len(self.clients) % 2 != 0 else "r"
            unum = (len(self.clients) + 1) // 2
            response = f"(init {side} {unum} before_kick_off)"
            self._send(response, addr)
            
            # Send initial server params (abbreviated)
            self._send("(server_param (goal_width 14.02))", addr)
            self._send("(player_param (player_size 0.3))", addr)
            self._send("(player_type (id 0) (player_speed_max 1.05))", addr)

        elif self.auto_response_enabled:
            # For other commands, we might want to auto-respond with sense_body/see
            pass

    def send_sense_body(self, time_step: int = -1):
        """Broadcast sense_body message to all clients."""
        if time_step < 0:
            time_step = self.time_step
            
        msg = f"(sense_body {time_step} (view_mode high normal) (stamina 4000 1) (speed 0 0) (head_angle 0) (kick 0) (dash 0) (turn 0) (say 0) (turn_neck 0) (catch 0) (move 0) (change_view 0))"
        self._broadcast(msg)

    def send_see(self, time_step: int = -1, objects_str: str = ""):
        """Broadcast see message to all clients.
        
        Args:
            time_step: Simulation step
            objects_str: string content inside the see message, e.g. "((b) 10 0)"
        """
        if time_step < 0:
            time_step = self.time_step
            
        if not objects_str:
            # Default empty see message
            objects_str = ""
            
        msg = f"(see {time_step} {objects_str})"
        self._broadcast(msg)

    def _send(self, message: str, addr: Tuple[str, int]):
        """Send raw string to address."""
        if self.socket:
            self.socket.sendto(message.encode("utf-8"), addr)

    def _broadcast(self, message: str):
        """Send to all connected clients."""
        for addr in self.clients:
            self._send(message, addr)
