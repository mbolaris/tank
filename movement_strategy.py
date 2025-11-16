from pygame import Vector2
import pygame
from typing import List, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from agents import Fish

from agents import Crab, Food, Fish
from core.constants import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR

# Constants
CRAB_AVOIDANCE_DISTANCE = 200
FOOD_ALIGNMENT_DISTANCE = 0
SCHOOLING_FISH_ALIGNMENT_DISTANCE = 25
SOLO_FISH_AVOIDANCE_DISTANCE = 100


def rects_collide(rect1: Tuple[float, float, float, float],
                  rect2: Tuple[float, float, float, float]) -> bool:
    """Check if two rectangles collide.

    Args:
        rect1: (x, y, width, height) tuple for first rectangle
        rect2: (x, y, width, height) tuple for second rectangle

    Returns:
        True if rectangles overlap, False otherwise
    """
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    # Check if rectangles overlap
    return not (x1 + w1 < x2 or  # rect1 is left of rect2
                x2 + w2 < x1 or  # rect2 is left of rect1
                y1 + h1 < y2 or  # rect1 is above rect2
                y2 + h2 < y1)    # rect2 is above rect1


class MovementStrategy:
    """Base class for movement strategies."""
    def move(self, sprite: 'Fish') -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: 'Fish') -> None:
        """Check if sprite collides with food and stop it if so."""
        from core.entities import Food as FoodEntity

        # Get the entity's bounding box
        sprite_rect = sprite.get_rect()

        for food in sprite.environment.get_agents_of_type(Food):
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity = food._entity if hasattr(food, '_entity') else food
            food_rect = food_entity.get_rect()

            # Use entity-based collision detection
            if rects_collide(sprite_rect, food_rect):
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
        smoothing = 0.15  # Lower = smoother, higher = more responsive
        sprite.vel.x += (target_vx - sprite.vel.x) * smoothing
        sprite.vel.y += (target_vy - sprite.vel.y) * smoothing

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
        smoothing = 0.2  # Slightly more responsive than neural
        sprite.vel.x += (target_vx - sprite.vel.x) * smoothing
        sprite.vel.y += (target_vy - sprite.vel.y) * smoothing

        # Normalize velocity to maintain consistent speed
        vel_length = sprite.vel.length()
        if vel_length > 0:
            # Allow some variation in speed based on algorithm output
            max_speed_mult = 1.2
            target_speed = min(sprite.speed * max_speed_mult, vel_length)
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
