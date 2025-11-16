"""Sprite adapters that wrap pure entities for pygame rendering.

This module provides pygame.sprite.Sprite wrappers around the pure entity classes,
separating rendering concerns from simulation logic.
"""

import pygame
from pygame.math import Vector2
from pygame.surface import Surface
import os
import math
from typing import TYPE_CHECKING, List

from image_loader import ImageLoader
from core.constants import FILES, IMAGE_CHANGE_RATE, PLANT_SWAY_RANGE, PLANT_SWAY_SPEED

if TYPE_CHECKING:
    from core.entities import Agent, Fish, Crab, Plant, Food, Castle


class AgentSprite(pygame.sprite.Sprite):
    """Pygame sprite adapter for Agent entities."""

    def __init__(self, entity: 'Agent', filenames: List[str]) -> None:
        """Initialize sprite for an agent.

        Args:
            entity: The pure entity object
            filenames: Image filenames for animation
        """
        super().__init__()
        self.entity: 'Agent' = entity

        # Load images
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in filenames
        ]
        self.image_index: int = 0

        # Initialize pygame-specific attributes
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (entity.pos.x, entity.pos.y)

        # Update entity size based on image
        entity.set_size(self.rect.width, self.rect.height)

    def get_current_image(self) -> Surface:
        """Get the current image based on entity velocity."""
        if self.entity.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update_image_index(self, elapsed_time: int) -> None:
        """Update the animation frame index."""
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // IMAGE_CHANGE_RATE) % len(self.animation_frames)

    def sync_from_entity(self, elapsed_time: int) -> None:
        """Sync sprite visuals from entity state.

        Args:
            elapsed_time: Time elapsed since start (for animation)
        """
        self.update_image_index(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.entity.pos.x, self.entity.pos.y)


class FishSprite(AgentSprite):
    """Pygame sprite adapter for Fish entities."""

    def __init__(self, entity: 'Fish', filenames: List[str]) -> None:
        """Initialize sprite for a fish.

        Args:
            entity: The pure fish entity
            filenames: Image filenames for animation
        """
        # Load images first to get base size
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in filenames
        ]
        self.base_width: int = self.animation_frames[0].get_width()
        self.base_height: int = self.animation_frames[0].get_height()

        # Update entity's base size
        entity.base_width = self.base_width
        entity.base_height = self.base_height

        # Initialize sprite
        pygame.sprite.Sprite.__init__(self)
        self.entity: 'Fish' = entity
        self.image_index: int = 0
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (entity.pos.x, entity.pos.y)

        # Update entity size
        entity.set_size(self.rect.width, self.rect.height)

    def get_current_image(self) -> Surface:
        """Get the current image with genetic color tint and size scaling."""
        # Get base image
        if self.entity.vel.x > 0:
            base_image = self.animation_frames[self.image_index]
        else:
            base_image = pygame.transform.flip(self.animation_frames[self.image_index], True, False)

        # Scale based on size and genetics
        scale_factor = self.entity.size * self.entity.genome.size_modifier
        new_width = int(self.base_width * scale_factor)
        new_height = int(self.base_height * scale_factor)
        scaled_image = pygame.transform.scale(base_image, (new_width, new_height))

        # Apply genetic color tint
        color_tint = self.entity.genome.get_color_tint()
        tinted_image = scaled_image.copy()
        tinted_image.fill(color_tint, special_flags=pygame.BLEND_RGB_MULT)

        return tinted_image

    def sync_from_entity(self, elapsed_time: int) -> None:
        """Sync sprite visuals from fish entity state."""
        self.update_image_index(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.entity.pos.x, self.entity.pos.y)

        # Update entity size based on current image
        self.entity.set_size(self.rect.width, self.rect.height)


class CrabSprite(AgentSprite):
    """Pygame sprite adapter for Crab entities."""

    def __init__(self, entity: 'Crab') -> None:
        """Initialize sprite for a crab.

        Args:
            entity: The pure crab entity
        """
        super().__init__(entity, FILES['crab'])


class PlantSprite(AgentSprite):
    """Pygame sprite adapter for Plant entities."""

    def __init__(self, entity: 'Plant') -> None:
        """Initialize sprite for a plant.

        Args:
            entity: The pure plant entity
        """
        super().__init__(entity, [FILES['plant'][entity.plant_type - 1]])

    def get_current_image(self) -> Surface:
        """Get the current image (no flipping for plants)."""
        return self.animation_frames[self.image_index]

    def sync_from_entity(self, elapsed_time: int) -> None:
        """Sync sprite visuals from plant entity state."""
        self.update_image_index(elapsed_time)

        # Apply swaying effect
        base_image = self.get_current_image()
        self.image = self._sway(base_image, elapsed_time, PLANT_SWAY_RANGE, PLANT_SWAY_SPEED)

        # Plants don't move
        self.rect.topleft = (self.entity.pos.x, self.entity.pos.y)

    def _sway(self, image: Surface, angle: float, sway_range: float, sway_speed: float) -> Surface:
        """Sways (rotates) an image back and forth around a fixed point at the bottom."""
        pivot = image.get_rect().midbottom
        sway_angle = math.sin(angle * sway_speed) * sway_range
        rotated_image = pygame.transform.rotate(image, sway_angle)
        rect = rotated_image.get_rect(midbottom=pivot)

        # Create a new surface to hold the rotated image at the correct position
        result = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
        result.blit(rotated_image, rect.topleft)

        return result


class CastleSprite(AgentSprite):
    """Pygame sprite adapter for Castle entities."""

    def __init__(self, entity: 'Castle') -> None:
        """Initialize sprite for a castle.

        Args:
            entity: The pure castle entity
        """
        super().__init__(entity, FILES['castle'])

    def get_current_image(self) -> Surface:
        """Get the current image (no flipping for castles)."""
        return self.animation_frames[self.image_index]


class FoodSprite(AgentSprite):
    """Pygame sprite adapter for Food entities."""

    def __init__(self, entity: 'Food') -> None:
        """Initialize sprite for food.

        Args:
            entity: The pure food entity
        """
        from core.constants import FOOD_TYPES
        food_files = FOOD_TYPES[entity.food_type]['files']
        super().__init__(entity, food_files)

    def get_current_image(self) -> Surface:
        """Get the current image (no flipping for food)."""
        return self.animation_frames[self.image_index]

    def sync_from_entity(self, elapsed_time: int) -> None:
        """Sync sprite visuals from food entity state."""
        self.update_image_index(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.entity.pos.x, self.entity.pos.y)
