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
from core.entities import Fish as FishClass
from core.entities import Food
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
    """Movement strategy controlled by behavior algorithms with mix-and-match evolution.

    Fish now have TWO algorithms that can evolve independently:
    - behavior_algorithm: Primary movement algorithm (food seeking, exploration, etc.)
    - poker_algorithm: Poker-specific behavior algorithm (seeking/avoiding poker games)

    The algorithms are blended to create sophisticated composite behaviors.

    Performance optimizations:
    - Imports moved to module level
    - Pre-computed squared constant for speed comparison
    - Avoid sqrt when not needed
    - Reduced poker query radius for better performance
    - Skip poker weight calculation when no nearby fish found
    - Inline velocity calculations to avoid function call overhead
    """

    # Reduced radius for poker weight calculation (was 200, now 100)
    # This significantly reduces the number of fish checked while still
    # providing accurate poker behavior weighting for nearby fish
    POKER_WEIGHT_RADIUS = 100
    POKER_WEIGHT_RADIUS_SQ = POKER_WEIGHT_RADIUS * POKER_WEIGHT_RADIUS
    # OPTIMIZATION: Only check for nearby fish every N frames to reduce query load
    POKER_CHECK_INTERVAL = 5

    def move(self, sprite: Fish) -> None:
        """Move using the fish's behavior algorithms (mix-and-match).

        Performance optimizations:
        - Cache frequently accessed attributes
        - Use squared distances to avoid sqrt
        - Skip nearby fish query if no poker algorithm
        - Use smaller radius for poker weight calculation
        - Early exit paths to minimize work
        - Only check for nearby fish every N frames
        """
        genome = sprite.genome

        # Check if fish has a behavior algorithm
        behavior_algorithm = genome.behavior_algorithm
        if behavior_algorithm is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute primary behavior algorithm
        primary_vx, primary_vy = behavior_algorithm.execute(sprite)

        # Execute poker algorithm if available (mix-and-match evolution)
        poker_algorithm = genome.poker_algorithm
        if poker_algorithm is not None:
            poker_vx, poker_vy = poker_algorithm.execute(sprite)

            # OPTIMIZATION: Only query for nearby fish every N frames
            # This reduces spatial query load by 80% while maintaining gameplay feel
            age = sprite.age if hasattr(sprite, 'age') else 0
            should_check_nearby = (age % self.POKER_CHECK_INTERVAL) == 0
            
            # Cache the poker weight on the sprite to reuse between checks
            if should_check_nearby:
                # Get the sprite entity (unwrap if it's a sprite wrapper)
                sprite_entity: Fish = sprite._entity if hasattr(sprite, "_entity") else sprite

                env = sprite.environment
                poker_radius = self.POKER_WEIGHT_RADIUS
                poker_radius_sq = self.POKER_WEIGHT_RADIUS_SQ
                
                # Cache sprite position
                sprite_x = sprite.pos.x
                sprite_y = sprite.pos.y
                fish_id = sprite.fish_id

                # Find nearest fish using squared distance (avoid sqrt)
                nearest_dist_sq = poker_radius_sq
                has_nearby_fish = False
                
                if hasattr(env, "nearby_fish"):
                    nearby_fish = env.nearby_fish(sprite_entity, poker_radius)
                    for f in nearby_fish:
                        if f.fish_id != fish_id:
                            dx = sprite_x - f.pos.x
                            dy = sprite_y - f.pos.y
                            dist_sq = dx * dx + dy * dy
                            if dist_sq < nearest_dist_sq:
                                nearest_dist_sq = dist_sq
                                has_nearby_fish = True

                # Only compute weight if a nearby fish was found
                if has_nearby_fish:
                    distance = math.sqrt(nearest_dist_sq)
                    poker_weight = 1.0 - distance / poker_radius
                    max_energy = sprite.max_energy
                    if max_energy > 0:
                        energy_ratio = sprite.energy / max_energy
                        poker_weight *= 0.3 + energy_ratio * 0.7
                    sprite._cached_poker_weight = poker_weight
                else:
                    sprite._cached_poker_weight = 0.0
            
            # Use cached poker weight
            poker_weight = getattr(sprite, '_cached_poker_weight', 0.0)
            if poker_weight > 0:
                # Blend primary and poker algorithms
                inv_weight = 1.0 - poker_weight
                desired_vx = primary_vx * inv_weight + poker_vx * poker_weight
                desired_vy = primary_vy * inv_weight + poker_vy * poker_weight
            else:
                # No nearby fish, use primary only
                desired_vx, desired_vy = primary_vx, primary_vy
        else:
            # No poker algorithm, use primary only
            desired_vx, desired_vy = primary_vx, primary_vy

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
