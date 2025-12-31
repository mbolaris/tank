"""2D physics engine for soccer training world.

Simple but realistic physics for ball movement, player movement, collisions,
and kicks. Deterministic and lightweight for fast training.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.policies.soccer_interfaces import PlayerID, TeamID, Vector2D


@dataclass
class Ball:
    """Ball entity with physics state."""

    position: Vector2D
    velocity: Vector2D
    radius: float = 0.085  # meters

    def update_position(self, friction: float) -> None:
        """Update ball position and apply friction."""
        # Apply velocity
        self.position = Vector2D(
            self.position.x + self.velocity.x,
            self.position.y + self.velocity.y,
        )

        # Apply friction (exponential decay)
        self.velocity = Vector2D(
            self.velocity.x * friction,
            self.velocity.y * friction,
        )

        # Stop ball if velocity is very small
        if abs(self.velocity.x) < 0.01 and abs(self.velocity.y) < 0.01:
            self.velocity = Vector2D(0.0, 0.0)


@dataclass
class Player:
    """Player entity with physics and game state."""

    player_id: PlayerID
    team: TeamID
    position: Vector2D
    velocity: Vector2D
    facing_angle: float  # radians
    stamina: float
    radius: float = 0.3  # meters
    max_stamina: float = 100.0

    def distance_to(self, other_pos: Vector2D) -> float:
        """Calculate distance to another position."""
        dx = self.position.x - other_pos.x
        dy = self.position.y - other_pos.y
        return math.sqrt(dx * dx + dy * dy)

    def can_kick_ball(self, ball: Ball, kick_range: float = 0.5) -> bool:
        """Check if player is close enough to kick the ball."""
        return self.distance_to(ball.position) <= kick_range


@dataclass
class FieldBounds:
    """Soccer field boundaries and goal positions."""

    width: float  # Total field width
    height: float  # Total field height
    goal_width: float = 7.32  # Standard goal width (meters)
    goal_depth: float = 2.0  # How far goal extends beyond field

    @property
    def x_min(self) -> float:
        return -self.width / 2

    @property
    def x_max(self) -> float:
        return self.width / 2

    @property
    def y_min(self) -> float:
        return -self.height / 2

    @property
    def y_max(self) -> float:
        return self.height / 2

    @property
    def goal_y_min(self) -> float:
        return -self.goal_width / 2

    @property
    def goal_y_max(self) -> float:
        return self.goal_width / 2

    def is_in_bounds(self, pos: Vector2D, include_goals: bool = True) -> bool:
        """Check if position is within field bounds."""
        if include_goals:
            # Allow goal areas
            x_in = self.x_min - self.goal_depth <= pos.x <= self.x_max + self.goal_depth
        else:
            x_in = self.x_min <= pos.x <= self.x_max

        y_in = self.y_min <= pos.y <= self.y_max
        return x_in and y_in

    def is_goal(self, ball_pos: Vector2D) -> Optional[TeamID]:
        """Check if ball is in a goal. Returns scoring team or None.

        Left team scores on right goal (x > x_max)
        Right team scores on left goal (x < x_min)
        """
        # Ball must be within goal width
        if not (self.goal_y_min <= ball_pos.y <= self.goal_y_max):
            return None

        # Check left goal (right team scores)
        if ball_pos.x < self.x_min:
            return "right"

        # Check right goal (left team scores)
        if ball_pos.x > self.x_max:
            return "left"

        return None

    def clamp_to_field(self, pos: Vector2D) -> Vector2D:
        """Clamp position to field bounds (bounce off walls)."""
        x = max(self.x_min, min(self.x_max, pos.x))
        y = max(self.y_min, min(self.y_max, pos.y))
        return Vector2D(x, y)

    def get_initial_ball_position(self) -> Vector2D:
        """Get center of field for kickoff."""
        return Vector2D(0.0, 0.0)

    def get_initial_player_positions(
        self, team: TeamID, team_size: int, rng: random.Random
    ) -> List[Vector2D]:
        """Get initial formation positions for a team.

        Simple formation: spread players in their half of the field.
        """
        positions = []
        half_x = self.x_max / 2 if team == "right" else -self.x_max / 2

        # Create a grid formation
        rows = min(4, (team_size + 2) // 3)  # 3-4 rows typically
        cols = (team_size + rows - 1) // rows

        for i in range(team_size):
            row = i // cols
            col = i % cols

            # Spread players across their half
            x_offset = (row / max(1, rows - 1) - 0.5) * (self.width / 4)
            y_offset = (col / max(1, cols - 1) - 0.5) * (self.height * 0.8)

            # Add small random jitter
            x_jitter = rng.uniform(-1.0, 1.0)
            y_jitter = rng.uniform(-1.0, 1.0)

            x = half_x + x_offset + x_jitter
            y = y_offset + y_jitter

            # Clamp to field
            x = max(self.x_min + 5, min(self.x_max - 5, x))
            y = max(self.y_min + 5, min(self.y_max - 5, y))

            positions.append(Vector2D(x, y))

        return positions


class SoccerPhysics:
    """Physics engine for soccer simulation."""

    def __init__(
        self,
        field_bounds: FieldBounds,
        ball_friction: float = 0.98,
        player_max_speed: float = 1.2,
        player_acceleration: float = 0.3,
        ball_kick_power_max: float = 3.0,
        rng: Optional[random.Random] = None,
    ):
        """Initialize physics engine.

        Args:
            field_bounds: Field dimensions and goal locations
            ball_friction: Velocity decay per frame (0-1)
            player_max_speed: Maximum player speed (m/s)
            player_acceleration: Player acceleration (m/s^2)
            ball_kick_power_max: Maximum kick power (m/s)
            rng: Random number generator for determinism
        """
        self.field = field_bounds
        self.ball_friction = ball_friction
        self.player_max_speed = player_max_speed
        self.player_acceleration = player_acceleration
        self.ball_kick_power_max = ball_kick_power_max
        self.rng = rng or random.Random()

    def update_player_movement(
        self,
        player: Player,
        target_pos: Optional[Vector2D],
        target_angle: Optional[float],
        dt: float = 1.0 / 60.0,
    ) -> None:
        """Update player position and facing based on action intent.

        Args:
            player: Player to update
            target_pos: Target position to move towards (None = no movement)
            target_angle: Target facing angle (None = no turn)
            dt: Time step in seconds
        """
        # Update facing angle if requested
        if target_angle is not None:
            # Smooth turn towards target (instant for now, can add turn rate later)
            player.facing_angle = target_angle

        # Update movement towards target
        if target_pos is not None:
            # Calculate direction to target
            dx = target_pos.x - player.position.x
            dy = target_pos.y - player.position.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 0.1:  # Only move if target is far enough
                # Normalize direction
                dir_x = dx / distance
                dir_y = dy / distance

                # Accelerate towards target
                desired_vx = dir_x * self.player_max_speed
                desired_vy = dir_y * self.player_max_speed

                # Apply acceleration (smooth movement)
                player.velocity = Vector2D(
                    player.velocity.x + (desired_vx - player.velocity.x) * self.player_acceleration,
                    player.velocity.y + (desired_vy - player.velocity.y) * self.player_acceleration,
                )

                # Clamp to max speed
                speed = math.sqrt(player.velocity.x**2 + player.velocity.y**2)
                if speed > self.player_max_speed:
                    scale = self.player_max_speed / speed
                    player.velocity = Vector2D(
                        player.velocity.x * scale,
                        player.velocity.y * scale,
                    )
        else:
            # No target, decelerate
            player.velocity = Vector2D(
                player.velocity.x * 0.9,
                player.velocity.y * 0.9,
            )

        # Update position
        new_x = player.position.x + player.velocity.x * dt
        new_y = player.position.y + player.velocity.y * dt
        new_pos = self.field.clamp_to_field(Vector2D(new_x, new_y))
        player.position = new_pos

    def kick_ball(
        self,
        player: Player,
        ball: Ball,
        kick_power: float,
        kick_angle: float,
    ) -> bool:
        """Attempt to kick the ball.

        Args:
            player: Player kicking
            ball: Ball to kick
            kick_power: Kick power [0, 1]
            kick_angle: Kick direction relative to player facing (radians)

        Returns:
            True if kick succeeded, False if player too far from ball
        """
        if not player.can_kick_ball(ball):
            return False

        # Calculate kick direction (player facing + kick angle)
        absolute_angle = player.facing_angle + kick_angle

        # Calculate ball velocity from kick
        kick_speed = kick_power * self.ball_kick_power_max
        ball_vx = kick_speed * math.cos(absolute_angle)
        ball_vy = kick_speed * math.sin(absolute_angle)

        # Set ball velocity (replaces current velocity)
        ball.velocity = Vector2D(ball_vx, ball_vy)

        return True

    def update_ball(self, ball: Ball) -> None:
        """Update ball position and handle boundary collisions."""
        # Apply physics
        ball.update_position(self.ball_friction)

        # Bounce off field boundaries (but not goals)
        if ball.position.x < self.field.x_min or ball.position.x > self.field.x_max:
            # Allow ball to enter goal area
            if not (self.field.goal_y_min <= ball.position.y <= self.field.goal_y_max):
                # Bounce off side walls
                ball.velocity = Vector2D(-ball.velocity.x * 0.8, ball.velocity.y)
                ball.position = self.field.clamp_to_field(ball.position)

        if ball.position.y < self.field.y_min or ball.position.y > self.field.y_max:
            # Bounce off top/bottom walls
            ball.velocity = Vector2D(ball.velocity.x, -ball.velocity.y * 0.8)
            ball.position = self.field.clamp_to_field(ball.position)

    def check_player_collisions(self, players: List[Player]) -> None:
        """Handle player-player collisions (simple separation)."""
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                dx = p2.position.x - p1.position.x
                dy = p2.position.y - p1.position.y
                dist = math.sqrt(dx * dx + dy * dy)

                min_dist = p1.radius + p2.radius
                if dist < min_dist and dist > 0:
                    # Separate players
                    overlap = min_dist - dist
                    nx = dx / dist
                    ny = dy / dist

                    # Move each player half the overlap distance
                    p1.position = Vector2D(
                        p1.position.x - nx * overlap / 2,
                        p1.position.y - ny * overlap / 2,
                    )
                    p2.position = Vector2D(
                        p2.position.x + nx * overlap / 2,
                        p2.position.y + ny * overlap / 2,
                    )

    def find_closest_player_to_ball(
        self, ball: Ball, players: List[Player]
    ) -> Optional[Tuple[Player, float]]:
        """Find the player closest to the ball.

        Returns:
            (player, distance) tuple or None if no players
        """
        if not players:
            return None

        closest = min(players, key=lambda p: p.distance_to(ball.position))
        distance = closest.distance_to(ball.position)
        return (closest, distance)
