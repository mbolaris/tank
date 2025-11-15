from pygame import Vector2
import pygame
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Fish

from agents import Crab, Food, Fish

# Constants
CRAB_AVOIDANCE_DISTANCE = 200
FOOD_ALIGNMENT_DISTANCE = 0
SCHOOLING_FISH_ALIGNMENT_DISTANCE = 25
SOLO_FISH_AVOIDANCE_DISTANCE = 100

class MovementStrategy:
    """Base class for movement strategies."""
    def move(self, sprite: 'Fish') -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: 'Fish') -> None:
        """Check if sprite collides with food and stop it if so."""
        for food in sprite.environment.get_agents_of_type(Food):
            if pygame.sprite.collide_rect(sprite, food):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


class NeuralMovement(MovementStrategy):
    """Movement strategy controlled by a neural network brain."""

    def move(self, sprite: 'Fish') -> None:
        """Move using neural network decision making."""
        # Check if fish has a brain
        if sprite.genome.brain is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change()
            super().move(sprite)
            return

        # Get inputs for the neural network
        from neural_brain import get_brain_inputs
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

class SoloFishMovement(MovementStrategy):
    """Movement strategy for a solo fish."""
    def move(self, sprite: 'Fish') -> None:
        """Move a solo fish."""
        sprite.add_random_velocity_change()
        sprite.avoid(sprite.environment.get_agents_of_type(Crab), CRAB_AVOIDANCE_DISTANCE)
        sprite.align_near(sprite.environment.get_agents_of_type(Food), FOOD_ALIGNMENT_DISTANCE)
        super().move(sprite)

class SchoolingFishMovement(MovementStrategy):
    """Movement strategy for schooling fish."""
    def move(self, sprite: 'Fish') -> None:
        """Move a schooling fish."""
        sprite.align_near(self.get_same_type_sprites(sprite), SCHOOLING_FISH_ALIGNMENT_DISTANCE)
        sprite.add_random_velocity_change()
        sprite.avoid(self.get_different_type_sprites(sprite), SOLO_FISH_AVOIDANCE_DISTANCE)
        sprite.avoid(sprite.environment.get_agents_of_type(Crab), CRAB_AVOIDANCE_DISTANCE)
        sprite.align_near(sprite.environment.get_agents_of_type(Food), FOOD_ALIGNMENT_DISTANCE)
        super().move(sprite)

    def get_same_type_sprites(self, sprite: 'Fish') -> List['Fish']:
        """Get sprites of the same type as the given sprite."""
        return [other_sprite for other_sprite in sprite.environment.get_agents_of_type(Fish)
                if other_sprite.animation_frames == sprite.animation_frames]

    def get_different_type_sprites(self, sprite: 'Fish') -> List['Fish']:
        """Get sprites of a different type from the given sprite."""
        return [other_sprite for other_sprite in sprite.environment.get_agents_of_type(Fish)
                if other_sprite.animation_frames != sprite.animation_frames]
