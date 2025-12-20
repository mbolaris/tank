"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Tuple

from core.collision_system import default_collision_detector
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Food
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish

# Movement smoothing constants (lower = smoother, higher = more responsive)
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.02  # Slightly more responsive for algorithms
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.0  # Cap at base speed (was 0.6)
ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ = ALGORITHMIC_MAX_SPEED_MULTIPLIER * ALGORITHMIC_MAX_SPEED_MULTIPLIER

VelocityComponents = Tuple[float, float]


class MovementStrategy:
    """Base class for movement strategies."""

    def move(self, sprite: Fish) -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: Fish) -> None:
        """Check if sprite collides with food and stop it if so.

        Args:
            sprite: The fish sprite to check for collisions
        """
        # Get the sprite entity (unwrap if it's a sprite wrapper)
        sprite_entity: Fish = sprite._entity if hasattr(sprite, "_entity") else sprite

        # Optimize: Use spatial query to only check nearby food
        # Radius of 50 is sufficient for collision detection (fish size + food size)
        # Use optimized nearby_food query if available
        if hasattr(sprite.environment, "nearby_food"):
            nearby_food = sprite.environment.nearby_food(sprite_entity, 50)
        else:
            nearby_food = sprite.environment.nearby_agents_by_type(sprite_entity, 50, Food)

        for food in nearby_food:
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity: Food = food._entity if hasattr(food, "_entity") else food

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by composable behaviors.

    Fish use a ComposableBehavior that combines multiple sub-behaviors:
    - ThreatResponse: How to react to predators
    - FoodApproach: How to approach and capture food
    - EnergyStyle: How to manage energy expenditure
    - SocialMode: How to interact with other fish
    - PokerEngagement: How to engage with poker opportunities

    This provides 1,152+ behavior combinations with tunable parameters,
    enabling much richer evolutionary exploration than the previous
    48 monolithic algorithms.

    Performance optimizations:
    - Pre-computed squared constant for speed comparison
    - Avoid sqrt when not needed
    - Inline velocity calculations
    """

    def move(self, sprite: Fish) -> None:
        """Move using the fish's composable behavior.

        The composable behavior handles all sub-behaviors internally:
        threat response, food seeking, social behavior, and poker engagement.
        """
        genome = sprite.genome

        # Check if fish has a composable behavior
        composable_behavior = (
            genome.behavioral.behavior.value
            if genome.behavioral.behavior
            else None
        )

        if composable_behavior is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute composable behavior - it handles all sub-behaviors internally
        desired_vx, desired_vy = composable_behavior.execute(sprite)

        # Apply algorithm decision - scale by speed to get actual velocity
        speed = sprite.speed
        target_vx = desired_vx * speed
        target_vy = desired_vy * speed

        # Smoothly interpolate toward desired velocity - inline for performance
        vel = sprite.vel
        vel.x += (target_vx - vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        vel.y += (target_vy - vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        # Normalize velocity to maintain consistent speed
        # Performance: Use squared comparison to avoid sqrt when not needed
        vel_x = vel.x
        vel_y = vel.y
        vel_length_sq = vel_x * vel_x + vel_y * vel_y

        # Anti-stuck mechanism: if velocity is very low, add small random nudge
        # This prevents fish from getting permanently stuck at (0,0)
        if vel_length_sq < 0.01:
            angle = random.random() * 6.283185307
            nudge_speed = speed * 0.3  # Small nudge to get unstuck
            vel.x = nudge_speed * math.cos(angle)
            vel.y = nudge_speed * math.sin(angle)
            vel_length_sq = vel.x * vel.x + vel.y * vel.y

        if vel_length_sq > 0:
            # Only normalize if speed exceeds max allowed
            max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ
            if vel_length_sq > max_speed_sq:
                # Normalize and scale in one step
                max_speed = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER
                scale = max_speed / math.sqrt(vel_length_sq)
                vel.x = vel_x * scale
                vel.y = vel_y * scale

        super().move(sprite)
