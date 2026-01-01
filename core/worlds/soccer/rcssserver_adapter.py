"""RoboCup Soccer Simulator (rcssserver) adapter with testable socket abstraction.

This module provides an adapter for connecting to rcssserver with clean separation of:
- Transport layer (UDP sockets with dependency injection for testing)
- Protocol layer (message parsing and command building)
- Policy layer (action decision making)

The adapter can run in two modes:
1. Fake socket mode (for testing without server)
2. Real socket mode (for actual rcssserver connection)

References:
- RoboCup Soccer Simulator: https://github.com/rcsoccersim/rcssserver
- Default server port: UDP 6000
- Protocol: text-based commands over UDP
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Protocol

from core.policies.soccer_interfaces import (
    BallState,
    PlayerID,
    PlayerState,
    SoccerAction,
    SoccerObservation,
    Vector2D,
)
from core.worlds.interfaces import MultiAgentWorldBackend, StepResult
from core.worlds.soccer.config import SoccerWorldConfig
from core.worlds.soccer.rcss_protocol import (
    SeeInfo,
    SenseBodyInfo,
    action_to_commands,
    build_init_command,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Socket abstraction for dependency injection
# ============================================================================


class SocketInterface(Protocol):
    """Protocol for socket communication (allows fake sockets for testing)."""

    def send(self, data: str, addr: tuple[str, int]) -> None:
        """Send data to address."""
        ...

    def recv(self, bufsize: int) -> tuple[str, tuple[str, int]]:
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

    def send(self, data: str, addr: tuple[str, int]) -> None:
        """Store sent command."""
        if self.closed:
            raise RuntimeError("Socket is closed")
        self.sent_commands.append(data)
        logger.debug(f"FakeSocket.send: {data} to {addr}")

    def recv(self, bufsize: int) -> tuple[str, tuple[str, int]]:
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


# ============================================================================
# RCSSServer Adapter
# ============================================================================


class RCSSServerAdapter(MultiAgentWorldBackend):
    """Adapter for RoboCup Soccer Simulator (rcssserver) with testable design.

    This adapter provides clean separation of concerns:
    - Transport: UDP socket communication (real or fake)
    - Protocol: Message parsing and command building
    - Policy: Action decision making (delegated to external policies)

    The adapter can be tested without rcssserver by using FakeSocket.

    Args:
        server_host: rcssserver hostname (default: localhost)
        server_port: rcssserver port (default: 6000)
        team_name: Name of the team
        num_players: Number of players to connect (1-11)
        config: Soccer world configuration (for compatibility)
        socket_factory: Factory function to create socket (default: FakeSocket)

    Example (testing mode):
        >>> adapter = RCSSServerAdapter(
        ...     team_name="TestTeam",
        ...     num_players=1,
        ...     socket_factory=FakeSocket
        ... )
        >>> result = adapter.reset()
        >>> # Adapter is ready but not connected to real server

    Example (real server mode - future):
        >>> adapter = RCSSServerAdapter(
        ...     team_name="MyTeam",
        ...     num_players=11,
        ...     socket_factory=RealSocket  # Not implemented yet
        ... )
    """

    def __init__(
        self,
        server_host: str = "localhost",
        server_port: int = 6000,
        team_name: str = "TankTeam",
        num_players: int = 11,
        config: Optional[SoccerWorldConfig] = None,
        socket_factory: Callable[[], SocketInterface] = FakeSocket,
        **kwargs,
    ):
        """Initialize rcssserver adapter.

        Args:
            server_host: Hostname of rcssserver
            server_port: UDP port of rcssserver
            team_name: Team name for initialization
            num_players: Number of players to spawn
            config: Configuration (for compatibility with training world)
            socket_factory: Factory to create socket (FakeSocket or RealSocket)
            **kwargs: Additional config overrides
        """
        self.server_host = server_host
        self.server_port = server_port
        self.team_name = team_name
        self.num_players = num_players
        self.config = config or SoccerWorldConfig(**kwargs)
        self.socket_factory = socket_factory

        # Transport layer
        self._socket: Optional[SocketInterface] = None

        # Game state
        self._frame = 0
        self._player_states: Dict[PlayerID, PlayerState] = {}
        self._ball_state: Optional[BallState] = None
        self._play_mode = "before_kick_off"
        self._last_see_info: Dict[PlayerID, Optional[SeeInfo]] = {}
        self._last_sense_info: Dict[PlayerID, Optional[SenseBodyInfo]] = {}

        # Protocol support
        self.supports_fast_step = False  # rcssserver doesn't support fast step

        logger.info(
            f"RCSSServerAdapter initialized: team={team_name}, "
            f"players={num_players}, socket={socket_factory.__name__}"
        )

    def reset(
        self, seed: Optional[int] = None, config: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        """Reset by initializing connection state.

        In fake socket mode: Just resets internal state
        In real socket mode (future): Connects to server and initializes players

        Args:
            seed: Random seed (not used in rcssserver mode)
            config: Soccer-specific configuration overrides

        Returns:
            StepResult with initial observations and snapshot
        """
        # Create socket
        self._socket = self.socket_factory()

        # Reset state
        self._frame = 0
        self._player_states = {}
        self._ball_state = BallState(position=Vector2D(0.0, 0.0), velocity=Vector2D(0.0, 0.0))
        self._play_mode = "before_kick_off"
        self._last_see_info = {}
        self._last_sense_info = {}

        # Initialize player states (placeholder positions)
        for i in range(self.num_players):
            player_id = f"left_{i + 1}"
            self._player_states[player_id] = PlayerState(
                player_id=player_id,
                team="left",
                position=Vector2D(-20.0 + i * 5, 0.0),
                velocity=Vector2D(0.0, 0.0),
                stamina=1.0,
                facing_angle=0.0,
            )
            self._last_see_info[player_id] = None
            self._last_sense_info[player_id] = None

        # In real mode, would send init commands here
        if isinstance(self._socket, FakeSocket):
            logger.debug("Fake socket mode: skipping server initialization")
        else:
            # Future: Send init commands to server
            for i in range(self.num_players):
                init_cmd = build_init_command(self.team_name, version=15)
                self._socket.send(init_cmd, (self.server_host, self.server_port))

        logger.info(f"RCSSServerAdapter reset complete: {self.num_players} players")

        return StepResult(
            obs_by_agent=self._build_observations(),
            snapshot=self._build_snapshot(),
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._frame, "mode": "rcssserver"},
        )

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> StepResult:
        """Execute one simulation step by communicating with rcssserver.

        In fake socket mode: Processes actions and updates internal state
        In real socket mode (future): Sends commands and receives observations

        Args:
            actions_by_agent: Dict mapping player_id to action dict

        Returns:
            StepResult with observations, events, metrics, and done flag
        """
        # Process actions and send commands
        if actions_by_agent:
            self._process_actions(actions_by_agent)

        # In real mode, would receive and parse server messages here
        if isinstance(self._socket, FakeSocket):
            # Fake mode: simulate minimal updates
            self._simulate_fake_step()
        else:
            # Future: Receive see/sense_body messages and parse them
            self._receive_and_parse_messages()

        # Increment frame
        self._frame += 1

        # Build result
        return StepResult(
            obs_by_agent=self._build_observations(),
            snapshot=self._build_snapshot(),
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._frame},
        )

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current world state for rendering."""
        return self._build_snapshot()

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current simulation metrics."""
        return {
            "frame": self._frame,
            "num_players": len(self._player_states),
            "play_mode": self._play_mode,
            "mode": "rcssserver",
        }

    # =========================================================================
    # Internal methods
    # =========================================================================

    def _process_actions(self, actions_by_agent: Dict[str, Any]) -> None:
        """Process actions from agents and send commands to server."""
        for player_id, action_data in actions_by_agent.items():
            if player_id not in self._player_states:
                continue

            player_state = self._player_states[player_id]

            # Parse action
            try:
                action = SoccerAction.from_dict(action_data)
            except Exception as e:
                logger.warning(f"Invalid action for {player_id}: {e}")
                continue

            # Translate to commands
            commands = action_to_commands(action, player_state)

            # Send commands
            for cmd in commands:
                if self._socket:
                    self._socket.send(cmd, (self.server_host, self.server_port))
                    logger.debug(f"Sent command for {player_id}: {cmd}")

    def _simulate_fake_step(self) -> None:
        """Simulate a minimal step in fake socket mode (for testing)."""
        # In fake mode, just maintain current state
        # Real implementation would parse server messages
        pass

    def _receive_and_parse_messages(self) -> None:
        """Receive and parse messages from rcssserver (future implementation)."""
        # Future: Receive see/sense_body messages
        # Parse them using rcss_protocol functions
        # Update _player_states and _ball_state
        if not self._socket:
            return

        # Example structure (not implemented):
        # msg, addr = self._socket.recv(8192)
        # if msg.startswith("(see"):
        #     see_info = parse_see_message(msg)
        #     # Update state based on see_info
        # elif msg.startswith("(sense_body"):
        #     sense_info = parse_sense_body_message(msg)
        #     # Update state based on sense_info
        pass

    def _build_observations(self) -> Dict[PlayerID, Dict[str, Any]]:
        """Build observations for all players."""
        observations = {}

        for player_id, player_state in self._player_states.items():
            # Get teammates and opponents
            teammates = [
                p
                for pid, p in self._player_states.items()
                if p.team == player_state.team and pid != player_id
            ]
            opponents = [p for p in self._player_states.values() if p.team != player_state.team]

            # Build observation
            obs = SoccerObservation(
                self_state=player_state,
                ball=self._ball_state,
                teammates=teammates,
                opponents=opponents,
                game_time=self._frame / 10.0,  # rcssserver runs at 10 Hz
                play_mode=self._play_mode,
                field_bounds=(105.0, 68.0),  # Standard field size
            )

            observations[player_id] = obs.to_dict()

        return observations

    def _build_snapshot(self) -> Dict[str, Any]:
        """Build snapshot for rendering/persistence."""
        return {
            "frame": self._frame,
            "ball": {
                "x": self._ball_state.position.x if self._ball_state else 0.0,
                "y": self._ball_state.position.y if self._ball_state else 0.0,
                "vx": self._ball_state.velocity.x if self._ball_state else 0.0,
                "vy": self._ball_state.velocity.y if self._ball_state else 0.0,
            },
            "players": [
                {
                    "id": player.player_id,
                    "team": player.team,
                    "x": player.position.x,
                    "y": player.position.y,
                    "vx": player.velocity.x,
                    "vy": player.velocity.y,
                    "facing": player.facing_angle,
                    "stamina": player.stamina,
                }
                for player in self._player_states.values()
            ],
            "field": {
                "width": 105.0,
                "height": 68.0,
                "goal_width": 7.32,
            },
            "play_mode": self._play_mode,
        }

    # =========================================================================
    # Protocol methods for world-agnostic backend support
    # =========================================================================

    @property
    def is_paused(self) -> bool:
        """Whether the simulation is paused (protocol method)."""
        return False

    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state (protocol method)."""
        pass  # rcssserver doesn't support pausing

    def get_entities_for_snapshot(self) -> List[Any]:
        """Get entities for snapshot building (protocol method)."""
        return []  # Soccer uses different rendering model

    def capture_state_for_save(self) -> Dict[str, Any]:
        """Capture complete world state for persistence (protocol method)."""
        return {}  # rcssserver matches are ephemeral

    def restore_state_from_save(self, state: Dict[str, Any]) -> None:
        """Restore world state from a saved snapshot (protocol method)."""
        pass  # rcssserver matches are ephemeral

    def __del__(self):
        """Cleanup socket on deletion."""
        if self._socket:
            self._socket.close()
