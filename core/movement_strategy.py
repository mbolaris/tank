"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Tuple

from core.collision_system import default_collision_detector
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Fish as FishClass, Food
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish

# Movement smoothing constants (lower = smoother, higher = more responsive)
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.2  # Slightly more responsive for algorithms
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.2  # Allow 20% speed variation
ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ = ALGORITHMIC_MAX_SPEED_MULTIPLIER * ALGORITHMIC_MAX_SPEED_MULTIPLIER

VelocityComponents = Tuple[float, float]


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
        sprite_entity: "Fish" = sprite._entity if hasattr(sprite, "_entity") else sprite

        # Optimize: Use spatial query to only check nearby food
        # Radius of 50 is sufficient for collision detection (fish size + food size)
        nearby_food = sprite.environment.nearby_agents_by_type(sprite_entity, 50, Food)
        
        for food in nearby_food:
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity: Food = food._entity if hasattr(food, "_entity") else food

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by behavior algorithms with mix-and-match evolution.

    Fish now have TWO algorithms that can evolve independently:
    - behavior_algorithm: Primary movement algorithm (food seeking, exploration, etc.)
    - poker_algorithm: Poker-specific behavior algorithm (seeking/avoiding poker games)

    The algorithms are blended to create sophisticated composite behaviors.

    Performance optimizations:
    - Imports moved to module level
    - Pre-computed squared constant for speed comparison
    - Avoid sqrt when not needed
    """

    def move(self, sprite: "Fish") -> None:
        """Move using the fish's behavior algorithms (mix-and-match).

        Performance optimizations:
        - Cache frequently accessed attributes
        - Use squared distances to avoid sqrt
        - Batch calculations
        """
        genome = sprite.genome

        # Check if fish has a behavior algorithm
        if genome.behavior_algorithm is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute primary behavior algorithm
        primary_velocity: VelocityComponents = genome.behavior_algorithm.execute(sprite)
        primary_vx, primary_vy = primary_velocity

        # Execute poker algorithm if available (mix-and-match evolution)
        poker_algorithm = genome.poker_algorithm
        if poker_algorithm is not None:
            poker_velocity: VelocityComponents = poker_algorithm.execute(sprite)
            poker_vx, poker_vy = poker_velocity

            # Get the sprite entity (unwrap if it's a sprite wrapper)
            sprite_entity: "Fish" = sprite._entity if hasattr(sprite, "_entity") else sprite

            # Optimize: Use spatial query to only check nearby fish
            # We only care about fish within 200 units for poker behavior
            nearby_fish = sprite.environment.nearby_agents_by_type(sprite_entity, 200, FishClass)

            # Calculate poker behavior weight based on context
            poker_weight: float = 0.0

            # Performance: Only calculate weight if there are nearby fish
            fish_id = sprite.fish_id
            sprite_x = sprite.pos.x
            sprite_y = sprite.pos.y

            # Find nearest fish using squared distance (avoid sqrt)
            nearest_dist_sq: float = 40000.0  # 200^2 - anything beyond this is irrelevant

            for f in nearby_fish:
                if f.fish_id != fish_id:
                    dx = f.pos.x - sprite_x
                    dy = f.pos.y - sprite_y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < nearest_dist_sq:
                        nearest_dist_sq = dist_sq

            # Only compute weight if a nearby fish was found
            if nearest_dist_sq < 40000.0:
                distance = math.sqrt(nearest_dist_sq)
                # Poker is more relevant when fish are nearby (within 200 units)
                # Weight increases as fish get closer
                poker_weight = 1.0 - distance * 0.005  # Equivalent to distance / 200.0
                # Also consider energy - poker more relevant with higher energy
                max_energy = sprite.max_energy
                if max_energy > 0:
                    energy_ratio = sprite.energy / max_energy
                    poker_weight *= 0.3 + energy_ratio * 0.7  # Scale by energy (30-100%)

            # Blend primary and poker algorithms
            inv_weight = 1.0 - poker_weight
            desired_vx = primary_vx * inv_weight + poker_vx * poker_weight
            desired_vy = primary_vy * inv_weight + poker_vy * poker_weight
        else:
            # No poker algorithm, use primary only
            desired_vx, desired_vy = primary_vx, primary_vy

        # Apply algorithm decision - scale by speed to get actual velocity
        speed = sprite.speed
        target_vx = desired_vx * speed
        target_vy = desired_vy * speed

        # Smoothly interpolate toward desired velocity
        vel = sprite.vel
        dx = (target_vx - vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        dy = (target_vy - vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        vel.x += dx
        vel.y += dy

        # Normalize velocity to maintain consistent speed
        # Performance: Use squared comparison to avoid sqrt when not needed
        vel_length_sq = vel.length_squared()
        if vel_length_sq > 0:
            # Only normalize if speed exceeds max allowed
            max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ
            if vel_length_sq > max_speed_sq:
                # Normalize and scale in one step
                max_speed = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER
                scale = max_speed / math.sqrt(vel_length_sq)
                vel.mul_inplace(scale)

        super().move(sprite)
