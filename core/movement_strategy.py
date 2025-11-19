"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from typing import TYPE_CHECKING

from core.collision_system import default_collision_detector
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Food
from core.math_utils import Vector2

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
    """Movement strategy controlled by behavior algorithms with mix-and-match evolution.

    Fish now have TWO algorithms that can evolve independently:
    - behavior_algorithm: Primary movement algorithm (food seeking, exploration, etc.)
    - poker_algorithm: Poker-specific behavior algorithm (seeking/avoiding poker games)

    The algorithms are blended to create sophisticated composite behaviors.
    """

    def move(self, sprite: "Fish") -> None:
        """Move using the fish's behavior algorithms (mix-and-match)."""
        # Check if fish has a behavior algorithm
        if sprite.genome.behavior_algorithm is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute primary behavior algorithm
        primary_vx, primary_vy = sprite.genome.behavior_algorithm.execute(sprite)

        # Execute poker algorithm if available (mix-and-match evolution)
        poker_vx, poker_vy = 0, 0
        if sprite.genome.poker_algorithm is not None:
            poker_vx, poker_vy = sprite.genome.poker_algorithm.execute(sprite)

        # Blend algorithms based on context
        # If fish has high energy and poker algorithm is seeking poker, blend behaviors
        # Otherwise, primarily use the main behavior algorithm
        if sprite.genome.poker_algorithm is not None:
            # Check if there are nearby fish for poker (determines poker relevance)
            from core.entities import Fish as FishClass
            all_fish = sprite.environment.get_agents_of_type(FishClass)
            other_fish = [f for f in all_fish if f.fish_id != sprite.fish_id]

            # Calculate poker behavior weight based on context
            poker_weight = 0.0
            if other_fish and len(other_fish) > 0:
                # Find nearest fish
                nearest_fish = min(other_fish, key=lambda f: (f.pos - sprite.pos).length())
                distance = (nearest_fish.pos - sprite.pos).length()

                # Poker is more relevant when fish are nearby (within 200 units)
                # Weight increases as fish get closer
                if distance < 200:
                    poker_weight = max(0.0, 1.0 - distance / 200.0)
                    # Also consider energy - poker more relevant with higher energy
                    energy_ratio = sprite.energy / sprite.max_energy if sprite.max_energy > 0 else 0
                    poker_weight *= (0.3 + energy_ratio * 0.7)  # Scale by energy (30-100%)

            # Blend primary and poker algorithms
            desired_vx = primary_vx * (1.0 - poker_weight) + poker_vx * poker_weight
            desired_vy = primary_vy * (1.0 - poker_weight) + poker_vy * poker_weight
        else:
            # No poker algorithm, use primary only
            desired_vx, desired_vy = primary_vx, primary_vy

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
