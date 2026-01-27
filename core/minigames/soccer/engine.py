"""RCSS-Lite physics engine with cycle-based stepping.

This engine implements the rcssserver physics model for deterministic training.
The key difference from the legacy physics is:
1. Cycle-based timing (100ms semantics, not frame-based)
2. Command queue semantics (commands applied at end of cycle)
3. RCSS-like update order: u(t+1) = v(t) + a(t), p(t+1) = p(t) + u(t+1), v(t+1) = decay * u(t+1)

Reference: https://rcsoccersim.readthedocs.io/en/latest/soccerserver.html
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS, RCSSParams


class CommandType(Enum):
    """RCSS command types."""

    DASH = "dash"
    TURN = "turn"
    TURN_NECK = "turn_neck"
    KICK = "kick"
    MOVE = "move"  # Before kick-off only


@dataclass
class RCSSCommand:
    """A single RCSS command queued for execution."""

    cmd_type: CommandType
    power: float = 0.0  # For dash/kick
    direction: float = 0.0  # For dash (relative), kick (relative), turn (moment)

    @staticmethod
    def dash(power: float, direction: float = 0.0) -> RCSSCommand:
        """Create a dash command."""
        return RCSSCommand(CommandType.DASH, power=power, direction=direction)

    @staticmethod
    def turn(moment: float) -> RCSSCommand:
        """Create a turn command (moment in degrees)."""
        return RCSSCommand(CommandType.TURN, direction=moment)

    @staticmethod
    def turn_neck(moment: float) -> RCSSCommand:
        """Create a turn_neck command (moment in degrees)."""
        return RCSSCommand(CommandType.TURN_NECK, direction=moment)

    @staticmethod
    def kick(power: float, direction: float) -> RCSSCommand:
        """Create a kick command."""
        return RCSSCommand(CommandType.KICK, power=power, direction=direction)

    @staticmethod
    def move(x: float, y: float) -> RCSSCommand:
        """Create a move command (before kick-off only)."""
        return RCSSCommand(CommandType.MOVE, power=x, direction=y)


@dataclass
class RCSSVector:
    """2D vector for positions and velocities."""

    x: float = 0.0
    y: float = 0.0

    def magnitude(self) -> float:
        """Return vector magnitude."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> RCSSVector:
        """Return unit vector."""
        mag = self.magnitude()
        if mag < 1e-9:
            return RCSSVector(0.0, 0.0)
        return RCSSVector(self.x / mag, self.y / mag)

    def __add__(self, other: RCSSVector) -> RCSSVector:
        return RCSSVector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> RCSSVector:
        return RCSSVector(self.x * scalar, self.y * scalar)

    def clamp_magnitude(self, max_mag: float) -> RCSSVector:
        """Clamp to maximum magnitude."""
        mag = self.magnitude()
        if mag > max_mag:
            scale = max_mag / mag
            return RCSSVector(self.x * scale, self.y * scale)
        return self


@dataclass
class RCSSPlayerState:
    """State of a single player in RCSS-Lite engine."""

    player_id: str
    team: str  # "left" or "right"
    position: RCSSVector = field(default_factory=RCSSVector)
    velocity: RCSSVector = field(default_factory=RCSSVector)
    acceleration: RCSSVector = field(default_factory=RCSSVector)
    body_angle: float = 0.0  # radians
    neck_angle: float = 0.0  # radians (relative to body)
    stamina: float = 8000.0
    recovery: float = 1.0
    effort: float = 1.0

    def distance_to(self, other_pos: RCSSVector) -> float:
        """Calculate distance to another position."""
        dx = self.position.x - other_pos.x
        dy = self.position.y - other_pos.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class RCSSBallState:
    """State of the ball in RCSS-Lite engine."""

    position: RCSSVector = field(default_factory=RCSSVector)
    velocity: RCSSVector = field(default_factory=RCSSVector)
    acceleration: RCSSVector = field(default_factory=RCSSVector)


