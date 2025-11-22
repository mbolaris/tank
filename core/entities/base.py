"""Base entity classes for the simulation."""

import random
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.constants import ALIGNMENT_SPEED_CHANGE, AVOIDANCE_SPEED_CHANGE, DEFAULT_AGENT_SIZE
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.environment import Environment
    from core.entities.predators import Crab


class LifeStage(Enum):
    """Life stages of a fish."""

    BABY = "baby"
    JUVENILE = "juvenile"
    ADULT = "adult"
    ELDER = "elder"


class Rect:
    """Simple rectangle class for collision detection and positioning."""

    def __init__(self, x: float = 0, y: float = 0, width: float = 32, height: float = 32):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def topleft(self):
        return (self.x, self.y)

    @topleft.setter
    def topleft(self, value):
        if isinstance(value, Vector2):
            self.x = value.x
            self.y = value.y
        else:
            self.x, self.y = value

    @property
    def center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)

    @center.setter
    def center(self, value):
        if isinstance(value, Vector2):
            self.x = value.x - self.width / 2
            self.y = value.y - self.height / 2
        else:
            self.x = value[0] - self.width / 2
            self.y = value[1] - self.height / 2

    def colliderect(self, other: "Rect") -> bool:
        """Check if this rect collides with another rect."""
        return (
            self.x < other.x + other.width
            and self.x + self.width > other.x
            and self.y < other.y + other.height
            and self.y + self.height > other.y
        )


class Agent:
    """Base class for all entities in the simulation (pure logic, no rendering)."""

    def __init__(
        self, environment: "Environment", *args, screen_width: int = 800, screen_height: int = 600
    ) -> None:
        """Initialize an agent.

        Args:
            environment: The environment the agent lives in
            *args: Either (x, y, speed) or (images, x, y, speed) for backward compatibility
            screen_width: Width of the simulation area
            screen_height: Height of the simulation area
        """
        # Handle backward compatibility with old API that included images parameter
        if len(args) == 5:
            # API with all positional: Agent(env, x, y, speed, screen_width, screen_height)
            x, y, speed, screen_width, screen_height = args
        elif len(args) == 4:
            # Old test API: Agent(env, images, x, y, speed)
            _, x, y, speed = args
        elif len(args) == 3:
            # Standard API: Agent(env, x, y, speed)
            x, y, speed = args
        else:
            raise ValueError(f"Expected 3, 4, or 5 positional args, got {len(args)}")

        self.speed: float = speed
        self.vel: Vector2 = Vector2(speed, 0)
        self.pos: Vector2 = Vector2(x, y)
        self.avoidance_velocity: Vector2 = Vector2(0, 0)
        self.environment: Environment = environment
        self.screen_width: int = screen_width
        self.screen_height: int = screen_height

        # Bounding box for collision detection (will be updated by size)
        self.width: float = DEFAULT_AGENT_SIZE  # Default size
        self.height: float = DEFAULT_AGENT_SIZE

        # Test compatibility attributes
        self.rect: Rect = Rect(x, y, self.width, self.height)
        self.image: Optional[object] = None  # Placeholder for test compatibility
        self._groups: List = []  # Track sprite groups for kill() method

    def get_rect(self) -> Tuple[float, float, float, float]:
        """Get bounding rectangle (x, y, width, height) for collision detection."""
        return (self.pos.x, self.pos.y, self.width, self.height)

    def set_size(self, width: float, height: float) -> None:
        """Set the size of the agent's bounding box."""
        self.width = width
        self.height = height
        # Keep rect in sync with size
        self.rect.width = width
        self.rect.height = height

    def update_position(self) -> None:
        """Update the position of the agent."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.handle_screen_edges()
        # Keep rect in sync with position
        self.rect.topleft = self.pos

    def handle_screen_edges(self) -> None:
        """Handle the agent hitting the edge of the screen."""
        # Horizontal boundaries - reverse velocity and clamp position
        if self.pos.x < 0:
            self.pos.x = 0
            self.vel.x = abs(self.vel.x)  # Bounce right
        elif self.pos.x + self.width > self.screen_width:
            self.pos.x = self.screen_width - self.width
            self.vel.x = -abs(self.vel.x)  # Bounce left

        # Vertical boundaries - reverse velocity and clamp position
        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + self.height > self.screen_height:
            self.pos.y = self.screen_height - self.height
            self.vel.y = -abs(self.vel.y)  # Bounce up

    def update(self, elapsed_time: int) -> None:
        """Update the agent state (pure logic, no rendering)."""
        self.update_position()

    def add_random_velocity_change(self, probabilities: List[float], divisor: float) -> None:
        """Add a random direction change to the agent."""
        random_x_direction = random.choices([-1, 0, 1], probabilities)[0]
        random_y_direction = random.choices([-1, 0, 1], probabilities)[0]
        self.vel.x += random_x_direction / divisor
        self.vel.y += random_y_direction / divisor

    def avoid(self, other_sprites: List["Agent"], min_distance: float) -> None:
        """Avoid other agents."""
        any_sprite_close = False

        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                any_sprite_close = True
                # Safety check: only normalize if vector has length
                if dist_length > 0:
                    velocity_change = dist_vector.normalize()
                    from core.entities.predators import Crab

                    if isinstance(other, Crab):
                        velocity_change.y = abs(velocity_change.y)
                    self.avoidance_velocity -= velocity_change * AVOIDANCE_SPEED_CHANGE

        # Only reset avoidance_velocity when no sprites are close
        if not any_sprite_close:
            self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites: List["Agent"], min_distance: float) -> None:
        """Align with nearby agents."""
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(
            other_sprites, avg_pos, min_distance
        )
        if self.vel.x != 0 or self.vel.y != 0:  # Checking if it's a zero vector
            self.vel = self.vel.normalize() * abs(self.speed)

    def get_average_position(self, other_sprites: List["Agent"]) -> Vector2:
        """Calculate the average position of other agents."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(
        self, other_sprites: List["Agent"], avg_pos: Vector2, min_distance: float
    ) -> None:
        """Adjust velocity based on the position of other agents."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()
            if 0 < dist_length < min_distance:
                self.move_away(dist_vector)
            else:
                difference = avg_pos - self.pos
                difference_length = difference.length()

                if difference_length > 0:
                    self.move_towards(difference)

    def move_away(self, dist_vector: Vector2) -> None:
        """Adjust velocity to move away from another agent."""
        dist_length = dist_vector.length()
        if dist_length > 0:
            self.vel -= dist_vector.normalize() * AVOIDANCE_SPEED_CHANGE

    def move_towards(self, difference: Vector2) -> None:
        """Adjust velocity to move towards the average position of other agents."""
        diff_length = difference.length()
        if diff_length > 0:
            self.vel += difference.normalize() * ALIGNMENT_SPEED_CHANGE

    def add_internal(self, group) -> None:
        """Track group for kill() method."""
        if group not in self._groups:
            self._groups.append(group)

    def kill(self) -> None:
        """Remove this agent from all groups."""
        for group in self._groups[:]:  # Copy list to avoid modification during iteration
            if hasattr(group, "remove"):
                group.remove(self)
        self._groups.clear()


class Castle(Agent):
    """A castle entity (decorative, pure logic)."""

    def __init__(
        self,
        environment: "Environment",
        x: float = 375,
        y: float = 475,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize a castle.

        Args:
            environment: The environment the castle lives in
            x: Initial x position
            y: Initial y position
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        super().__init__(environment, x, y, 0, screen_width, screen_height)
        # Make castle larger (3x default size)
        self.width = 150.0
        self.height = 150.0
