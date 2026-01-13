"""Ball entity for soccer/sports gameplay in tank and Petri dish environments.

Physics Model:
    This implements RCSS-Lite style physics:
    1. Acceleration accumulates into velocity
    2. Velocity accumulates into position
    3. Velocity decays (friction/air resistance)
    4. Acceleration resets each cycle

This enables realistic ball mechanics while being deterministic and predictable.
"""

from typing import TYPE_CHECKING, Optional

from core.entities.base import Agent
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.world import World


class Ball(Agent):
    """Soccer ball entity with RCSS-Lite physics model.

    Attributes:
        position: (x, y) coordinates
        velocity: Current velocity vector
        acceleration: Current acceleration (reset each update)
        decay_rate: Velocity retention per cycle (0.94 = 94%)
        max_speed: Maximum velocity magnitude
        size: Ball radius for collision detection
        kickable_margin: Distance within which entities can kick the ball
        last_kicker: Last entity that kicked the ball (for goal attribution)
    """

    # Physics parameters (RCSS-compatible)
    DEFAULT_DECAY_RATE = 0.94  # 94% velocity retention per cycle
    DEFAULT_MAX_SPEED = 3.0  # Maximum velocity per cycle
    DEFAULT_SIZE = 0.085  # Ball radius in world units (meters)
    DEFAULT_KICKABLE_MARGIN = 0.7  # How close to kick the ball
    DEFAULT_KICK_POWER_RATE = 0.027  # Acceleration per power unit [0-100]

    # Ball size for rendering/collision (in pixels, roughly)
    DEFAULT_PIXEL_RADIUS = 5

    def __init__(
        self,
        environment: "World",
        x: float,
        y: float,
        decay_rate: float = DEFAULT_DECAY_RATE,
        max_speed: float = DEFAULT_MAX_SPEED,
        size: float = DEFAULT_SIZE,
        kickable_margin: float = DEFAULT_KICKABLE_MARGIN,
        kick_power_rate: float = DEFAULT_KICK_POWER_RATE,
    ) -> None:
        """Initialize the ball.

        Args:
            environment: The world the ball lives in
            x: Initial x position
            y: Initial y position
            decay_rate: Velocity retention per cycle (0.0-1.0)
            max_speed: Maximum velocity magnitude
            size: Ball radius in world units
            kickable_margin: Distance to kick the ball
            kick_power_rate: Acceleration per power unit
        """
        # Initialize as Agent with zero speed (ball doesn't have inherent speed)
        super().__init__(environment, x, y, speed=0.0)

        # Physics state
        self.acceleration = Vector2(0.0, 0.0)
        self.decay_rate = decay_rate
        self.max_speed = max_speed
        self.size = size
        self.kickable_margin = kickable_margin
        self.kick_power_rate = kick_power_rate

        # Collision and interaction tracking
        self.last_kicker: Optional[object] = None  # Last entity that kicked the ball
        self.last_kick_time: int = 0  # Frame number of last kick
        self.goal_event: Optional[dict] = None  # Current goal event if scored

        # Set visual size for rendering
        pixel_radius = self.DEFAULT_PIXEL_RADIUS
        self.set_size(pixel_radius * 2, pixel_radius * 2)

    def kick(self, power: float, direction: Vector2, kicker: Optional[object] = None) -> None:
        """Apply force to the ball from a kick.

        Args:
            power: Kick power [0-100]
            direction: Kick direction (unit vector)
            kicker: Entity performing the kick (tracked for goal attribution)
        """
        # Apply acceleration: power * kick_power_rate
        force = direction * power * self.kick_power_rate
        self.acceleration += force
        self.last_kicker = kicker

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ):
        """Update ball physics (RCSS-Lite: accel→vel→pos→decay).

        Args:
            frame_count: Current frame number
            time_modifier: Time scaling factor
            time_of_day: Current time of day (unused for ball)
        """
        from core.entities.base import EntityUpdateResult

        # 1. Acceleration → Velocity
        self.vel += self.acceleration

        # 2. Velocity → Position
        self.pos += self.vel

        # 3. Apply velocity decay (friction/air resistance)
        self.vel *= self.decay_rate

        # 4. Cap maximum speed
        speed = self.vel.length()
        if speed > self.max_speed:
            self.vel = self.vel.normalize() * self.max_speed

        # 5. Handle boundary collisions (bouncing)
        self._handle_boundary_collision()

        # 6. Reset acceleration
        self.acceleration = Vector2(0.0, 0.0)

        # Update rect for collision detection
        self.rect.topleft = self.pos

        return EntityUpdateResult()

    def _handle_boundary_collision(self) -> None:
        """Handle ball bouncing off walls.

        Uses elastic collision with coefficient of restitution (0.8).
        """
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        bounce_coefficient = 0.8  # 20% energy loss on bounce

        # Check for custom boundary resolution (e.g., Petri circular dish)
        resolve_collision = getattr(self.environment, "resolve_boundary_collision", None)
        if resolve_collision is not None:
            if resolve_collision(self):
                return

        # Horizontal boundaries
        if self.pos.x < min_x:
            self.pos.x = min_x
            self.vel.x = abs(self.vel.x) * bounce_coefficient
        elif self.pos.x + self.width > max_x:
            self.pos.x = max_x - self.width
            self.vel.x = -abs(self.vel.x) * bounce_coefficient

        # Vertical boundaries
        if self.pos.y < min_y:
            self.pos.y = min_y
            self.vel.y = abs(self.vel.y) * bounce_coefficient
        elif self.pos.y + self.height > max_y:
            self.pos.y = max_y - self.height
            self.vel.y = -abs(self.vel.y) * bounce_coefficient

    def is_kickable_by(self, entity: object, entity_pos: Vector2) -> bool:
        """Check if entity can kick the ball (within kickable distance).

        Args:
            entity: Entity attempting to kick
            entity_pos: Position of the entity

        Returns:
            True if entity is within kickable_margin of ball
        """
        distance = (self.pos - entity_pos).length()
        entity_size = getattr(entity, "width", 0) / 2  # Entity radius
        return distance <= entity_size + self.size + self.kickable_margin

    def reset_position(self, x: float, y: float) -> None:
        """Reset ball to a specific position with zero velocity.

        Useful for restart/kickoff scenarios.

        Args:
            x: New x position
            y: New y position
        """
        self.pos = Vector2(x, y)
        self.vel = Vector2(0.0, 0.0)
        self.acceleration = Vector2(0.0, 0.0)
        self.last_kicker = None
        self.last_kick_time = 0
        self.rect.topleft = self.pos

    def get_distance_to(self, target_pos: Vector2) -> float:
        """Get distance from ball to target position.

        Args:
            target_pos: Target position

        Returns:
            Euclidean distance
        """
        return (self.pos - target_pos).length()

    def get_direction_to(self, target_pos: Vector2) -> Vector2:
        """Get unit vector pointing from ball to target.

        Args:
            target_pos: Target position

        Returns:
            Normalized direction vector (or zero vector if same position)
        """
        direction = target_pos - self.pos
        length = direction.length()
        if length > 0:
            return direction / length
        return Vector2(0, 0)
