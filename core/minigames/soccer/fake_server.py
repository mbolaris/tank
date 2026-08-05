"""FakeRCSSServer - In-process rcssserver harness.

This module provides an in-process server that mimics the rcssserver
command/observation interface. It uses the RCSSLiteEngine internally
and can emit basic "see" and "sense_body" messages.

This is useful for:
- Training policies with RCSS command semantics
- Testing without running the real server
- Deterministic replay and debugging
"""

from __future__ import annotations

import math
import re
from typing import Any

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import RCSSParams


class FakeRCSSServer:
    """In-process rcssserver-like harness for deterministic training.

    This server provides the same command/observation interface as rcssserver
    but runs entirely in-process with deterministic physics.

    Example:
        >>> server = FakeRCSSServer(seed=42)
        >>> server.add_player("player1", "left", (-20, 0))
        >>> server.queue_command("player1", "(dash 100)")
        >>> result = server.step()
        >>> print(server.get_sense_body_message("player1"))
    """

    def __init__(
        self,
        params: RCSSParams | None = None,
        seed: int | None = None,
        team_size: int = 11,
    ):
        """Initialize the fake server.

        Args:
            params: Physics parameters
            seed: Random seed for determinism
            team_size: Number of players per team
        """
        self._engine = RCSSLiteEngine(params=params, seed=seed)
        self._team_size = team_size
        self._player_teams: dict[str, str] = {}

    def add_player(
        self,
        player_id: str,
        team: str,
        position: tuple[float, float] = (0.0, 0.0),
        body_angle: float = 0.0,
    ) -> None:
        """Add a player to the server.

        Args:
            player_id: Unique player identifier
            team: "left" or "right"
            position: (x, y) position
            body_angle: Initial body angle in radians
        """
        self._engine.add_player(
            player_id=player_id,
            team=team,
            position=RCSSVector(position[0], position[1]),
            body_angle=body_angle,
        )
        self._player_teams[player_id] = team

    def setup_teams(self) -> None:
        """Set up default team formations."""
        half_length = self._engine.params.field_length / 2

        for i in range(self._team_size):
            # Left team
            left_id = f"left_{i + 1}"
            x = -half_length / 2 + (i % 4) * 5
            y = (i // 4 - 1) * 10
            body_angle = 0.0  # Face right
            self.add_player(left_id, "left", (x, y), body_angle)

            # Right team
            right_id = f"right_{i + 1}"
            x = half_length / 2 - (i % 4) * 5
            y = (i // 4 - 1) * 10
            body_angle = math.pi  # Face left
            self.add_player(right_id, "right", (x, y), body_angle)

    def queue_command(self, player_id: str, command_str: str) -> bool:
        """Queue a command string for a player.

        Parses RCSS command format:
        - (dash power [direction])
        - (turn moment)
        - (kick power direction)
        - (move x y)

        Args:
            player_id: Player to send command to
            command_str: Command string in RCSS format

        Returns:
            True if command was parsed and queued successfully
        """
        command = self._parse_command(command_str)
        if command is None:
            return False
        return self._engine.queue_command(player_id, command)

    def _parse_command(self, command_str: str) -> RCSSCommand | None:
        """Parse an RCSS command string."""
        command_str = command_str.strip()

        # Dash: (dash power [direction])
        dash_match = re.match(r"\(dash\s+([-\d.]+)(?:\s+([-\d.]+))?\)", command_str)
        if dash_match:
            power = float(dash_match.group(1))
            direction = float(dash_match.group(2)) if dash_match.group(2) else 0.0
            return RCSSCommand.dash(power, direction)

        # Turn: (turn moment)
        turn_match = re.match(r"\(turn\s+([-\d.]+)\)", command_str)
        if turn_match:
            moment = float(turn_match.group(1))
            return RCSSCommand.turn(moment)

        # Kick: (kick power direction)
        kick_match = re.match(r"\(kick\s+([-\d.]+)\s+([-\d.]+)\)", command_str)
        if kick_match:
            power = float(kick_match.group(1))
            direction = float(kick_match.group(2))
            return RCSSCommand.kick(power, direction)

        # Move: (move x y)
        move_match = re.match(r"\(move\s+([-\d.]+)\s+([-\d.]+)\)", command_str)
        if move_match:
            x = float(move_match.group(1))
            y = float(move_match.group(2))
            return RCSSCommand.move(x, y)

        return None

    def step(self) -> dict[str, Any]:
        """Execute one cycle and return results.

        Returns:
            Dict with cycle info, events, and observations per player
        """
        result = self._engine.step_cycle()

        # Build observations for all players
        observations = {}
        for player_id in self._player_teams:
            observations[player_id] = {
                "see": self.get_see_message(player_id),
                "sense_body": self.get_sense_body_message(player_id),
            }

        result["observations"] = observations
        return result

    def get_see_message(self, player_id: str) -> str:
        """Build see message in RCSS format for a player.

        Format: (see Time ObjInfo ObjInfo ...)
        ObjInfo: (ObjName Distance Direction [DistChange DirChange])
        """
        player = self._engine.get_player(player_id)
        if player is None:
            return ""

        cycle = self._engine.cycle
        objects = []

        # Ball
        ball = self._engine.get_ball()
        ball_info = self._build_object_info(player, ball.position, "b")
        if ball_info:
            objects.append(ball_info)

        # Other players
        for pid, other in self._engine.players().items():
            if pid == player_id:
                continue

            team_char = "l" if other.team == "left" else "r"
            # Extract uniform number from player_id (e.g., "left_1" -> 1)
            unum = pid.split("_")[-1]
            obj_name = f"p {team_char} {unum}"
            obj_info = self._build_object_info(player, other.position, obj_name)
            if obj_info:
                objects.append(obj_info)

        # Goals
        half_length = self._engine.params.field_length / 2
        left_goal_info = self._build_object_info(player, RCSSVector(-half_length, 0), "g l")
        right_goal_info = self._build_object_info(player, RCSSVector(half_length, 0), "g r")
        if left_goal_info:
            objects.append(left_goal_info)
        if right_goal_info:
            objects.append(right_goal_info)

        objects_str = " ".join(objects)
        return f"(see {cycle} {objects_str})"

    def _build_object_info(
        self,
        player: Any,
        obj_pos: RCSSVector,
        obj_name: str,
    ) -> str | None:
        """Build object info string for see message."""
        # Calculate relative position
        dx = obj_pos.x - player.position.x
        dy = obj_pos.y - player.position.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.01:
            return None  # Object at same position

        # Calculate direction relative to player's view
        absolute_angle = math.atan2(dy, dx)
        relative_angle = math.degrees(absolute_angle - player.body_angle)

        # Normalize to [-180, 180]
        while relative_angle > 180:
            relative_angle -= 360
        while relative_angle < -180:
            relative_angle += 360

        return f"(({obj_name}) {distance:.1f} {relative_angle:.1f})"

    def get_sense_body_message(self, player_id: str) -> str:
        """Build sense_body message in RCSS format for a player.

        Format: (sense_body Time (view_mode Quality Width) (stamina Stamina Effort)
                 (speed Amount Direction) (head_angle Angle) ...)
        """
        player = self._engine.get_player(player_id)
        if player is None:
            return ""

        cycle = self._engine.cycle
        stamina = player.stamina
        effort = 1.0  # Simplified

        speed = player.velocity.magnitude()
        speed_dir = math.degrees(math.atan2(player.velocity.y, player.velocity.x))

        # Normalize speed direction relative to body
        speed_dir_rel = speed_dir - math.degrees(player.body_angle)
        while speed_dir_rel > 180:
            speed_dir_rel -= 360
        while speed_dir_rel < -180:
            speed_dir_rel += 360

        return (
            f"(sense_body {cycle} "
            f"(view_mode high normal) "
            f"(stamina {stamina:.1f} {effort:.2f}) "
            f"(speed {speed:.2f} {speed_dir_rel:.1f}) "
            f"(head_angle 0) "
            f"(kick 0) (dash 0) (turn 0) (say 0) (turn_neck 0) "
            f"(catch 0) (move 0) (change_view 0))"
        )

    def get_monitor_message(self) -> str:
        """Build a monitor-protocol `(show ...)` frame for the current cycle.

        This is the **monitor** view of the match, not the player-facing
        `(see ...)` / `(sense_body ...)` messages the rest of this class emits:
        it is omniscient, unnoised, and consumed by
        `adapters.rcss_monitor_adapter`, which is what makes an RCSS-shaped
        match state testable without running a real server.

        Emitted in soccerserver's own convention - metres, `+y` south, body
        angles in **degrees clockwise** - so the adapter under test has real
        sign work to do rather than being handed canonical values.
        """
        score = self._engine.score
        parts = [
            f"(show {self._engine.cycle}",
            f"(pm {self._monitor_play_mode()})",
            f"(tm left right {score.get('left', 0)} {score.get('right', 0)})",
        ]

        ball = self._engine.get_ball()
        parts.append(
            f"((b) {ball.position.x:.4f} {-ball.position.y:.4f} "
            f"{ball.velocity.x:.4f} {-ball.velocity.y:.4f})"
        )

        # Sorted so a frame is byte-identical for identical engine state.
        for player_id in sorted(self._player_teams):
            player = self._engine.get_player(player_id)
            if player is None:
                continue
            side = "l" if self._player_teams[player_id] == "left" else "r"
            number = self._monitor_uniform_number(player_id)
            body_degrees = -math.degrees(player.body_angle)
            stamina = getattr(player, "stamina", 0.0)
            parts.append(
                f"(({side} {number}) 0 0x1 "
                f"{player.position.x:.4f} {-player.position.y:.4f} "
                f"{player.velocity.x:.4f} {-player.velocity.y:.4f} "
                f"{body_degrees:.4f} 0 "
                f"(v h 90) (s {stamina:.1f} 1 1 130600) "
                f"(c 0 0 0 0 0 0 0 0 0 0 0))"
            )

        return " ".join(parts) + ")"

    def _monitor_play_mode(self) -> str:
        """The monitor's numeric play-mode slot.

        Kept numeric and unmapped on purpose: turning it into an RCSS mode name
        needs the rcssserver PlayMode enum ordering, which nothing in this
        repository can verify. The adapter carries it through as an honest
        unknown instead (SOCCER_ARENA_DESIGN.md §10.4 rule 5).
        """
        return "0"

    @staticmethod
    def _monitor_uniform_number(player_id: str) -> int:
        """Uniform number from a `<side>_<n>` id, defaulting to 0.

        Uniform numbers are unique only within a side, so the monitor identity
        is the `(side, uniform_number)` composite - never the number alone
        (§10.2).
        """
        try:
            return int(player_id.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            return 0

    def get_hear_message(self, player_id: str, sender: str, message: str) -> str:
        """Build hear message in RCSS format."""
        cycle = self._engine.cycle
        return f'(hear {cycle} {sender} "{message}")'

    def reset(self, seed: int | None = None) -> None:
        """Reset the server to initial state."""
        self._engine.reset(seed)
        self._player_teams.clear()

    @property
    def cycle(self) -> int:
        """Current cycle number."""
        return self._engine.cycle

    @property
    def score(self) -> dict[str, int]:
        """Current score."""
        return self._engine.score

    def get_snapshot(self) -> dict[str, Any]:
        """Get current state snapshot."""
        return self._engine.get_snapshot()
