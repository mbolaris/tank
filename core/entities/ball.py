"""Ball entity for soccer gameplay."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from core.entities.base import Entity
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.world import World


class Ball(Entity):
    """Soccer ball with RCSS-Lite physics."""

    def __init__(self, environment: World, x: float, y: float):
        super().__init__(environment, x, y)
        self.id = id(self) % 1000000000  # Unique ID for frontend
        self.vel = Vector2(0.0, 0.0)
        self.decay = 0.94
        self.max_speed = 3.0
        self.max_speed = 3.0
        self.radius = 8.0  # Visual size (increased for visibility)
        self.set_size(self.radius * 2, self.radius * 2)
        self.last_kicker_id: Optional[int] = None

        # Visual property for backend-to-frontend
        self.color = "#FFFFFF"
        self.is_ball = True  # Tag for renderers

    def update(self, frame: int = 0, time_modifier: float = 1.0, time_of_day: float = 0.0) -> Any:
        """Update physics with buoyancy."""
        from core.entities.base import EntityUpdateResult

        # Decay velocity (0.94 per cycle)
        self.vel *= self.decay

        # Add buoyancy - ball floats upward and toward center-height
        # If ball is in lower 40% of tank, apply upward drift
        height = self.environment.height
        target_y = height * 0.4  # Target zone is upper 40%
        if self.pos.y > target_y:
            # Gentle upward drift (stronger when deeper)
            buoyancy = (self.pos.y - target_y) / height * 0.15
            self.vel.y -= buoyancy

        # Hard speed cap (3.0 per cycle)
        if self.vel.length_squared() > self.max_speed * self.max_speed:
            self.vel = self.vel.normalize() * self.max_speed

        # Update position
        self.pos += self.vel

        # Wall collisions
        self._handle_boundaries()

        return EntityUpdateResult()

    def _handle_boundaries(self) -> None:
        """Bounce off walls with energy loss."""
        width = self.environment.width
        height = self.environment.height
        margin = self.radius
        bounce_coeff = -0.8  # Lose 20% energy on bounce

        if self.pos.x < margin:
            self.pos.x = margin
            self.vel.x *= bounce_coeff
        elif self.pos.x > width - margin:
            self.pos.x = width - margin
            self.vel.x *= bounce_coeff

        if self.pos.y < margin:
            self.pos.y = margin
            self.vel.y *= bounce_coeff
        elif self.pos.y > height - margin:
            self.pos.y = height - margin
            self.vel.y *= bounce_coeff

    def kick(self, power: float, angle: float, kicker_id: int) -> None:
        """Apply kick force to the ball.

        Args:
            power: Kick power (0.0 to 100.0)
            angle: Kick direction in radians
            kicker_id: ID of the kicking agent
        """
        # Clamp power
        actual_power = max(0.0, min(power, 100.0))

        # RCSS kick rate is 0.027
        # acceleration = power * kick_rate
        accel_mag = actual_power * 0.027

        import math

        impulse = Vector2(math.cos(angle) * accel_mag, math.sin(angle) * accel_mag)
        self.vel += impulse
        self.last_kicker_id = kicker_id