class RCSSLiteEngine:
    """RCSS-Lite physics engine with cycle-based stepping.

    This engine implements the rcssserver physics model:
    - Commands are queued and applied at the end of each cycle
    - Physics update follows: accel -> velocity -> position -> decay
    - Decay rates match server defaults

    Example:
        >>> engine = RCSSLiteEngine()
        >>> engine.add_player("left_1", "left", RCSSVector(-20, 0))
        >>> engine.queue_command("left_1", RCSSCommand.dash(100))
        >>> engine.step_cycle()
        >>> print(engine.get_player("left_1").position.x)
    """

    def __init__(
        self,
        params: RCSSParams | None = None,
        seed: int | None = None,
    ):
        """Initialize the RCSS-Lite engine.

        Args:
            params: Physics parameters (defaults to SOCCER_CANONICAL_PARAMS)
            seed: Random seed for determinism (None defaults to 0 for reproducibility)
        """
        self.params = params or SOCCER_CANONICAL_PARAMS
        # Treat None as 0 to prevent accidental nondeterminism
        self._rng = random.Random(seed if seed is not None else 0)

        # Game state
        self._players: dict[str, RCSSPlayerState] = {}
        self._ball = RCSSBallState()
        self._cycle = 0

        # Command queue (applied at end of cycle)
        self._command_queue: dict[str, RCSSCommand] = {}

        # Play mode
        self._play_mode = "before_kick_off"
        self._score = {"left": 0, "right": 0}

        # Goal attribution tracking
        self._last_touch_player_id: str | None = None
        self._last_touch_cycle: int = -1
        self._prev_touch_player_id: str | None = None
        self._prev_touch_cycle: int = -1

        # Side swapping state (for half-time)
        self._swapped_sides = False

    @property
    def cycle(self) -> int:
        """Current cycle number."""
        return self._cycle

    @property
    def score(self) -> dict[str, int]:
        """Current score."""
        return self._score.copy()

    def add_player(
        self,
        player_id: str,
        team: str,
        position: RCSSVector | None = None,
        body_angle: float = 0.0,
    ) -> None:
        """Add a player to the simulation."""
        pos = position or RCSSVector(0.0, 0.0)
        self._players[player_id] = RCSSPlayerState(
            player_id=player_id,
            team=team,
            position=pos,
            body_angle=body_angle,
            stamina=self.params.stamina_max,
            recovery=1.0,
            effort=1.0,
        )

    def get_player(self, player_id: str) -> RCSSPlayerState | None:
        """Get player state by ID."""
        return self._players.get(player_id)

    def get_ball(self) -> RCSSBallState:
        """Get ball state."""
        return self._ball

    def players(self) -> dict[str, RCSSPlayerState]:
        """Get read-only view of all players.

        Returns:
            Dict mapping player_id to RCSSPlayerState (read-only)
        """
        return self._players.copy()

    def iter_players(self):
        """Iterate over all player states.

        Yields:
            RCSSPlayerState objects for all players
        """
        return iter(self._players.values())

    def last_touch_info(self) -> dict[str, Any]:
        """Get information about last ball touch.

        Returns:
            Dict with keys:
                - player_id: ID of player who last touched ball (or None)
                - cycle: Cycle when last touch occurred (-1 if never)
                - prev_player_id: ID of player who touched ball before (or None)
                - prev_cycle: Cycle when previous touch occurred (-1 if never)
        """
        return {
            "player_id": self._last_touch_player_id,
            "cycle": self._last_touch_cycle,
            "prev_player_id": self._prev_touch_player_id,
            "prev_cycle": self._prev_touch_cycle,
        }

    def set_ball_position(self, x: float, y: float) -> None:
        """Set ball position (for kickoff/reset)."""
        self._ball.position = RCSSVector(x, y)
        self._ball.velocity = RCSSVector(0.0, 0.0)
        self._ball.acceleration = RCSSVector(0.0, 0.0)

    @property
    def play_mode(self) -> str:
        """Current play mode."""
        return self._play_mode

    def set_play_mode(self, mode: str) -> None:
        """Set play mode.

        Only a small set of modes are currently supported.
        """
        valid_modes = ("before_kick_off", "kick_off_left", "kick_off_right")
        if mode not in valid_modes:
            raise ValueError(f"Invalid play mode: {mode!r}. Expected one of {valid_modes}.")
        self._play_mode = mode

    def set_swapped_sides(self, swapped: bool) -> None:
        """Set whether teams have swapped sides (affects goal attribution)."""
        self._swapped_sides = swapped

    @property
    def swapped_sides(self) -> bool:
        """Whether sides are currently swapped (2nd half)."""
        return self._swapped_sides

    def queue_command(self, player_id: str, command: RCSSCommand) -> bool:
        """Queue a command for a player (applied at cycle end).

        Only one command per player per cycle is allowed.

        Args:
            player_id: Player to send command to
            command: Command to queue

        Returns:
            True if command was queued, False if player not found
        """
        if player_id not in self._players:
            return False

        # Only one command per cycle (last one wins)
        self._command_queue[player_id] = command
        return True

    def step_cycle(self) -> dict[str, Any]:
        """Execute one RCSS cycle with queued commands.

        Update order per rcssserver docs:
        1. Apply queued commands (generate accelerations)
        2. u(t+1) = v(t) + a(t)  -- update velocity with acceleration
        3. p(t+1) = p(t) + u(t+1)  -- update position with new velocity
        4. v(t+1) = decay * u(t+1)  -- apply decay to get final velocity
        5. a = 0  -- reset acceleration for next cycle

        Returns:
            Dict with cycle info and any events (goals, etc.)
        """
        events = []

        # 1. Process queued commands
        for player_id, command in self._command_queue.items():
            player = self._players.get(player_id)
            if player:
                self._apply_command(player, command)

        self._command_queue.clear()

        # 2-5. Update physics for all players
        for player in self._players.values():
            self._update_player_physics(player)

        # Update ball physics
        self._update_ball_physics()

        # Handle collisions
        self._handle_collisions()

        # Check for goals
        goal_info = self._check_goal()
        if goal_info:
            goal_team = goal_info["team"]
            events.append(
                {
                    "type": "goal",
                    "team": goal_team,
                    "cycle": self._cycle,
                    "scorer_id": goal_info.get("scorer_id"),
                    "assist_id": goal_info.get("assist_id"),
                }
            )
            self._score[goal_team] += 1
            self._reset_for_kickoff(goal_team)

        # Increment cycle
        self._cycle += 1

        return {
            "cycle": self._cycle,
            "events": events,
            "score": self._score.copy(),
        }

    def _apply_command(self, player: RCSSPlayerState, command: RCSSCommand) -> None:
        """Apply a command to generate acceleration/state changes."""
        if command.cmd_type == CommandType.DASH:
            self._apply_dash(player, command.power, command.direction)
        elif command.cmd_type == CommandType.TURN:
            self._apply_turn(player, command.direction)
        elif command.cmd_type == CommandType.TURN_NECK:
            self._apply_turn_neck(player, command.direction)
        elif command.cmd_type == CommandType.KICK:
            self._apply_kick(player, command.power, command.direction)
        elif command.cmd_type == CommandType.MOVE:
            self._apply_move(player, command.power, command.direction)

    def _apply_dash(self, player: RCSSPlayerState, power: float, direction: float) -> None:
        """Apply dash command.

        Dash generates acceleration based on:
        - power: [-100, 100]
        - direction: relative to body angle (degrees)
        - dash_power_rate: acceleration = power * rate

        Consumes stamina proportional to abs(power).
        """
        # Clamp power
        power = max(-100, min(100, power))

        # Check stamina
        # Dash consumes stamina proportional to power
        # Note: In RCSS, efficiency is also affected by effort, but consumption is raw power
        stamina_cost = abs(power) * self.params.dash_consume_rate

        # Check stamina vs cost
        if player.stamina < stamina_cost:
            # Not enough stamina for full dash
            if stamina_cost > 0:
                power = power * (player.stamina / stamina_cost)
            stamina_cost = player.stamina

        player.stamina -= stamina_cost

        # Apply effort to effective power
        effective_power = power * player.effort

        # Calculate acceleration direction
        dir_rad = player.body_angle + math.radians(direction)
        accel_mag = effective_power * self.params.dash_power_rate

        player.acceleration = RCSSVector(
            math.cos(dir_rad) * accel_mag,
            math.sin(dir_rad) * accel_mag,
        )

    def _apply_turn(self, player: RCSSPlayerState, moment: float) -> None:
        """Apply turn command.

        Turn rate is affected by player speed (inertia moment):
        actual_turn = moment / (1 + inertia_moment * speed)
        """
        # Clamp moment
        moment = max(self.params.min_moment, min(self.params.max_moment, moment))

        # Calculate actual turn based on inertia
        speed = player.velocity.magnitude()
        actual_turn = moment / (1.0 + self.params.inertia_moment * speed)

        # Apply turn
        player.body_angle += math.radians(actual_turn)

        # Normalize to [-pi, pi]
        while player.body_angle > math.pi:
            player.body_angle -= 2 * math.pi
        while player.body_angle < -math.pi:
            player.body_angle += 2 * math.pi

    def _apply_turn_neck(self, player: RCSSPlayerState, moment: float) -> None:
        """Apply turn_neck command.

        Neck angle is relative to body.
        Range is usually constrained (e.g. [-90, 90]), but RCSS-Lite can be loose for now.
        RCSS Standard: neck angle is limited to [min_neck_angle, max_neck_angle]
        """
        # Clamp moment
        moment = max(self.params.min_moment, min(self.params.max_moment, moment))

        # Apply turn (simple addition for now, no complex inertia for neck usually)
        player.neck_angle += math.radians(moment)

        # Clamp neck angle to RCSS limits
        max_neck_rad = math.radians(self.params.max_neck_angle)
        min_neck_rad = math.radians(self.params.min_neck_angle)
        player.neck_angle = max(min_neck_rad, min(max_neck_rad, player.neck_angle))

    def _apply_kick(self, player: RCSSPlayerState, power: float, direction: float) -> None:
        """Apply kick command.

        Kick accelerates ball if player is within kickable_margin.
        Ball speed = power * kick_power_rate
        Direction is relative to player body angle.
        """
        # Check if ball is kickable
        dist_to_ball = player.distance_to(self._ball.position)
        if dist_to_ball > self.params.kickable_margin + self.params.player_size:
            return  # Too far to kick

        # Clamp power
        power = max(0, min(100, power))

        # Calculate kick direction
        dir_rad = player.body_angle + math.radians(direction)

        # Add noise if enabled
        if self.params.noise_enabled:
            noise = self._rng.gauss(0, self.params.kick_rand)
            dir_rad += noise

        # Calculate ball acceleration from kick
        kick_accel = power * self.params.kick_power_rate

        # Add to ball acceleration (handle simultaneous kicks)
        accel_vec = RCSSVector(
            math.cos(dir_rad) * kick_accel,
            math.sin(dir_rad) * kick_accel,
        )
        self._ball.acceleration = self._ball.acceleration + accel_vec

        # Track touch for goal attribution
        # If different player than last touch, record assist candidate
        if self._last_touch_player_id and self._last_touch_player_id != player.player_id:
            self._prev_touch_player_id = self._last_touch_player_id
            self._prev_touch_cycle = self._last_touch_cycle
        self._last_touch_player_id = player.player_id
        self._last_touch_cycle = self._cycle

    def _apply_move(self, player: RCSSPlayerState, x: float, y: float) -> None:
        """Apply move command (before kick-off only)."""
        if self._play_mode not in ("before_kick_off", "kick_off_left", "kick_off_right"):
            return

        # Clamp to field bounds
        half_length = self.params.field_length / 2
        half_width = self.params.field_width / 2
        x = max(-half_length, min(half_length, x))
        y = max(-half_width, min(half_width, y))

        player.position = RCSSVector(x, y)
        player.velocity = RCSSVector(0.0, 0.0)
        player.acceleration = RCSSVector(0.0, 0.0)

    def _update_player_physics(self, player: RCSSPlayerState) -> None:
        """Update player physics for one cycle.

        RCSS update order:
        1. u(t+1) = v(t) + a(t)
        2. p(t+1) = p(t) + u(t+1)
        3. v(t+1) = decay * u(t+1)
        4. a = 0
        """
        # 1. Add acceleration to velocity
        new_velocity = player.velocity + player.acceleration

        # Apply noise if enabled (RCSS: velocity noise)
        if self.params.noise_enabled:
            # Noise is uniform in [-player_rand * |v|, player_rand * |v|]
            v_mag = new_velocity.magnitude()
            if v_mag > 0.001:
                noise_range = v_mag * self.params.player_rand
                noise_x = self._rng.uniform(-noise_range, noise_range)
                noise_y = self._rng.uniform(-noise_range, noise_range)
                new_velocity.x += noise_x
                new_velocity.y += noise_y

        # Clamp to max speed
        new_velocity = new_velocity.clamp_magnitude(self.params.player_speed_max)

        # 2. Update position
        player.position = player.position + new_velocity

        # Clamp to field bounds
        half_length = self.params.field_length / 2
        half_width = self.params.field_width / 2
        player.position.x = max(-half_length, min(half_length, player.position.x))
        player.position.y = max(-half_width, min(half_width, player.position.y))

        # 3. Apply decay
        player.velocity = new_velocity * self.params.player_decay

        # 4. Reset acceleration
        player.acceleration = RCSSVector(0.0, 0.0)

        # Recover stamina
        # RCSS Stamina Model:
        # 1. If stamina <= threshold, reduce effort and recovery
        # 2. Recover stamina based on recovery rate
        # 3. If stamina >= thresholds, recover effort

        # Constants
        stamina_max = self.params.stamina_max
        recover_dec_thr = stamina_max * 0.25  # 2000
        effort_dec_thr = stamina_max * 0.25  # 2000
        effort_inc_thr = stamina_max * 0.6  # 4800

        # 1. Decay recovery/effort if low stamina
        if player.stamina <= recover_dec_thr:
            player.recovery = max(
                self.params.recover_min, player.recovery - self.params.recover_dec
            )

        if player.stamina <= effort_dec_thr:
            player.effort = max(self.params.effort_min, player.effort - self.params.effort_dec)

        # 2. Recover stamina
        stamina_inc = self.params.stamina_inc_max * player.recovery
        player.stamina = min(stamina_max, player.stamina + stamina_inc)

        # 3. Recover effort if high stamina
        if player.stamina >= effort_inc_thr and player.effort < 1.0:
            player.effort = min(1.0, player.effort + self.params.effort_inc)

    def _update_ball_physics(self) -> None:
        """Update ball physics for one cycle."""
        # 1. Add acceleration to velocity
        new_velocity = self._ball.velocity + self._ball.acceleration

        # Clamp to max speed
        new_velocity = new_velocity.clamp_magnitude(self.params.ball_speed_max)

        # 2. Update position
        self._ball.position = self._ball.position + new_velocity

        # 3. Apply decay
        self._ball.velocity = new_velocity * self.params.ball_decay

        # 4. Reset acceleration
        self._ball.acceleration = RCSSVector(0.0, 0.0)

        # Bounce off field walls (not goals)
        self._ball_wall_bounce()

    def _ball_wall_bounce(self) -> None:
        """Handle ball bouncing off field walls."""
        half_length = self.params.field_length / 2
        half_width = self.params.field_width / 2
        half_goal = self.params.goal_width / 2

        # Check if in goal area (don't bounce)
        in_goal_area = abs(self._ball.position.y) < half_goal

        # Side walls (x)
        if not in_goal_area:
            if self._ball.position.x < -half_length:
                self._ball.position.x = -half_length
                self._ball.velocity.x *= -0.8
            elif self._ball.position.x > half_length:
                self._ball.position.x = half_length
                self._ball.velocity.x *= -0.8

        # Top/bottom walls (y)
        if self._ball.position.y < -half_width:
            self._ball.position.y = -half_width
            self._ball.velocity.y *= -0.8
        elif self._ball.position.y > half_width:
            self._ball.position.y = half_width
            self._ball.velocity.y *= -0.8

    def _handle_collisions(self) -> None:
        """Handle player-player and player-ball collisions."""
        players = list(self._players.values())

        # Player-player collisions
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                dx = p2.position.x - p1.position.x
                dy = p2.position.y - p1.position.y
                dist = math.sqrt(dx * dx + dy * dy)
                min_dist = self.params.player_size * 2

                if dist < min_dist and dist > 0:
                    # Separate players
                    overlap = min_dist - dist
                    nx, ny = dx / dist, dy / dist
                    p1.position.x -= nx * overlap / 2
                    p1.position.y -= ny * overlap / 2
                    p2.position.x += nx * overlap / 2
                    p2.position.y += ny * overlap / 2

                    # Apply velocity decay due to collision ( RCSS standard is ~0.1 )
                    p1.velocity = p1.velocity * 0.1
                    p2.velocity = p2.velocity * 0.1

        # Player-ball collisions
        for player in players:
            dx = self._ball.position.x - player.position.x
            dy = self._ball.position.y - player.position.y
            dist = math.sqrt(dx * dx + dy * dy)
            min_dist = self.params.player_size + self.params.ball_size

            if dist < min_dist and dist > 0:
                # Push ball away from player
                overlap = min_dist - dist
                nx, ny = dx / dist, dy / dist
                self._ball.position.x += nx * overlap
                self._ball.position.y += ny * overlap

    def _check_goal(self) -> dict[str, Any] | None:
        """Check if ball is in a goal. Returns goal info or None.

        Returns dict with:
            - team: scoring team ("left" or "right")
            - scorer_id: player who last touched ball (if known)
            - assist_id: player who touched before scorer on same team (if applicable)
        """
        half_length = self.params.field_length / 2
        half_goal = self.params.goal_width / 2

        # Check if ball y is within goal width
        if abs(self._ball.position.y) > half_goal:
            return None

        scoring_team: str | None = None

        # Left goal (right team scores)
        if self._ball.position.x < -half_length - self.params.ball_size:
            scoring_team = "right"

        # Right goal (left team scores)
        elif self._ball.position.x > half_length + self.params.ball_size:
            scoring_team = "left"

        if not scoring_team:
            return None

        # If sides are swapped, invert the scoring team
        # (Geometric "right" score means ball in Left Goal.
        # If swapped, Left Goal is defended by Right Team, so Left Team scored.)
        if self._swapped_sides:
            scoring_team = "left" if scoring_team == "right" else "right"

        # Attribute goal to last toucher
        scorer_id = self._last_touch_player_id
        assist_id: str | None = None

        # Assist: previous toucher on same team within assist window (50 cycles = 5 seconds)
        ASSIST_WINDOW = 50
        if (
            scorer_id
            and self._prev_touch_player_id
            and self._prev_touch_player_id != scorer_id
            and self._prev_touch_cycle >= 0
            and (self._last_touch_cycle - self._prev_touch_cycle) <= ASSIST_WINDOW
        ):
            # Check if prev toucher is on same team as scorer
            scorer_player = self._players.get(scorer_id)
            prev_player = self._players.get(self._prev_touch_player_id)
            if scorer_player and prev_player and scorer_player.team == prev_player.team:
                assist_id = self._prev_touch_player_id

        return {
            "team": scoring_team,
            "scorer_id": scorer_id,
            "assist_id": assist_id,
        }

    def _reset_for_kickoff(self, scoring_team: str) -> None:
        """Reset positions for kickoff after goal."""
        # Reset ball to center
        self.set_ball_position(0.0, 0.0)

        # Set play mode (other team kicks off)
        self._play_mode = f"kick_off_{'right' if scoring_team == 'left' else 'left'}"

        # Reset touch tracking for new play
        self._last_touch_player_id = None
        self._last_touch_cycle = -1
        self._prev_touch_player_id = None
        self._prev_touch_cycle = -1

    def reset(self, seed: int | None = None) -> None:
        """Reset the engine to initial state."""
        if seed is not None:
            self._rng = random.Random(seed)

        self._players.clear()
        self._ball = RCSSBallState()
        self._cycle = 0
        self._command_queue.clear()
        self._play_mode = "before_kick_off"
        self._score = {"left": 0, "right": 0}
        self._last_touch_player_id = None
        self._last_touch_cycle = -1
        self._prev_touch_player_id = None
        self._prev_touch_cycle = -1
        self._swapped_sides = False

    def get_snapshot(self) -> dict[str, Any]:
        """Get current state as a snapshot dict."""
        return {
            "cycle": self._cycle,
            "ball": {
                "x": self._ball.position.x,
                "y": self._ball.position.y,
                "vx": self._ball.velocity.x,
                "vy": self._ball.velocity.y,
            },
            "players": [
                {
                    "id": p.player_id,
                    "team": p.team,
                    "x": p.position.x,
                    "y": p.position.y,
                    "vx": p.velocity.x,
                    "vy": p.velocity.y,
                    "body_angle": p.body_angle,
                    "stamina": p.stamina,
                }
                for p in self._players.values()
            ],
            "score": self._score.copy(),
            "play_mode": self._play_mode,
        }
