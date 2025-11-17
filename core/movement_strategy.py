"""Movement strategies for fish agents.

This module provides different movement behaviors for fish:
- NeuralMovement: Neural network-based decision making
- AlgorithmicMovement: Parametrizable behavior algorithms
- SoloFishMovement: Simple rule-based solo behavior
- SchoolingFishMovement: Flocking behavior with schooling
"""

from typing import TYPE_CHECKING, List

from core.math_utils import Vector2

try:
    from agents import Crab, Fish, Food
except ImportError:
    from core.entities import Crab, Fish, Food
from core.collision_system import default_collision_detector
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR

if TYPE_CHECKING:
    from agents import Fish

# Movement distance constants
CRAB_AVOIDANCE_DISTANCE = 200
FOOD_ALIGNMENT_DISTANCE = 0  # Fish move to exact food position
SCHOOLING_FISH_ALIGNMENT_DISTANCE = 25
SOLO_FISH_AVOIDANCE_DISTANCE = 100

# Movement smoothing constants (lower = smoother, higher = more responsive)
NEURAL_MOVEMENT_SMOOTHING = 0.15  # Smooth movement for neural network control
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.2  # Slightly more responsive for algorithms
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.2  # Allow 20% speed variation


class MovementStrategy:
    """Base class for movement strategies."""
    def move(self, sprite: 'Fish') -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: 'Fish') -> None:
        """Check if sprite collides with food and stop it if so.

        Args:
            sprite: The fish sprite to check for collisions
        """
        # Get the sprite entity (unwrap if it's a sprite wrapper)
        sprite_entity = sprite._entity if hasattr(sprite, '_entity') else sprite

        for food in sprite.environment.get_agents_of_type(Food):
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity = food._entity if hasattr(food, '_entity') else food

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


class NeuralMovement(MovementStrategy):
    """Movement strategy controlled by a neural network brain."""

    def move(self, sprite: 'Fish') -> None:
        """Move using neural network decision making."""
        # Check if fish has a brain
        if sprite.genome.brain is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Get inputs for the neural network
        from core.neural_brain import get_brain_inputs
        inputs = get_brain_inputs(sprite)

        # Think and get desired velocity
        desired_vx, desired_vy = sprite.genome.brain.think(inputs)

        # Apply neural network decision
        # Scale by speed to get actual velocity
        target_vx = desired_vx * sprite.speed
        target_vy = desired_vy * sprite.speed

        # Smoothly interpolate toward desired velocity (not instant turns)
        sprite.vel.x += (target_vx - sprite.vel.x) * NEURAL_MOVEMENT_SMOOTHING
        sprite.vel.y += (target_vy - sprite.vel.y) * NEURAL_MOVEMENT_SMOOTHING

        # Normalize velocity to maintain consistent speed
        if sprite.vel.length() > 0:
            sprite.vel = sprite.vel.normalize() * sprite.speed

        super().move(sprite)


class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by a behavior algorithm (NEW!)."""

    def move(self, sprite: 'Fish') -> None:
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

class SoloFishMovement(MovementStrategy):
    """Movement strategy for a solo fish."""
    def move(self, sprite: 'Fish') -> None:
        """Move a solo fish."""
        sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
        sprite.avoid(sprite.environment.get_agents_of_type(Crab), CRAB_AVOIDANCE_DISTANCE)
        sprite.align_near(sprite.environment.get_agents_of_type(Food), FOOD_ALIGNMENT_DISTANCE)
        super().move(sprite)

class SchoolingFishMovement(MovementStrategy):
    """Movement strategy for schooling fish."""
    def move(self, sprite: 'Fish') -> None:
        """Move a schooling fish."""
        sprite.align_near(self.get_same_type_sprites(sprite), SCHOOLING_FISH_ALIGNMENT_DISTANCE)
        sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
        sprite.avoid(self.get_different_type_sprites(sprite), SOLO_FISH_AVOIDANCE_DISTANCE)
        sprite.avoid(sprite.environment.get_agents_of_type(Crab), CRAB_AVOIDANCE_DISTANCE)
        sprite.align_near(sprite.environment.get_agents_of_type(Food), FOOD_ALIGNMENT_DISTANCE)
        super().move(sprite)

    def get_same_type_sprites(self, sprite: 'Fish') -> List['Fish']:
        """Get sprites of the same type as the given sprite."""
        return [other_sprite for other_sprite in sprite.environment.get_agents_of_type(Fish)
                if hasattr(other_sprite, 'species') and hasattr(sprite, 'species')
                and other_sprite.species == sprite.species]

    def get_different_type_sprites(self, sprite: 'Fish') -> List['Fish']:
        """Get sprites of a different type from the given sprite."""
        return [other_sprite for other_sprite in sprite.environment.get_agents_of_type(Fish)
                if hasattr(other_sprite, 'species') and hasattr(sprite, 'species')
                and other_sprite.species != sprite.species]
