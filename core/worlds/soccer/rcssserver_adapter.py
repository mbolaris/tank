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
from typing import Any, Callable, Dict, List, Optional

from core.worlds.interfaces import MultiAgentWorldBackend, StepResult
from core.worlds.soccer.config import SoccerWorldConfig
from core.worlds.soccer.rcss_protocol import (
    SeeInfo,
    SenseBodyInfo,
    action_to_commands,
    build_init_command,
)
from core.worlds.soccer.socket_interface import FakeSocket, SocketInterface
from core.worlds.soccer.types import (
    BallState,
    PlayerID,
    PlayerState,
    SoccerAction,
    SoccerObservation,
    Vector2D,
)

logger = logging.getLogger(__name__)


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

        # Receive and parse server messages
        self._receive_and_parse_messages()

        # In fake mode, we might need to trigger a response if the fake socket needs poking
        if isinstance(self._socket, FakeSocket):
            self._simulate_fake_step()

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
        """Receive and parse messages from rcssserver."""
        if not self._socket:
            return

        # Limit max messages per step to avoid infinite loop
        max_messages = 50

        for _ in range(max_messages):
            try:
                # Try to receive data (assuming non-blocking or timeout set)
                try:
                    data, _ = self._socket.recv(4096)
                except (TimeoutError, BlockingIOError):
                    break
                except Exception as e:
                    # Some socket implementations might raise other errors
                    logger.debug(f"Socket receive error: {e}")
                    break

                if not data:
                    break

                msg = data.strip()
                if not msg:
                    continue

                self._parse_server_message(msg)

            except Exception as e:
                logger.error(f"Unexpected error in receive loop: {e}")
                break

    def _parse_server_message(self, msg: str) -> None:
        """Parse a single server message and update state."""
        from core.worlds.soccer.rcss_protocol import (
            parse_hear_message,
            parse_see_message,
            parse_sense_body_message,
        )

        if msg.startswith("(see "):
            see_info = parse_see_message(msg)
            if see_info:
                # Assign to first player for now (single-agent assumption)
                if self._player_states:
                    pid = list(self._player_states.keys())[0]
                    self._update_state_from_see(pid, see_info)

        elif msg.startswith("(sense_body "):
            sense_info = parse_sense_body_message(msg)
            if sense_info:
                if self._player_states:
                    pid = list(self._player_states.keys())[0]
                    self._update_state_from_sense(pid, sense_info)

        elif msg.startswith("(hear "):
            hear_info = parse_hear_message(msg)
            if hear_info:
                if hear_info.sender == "referee":
                    self._play_mode = hear_info.message

    def _update_state_from_see(self, player_id: str, see_info: SeeInfo) -> None:
        """Update player and ball state from visual info."""
        from core.worlds.soccer.rcss_protocol import estimate_position_from_polar

        player = self._player_states[player_id]
        self._last_see_info[player_id] = see_info

        # Update ball if visible
        ball = see_info.get_ball()
        if ball and ball.distance is not None and ball.direction is not None:
            # Estimate ball absolute position
            ball_pos = estimate_position_from_polar(
                player.position, player.facing_angle, ball.distance, ball.direction
            )

            # Update shared ball state (BallState is frozen, so create new instance)
            if self._ball_state:
                self._ball_state = BallState(position=ball_pos, velocity=self._ball_state.velocity)
            else:
                self._ball_state = BallState(position=ball_pos, velocity=Vector2D(0, 0))

    def _update_state_from_sense(self, player_id: str, sense_info: SenseBodyInfo) -> None:
        """Update player state from body sensor info."""
        player = self._player_states[player_id]
        self._last_sense_info[player_id] = sense_info

        # Update stamina
        # PlayerState is NOT frozen in adapter dict, but it IS frozen in interfaces.py.
        # Wait, self._player_states stores PlayerState which IS frozen.
        # I need to check how self._player_states is populated.
        # In reset(), it creates PlayerState objects.

        # If PlayerState is frozen, I also need to replace the PlayerState object.

        new_stamina = sense_info.stamina

        if player.stamina != new_stamina:
            self._player_states[player_id] = PlayerState(
                player_id=player.player_id,
                team=player.team,
                position=player.position,
                velocity=player.velocity,
                stamina=new_stamina,
                facing_angle=player.facing_angle,
            )

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
