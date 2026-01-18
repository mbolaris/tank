"""Base entity classes for the simulation.

Entity Hierarchy
----------------
Entity (base)
    Core attributes: pos, state, rect, width, height, environment
    For: Static/decorative entities (Castle)

Agent(Entity)
    Adds: velocity, movement, AI behaviors (avoid, align, etc.)
    For: Moving entities with behavior (Fish, Plant, Food, Crab)

This hierarchy ensures decorative entities don't inherit unnecessary
movement methods.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from core.config.display import DEFAULT_AGENT_SIZE
from core.config.fish import ALIGNMENT_SPEED_CHANGE, AVOIDANCE_SPEED_CHANGE
from core.math_utils import Vector2

# Import LifeStage from state_machine for centralized definition with transition validation
from core.state_machine import LifeStage  # noqa: F401 - re-exported via core.entities.__init__
from core.state_machine import EntityState, create_entity_state_machine
from core.world import World


@dataclass
class EntityUpdateResult:
    """Result of an entity update cycle.

    Attributes:
        spawned_entities: List of new entities spawned by this entity
        events: List of events emitted by this entity (e.g. death, interaction)
    """

    spawned_entities: List["Entity"] = field(default_factory=list)
    events: List[Any] = field(default_factory=list)


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


class Entity:
    """Base class for all simulation entities (pure logic, no rendering).

    This is the minimal base class with just position, state, and bounding box.
    Use this for static/decorative entities that don't move or have AI.

    For moving entities with behavior, use Agent instead.
    """

    def __init__(self, environment: World, x: float, y: float) -> None:
        """Initialize an entity.

        Args:
            environment: The world the entity lives in
            x: Initial x position
            y: Initial y position
        """
        self.pos: Vector2 = Vector2(x, y)
        self.environment: World = environment

        # Bounding box for collision detection (will be updated by size)
        self.width: float = DEFAULT_AGENT_SIZE
        self.height: float = DEFAULT_AGENT_SIZE

        # Whether this entity should block fractal plant root spots beneath it
        self.blocks_root_spots: bool = False

        self.rect: Rect = Rect(x, y, self.width, self.height)
        self._groups: List = []  # Track sprite groups for kill() method

        # Lifecycle state machine (Active -> Dead/Removed)
        self.state = create_entity_state_machine(track_history=True)
        self.state.transition(EntityState.ACTIVE, reason="spawned")

    def get_rect(self) -> Tuple[float, float, float, float]:
        """Get bounding rectangle (x, y, width, height) for collision detection."""
        return (self.pos.x, self.pos.y, self.width, self.height)

    def set_size(self, width: float, height: float) -> None:
        """Set the size of the entity's bounding box."""
        self.width = width
        self.height = height
        # Keep rect in sync with size
        self.rect.width = width
        self.rect.height = height

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update the entity state (pure logic, no rendering).

        Returns:
            EntityUpdateResult containing any spawned entities or events.
        """
        return EntityUpdateResult()

    def add_internal(self, group) -> None:
        """Track group for kill() method."""
        if group not in self._groups:
            self._groups.append(group)

    def is_dead(self) -> bool:
        """Check if the entity is dead."""
        return self.state.state in (EntityState.DEAD, EntityState.REMOVED)

    def kill(self) -> None:
        """Remove this entity from all groups."""
        for group in self._groups[:]:  # Copy list to avoid modification during iteration
            if hasattr(group, "remove"):
                group.remove(self)
        self._groups.clear()

    def _emit_event(self, event: object) -> None:
        """Emit a telemetry event via EventBus or direct ecosystem recording.

        Prefers EventBus if available (enables decoupled telemetry subscribers).
        Falls back to direct ecosystem.record_event().
        Silently skips if neither is available.
        """
        # Try EventBus first (preferred path for decoupled telemetry)
        event_bus = getattr(self.environment, "event_bus", None)
        if event_bus is not None:
            event_bus.emit(event)
            return

        # Fallback to direct ecosystem recording
        telemetry = getattr(self, "ecosystem", None)
        if telemetry is None:
            return
        record_event = getattr(telemetry, "record_event", None)
        if callable(record_event):
            record_event(event)

    def constrain_to_screen(self) -> None:
        """Hard constraint to keep the entity fully within the bounds of the screen.

        This acts as a final safety clamp after movement and collision resolution.
        """
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        # Clamp horizontally
        if self.pos.x < min_x:
            self.pos.x = min_x
        elif self.pos.x + self.width > max_x:
            self.pos.x = max_x - self.width

        # Clamp vertically
        if self.pos.y < min_y:
            self.pos.y = min_y
        elif self.pos.y + self.height > max_y:
            self.pos.y = max_y - self.height

        # Keep rect in sync with position
        self.rect.topleft = self.pos


class Agent(Entity):
    """Moving entity with velocity and AI behaviors.

    Extends Entity with:
    - Velocity and movement (update_position, handle_screen_edges)
    - AI behaviors (avoid, align_near, move_away, move_towards)
    - Migration support

    Use this for Fish, Plant, Food, Crab, and other entities that move or
    have behavioral AI.
    """

    def __init__(self, environment: World, x: float, y: float, speed: float) -> None:
        """Initialize an agent.

        Args:
            environment: The world the agent lives in
            x: Initial x position
            y: Initial y position
            speed: Base movement speed
        """
        super().__init__(environment, x, y)

        # Movement attributes
        self.speed: float = speed
        self.vel: Vector2 = Vector2(speed, 0)
        self.avoidance_velocity: Vector2 = Vector2(0, 0)

        # Entity traits (overridden by subclasses)
        self.is_predator: bool = False

    def update_position(self) -> None:
        """Update the position of the agent."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.handle_screen_edges()
        # Keep rect in sync with position
        self.rect.topleft = self.pos

    def handle_screen_edges(self) -> None:
        """Handle the agent hitting the edge of the screen.

        Entities with migration support can attempt to leave the tank on horizontal
        boundaries. Other entities just bounce.
        """
        # Get boundaries from environment (World protocol)
        # 2D World returns ((min_x, min_y), (max_x, max_y))
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        # Check for custom boundary resolution (e.g. Petri circular dish)
        resolve_collision = getattr(self.environment, "resolve_boundary_collision", None)
        if resolve_collision is not None:
            if resolve_collision(self):
                return

        if self.can_attempt_migration():
            # Left boundary
            if self.pos.x < min_x:
                if self._attempt_migration("left"):
                    return  # Migration successful, entity removed from this tank
                self.pos.x = min_x
                self.vel.x = abs(self.vel.x)  # Bounce right
            # Right boundary
            elif self.pos.x + self.width > max_x:
                if self._attempt_migration("right"):
                    return  # Migration successful, entity removed from this tank
                self.pos.x = max_x - self.width
                self.vel.x = -abs(self.vel.x)  # Bounce left
        else:
            # Non-migrating entities just bounce
            if self.pos.x < min_x:
                self.pos.x = min_x
                self.vel.x = abs(self.vel.x)
            elif self.pos.x + self.width > max_x:
                self.pos.x = max_x - self.width
                self.vel.x = -abs(self.vel.x)

        # Vertical boundaries - always bounce (no migration)
        if self.pos.y < min_y:
            self.pos.y = min_y
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + self.height > max_y:
            self.pos.y = max_y - self.height
            self.vel.y = -abs(self.vel.y)  # Bounce up

    def can_attempt_migration(self) -> bool:
        """Return True if the entity should try migration when hitting boundaries."""

        return False

    def _attempt_migration(self, direction: str) -> bool:  # pragma: no cover - default no-op
        """Attempt migration in the given direction.

        Subclasses override this to integrate with migration handlers.
        """

        return False

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update the agent state (pure logic, no rendering).

        Returns:
            EntityUpdateResult containing any spawned entities or events.
        """
        self.update_position()
        return EntityUpdateResult()

    def add_random_velocity_change(self, probabilities: List[float], divisor: float) -> None:
        """Add a random direction change to the agent.

        Uses environment's RNG for deterministic behavior.
        """
        from core.util.rng import require_rng

        _rng = require_rng(self.environment, "Agent.add_random_velocity_change")
        random_x_direction = _rng.choices([-1, 0, 1], probabilities)[0]
        random_y_direction = _rng.choices([-1, 0, 1], probabilities)[0]
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

                    if other.is_predator:
                        velocity_change.y = abs(velocity_change.y)
                    self.avoidance_velocity -= velocity_change * AVOIDANCE_SPEED_CHANGE

        # Only reset avoidance_velocity when no sprites are close
        if not any_sprite_close:
            self.avoidance_velocity = Vector2(0, 0)
        else:
            # Cap avoidance velocity to prevent explosion
            # Limit to 50% of base speed
            max_avoidance = self.speed * 0.5
            if self.avoidance_velocity.length_squared() > max_avoidance * max_avoidance:
                self.avoidance_velocity = self.avoidance_velocity.normalize() * max_avoidance

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


class Castle(Entity):
    """A decorative castle entity that doesn't move.

    Inherits from Entity (not Agent) since it has no movement or AI behaviors.
    """

    def __init__(
        self,
        environment: World,
        x: float = 375,
        y: float = 475,
    ) -> None:
        """Initialize a castle.

        Args:
            environment: The world the castle lives in
            x: Initial x position
            y: Initial y position
        """
        super().__init__(environment, x, y)
        self.blocks_root_spots = True
        self.speed = 0  # Castle doesn't move
        # Make castle 50% larger than previous size (was 150x150 -> now 225x225)
        self.set_size(225.0, 225.0)

    def is_dead(self) -> bool:
        """Castle is never dead (decorative only)."""
        return False
