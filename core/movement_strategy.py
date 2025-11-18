"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from typing import TYPE_CHECKING

from core.math_utils import Vector2
from core.entities import Food
from core.collision_system import default_collision_detector
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR

if TYPE_CHECKING:
    from core.entities import Fish

# Movement smoothing constants (lower = smoother, higher = more responsive)
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.2  # Slightly more responsive for algorithms
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.2  # Allow 20% speed variation


class MovementStrategy:
    """Base class for movement strategies."""

    def move(self, sprite: "Fish") -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: "Fish") -> None:
        """Check if sprite collides with food and stop it if so.

        Args:
            sprite: The fish sprite to check for collisions
        """
        # Get the sprite entity (unwrap if it's a sprite wrapper)
        sprite_entity = sprite._entity if hasattr(sprite, "_entity") else sprite

        for food in sprite.environment.get_agents_of_type(Food):
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity = food._entity if hasattr(food, "_entity") else food

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by a behavior algorithm (NEW!)."""

    def move(self, sprite: "Fish") -> None:
        """Move using the fish's behavior algorithm."""
        # Check if fish has a behavior algorithm
        if sprite.genome.behavior_algorithm is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute the algorithm to get desired velocity
        desired_vx, desired_vy = sprite.genome.behavior_algorithm.execute(sprite)

        # Apply algorithm decision
        # Scale by speed to get actual velocity
        target_vx = desired_vx * sprite.speed
        target_vy = desired_vy * sprite.speed

        # Smoothly interpolate toward desired velocity
        sprite.vel.x += (target_vx - sprite.vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        sprite.vel.y += (target_vy - sprite.vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        # Normalize velocity to maintain consistent speed
        vel_length = sprite.vel.length()
        if vel_length > 0:
            # Allow some variation in speed based on algorithm output
            target_speed = min(sprite.speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER, vel_length)
            sprite.vel = sprite.vel.normalize() * target_speed

        super().move(sprite)
