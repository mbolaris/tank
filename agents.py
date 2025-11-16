"""Backward compatibility layer for agents.

This module provides pygame.sprite.Sprite classes that wrap the pure entity logic
from core.entities, maintaining backward compatibility while achieving separation
of concerns.

For new code, prefer importing from core.entities directly and using rendering.sprites
for visualization.
"""

import pygame
from pygame.math import Vector2
from pygame.surface import Surface
import os
import math
from typing import List, TYPE_CHECKING, Optional
from image_loader import ImageLoader
from core.constants import (FILES, INIT_POS, SCREEN_WIDTH, SCREEN_HEIGHT, IMAGE_CHANGE_RATE,
                       AVOIDANCE_SPEED_CHANGE, ALIGNMENT_SPEED_CHANGE, RANDOM_MOVE_PROBABILITIES,
                       RANDOM_VELOCITY_DIVISOR, FISH_GROWTH_RATE, PLANT_SWAY_RANGE,
                       PLANT_SWAY_SPEED, FOOD_SINK_ACCELERATION, FOOD_TYPES)
import random
from enum import Enum
from core.genetics import Genome
from core import entities as core_entities

if TYPE_CHECKING:
    from core.environment import Environment
    from movement_strategy import MovementStrategy
    from core.ecosystem import EcosystemManager


# Re-export LifeStage for backward compatibility
LifeStage = core_entities.LifeStage


class Agent(pygame.sprite.Sprite):
    """Backward compatible Agent class (pygame.sprite.Sprite + entity logic)."""

    def __init__(self, environment: 'Environment', filenames: List[str],
                 x: float, y: float, speed: float) -> None:
        """Initialize an agent sprite."""
        super().__init__()

        # Create the pure entity
        self._entity = core_entities.Agent(environment, x, y, speed, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Pygame-specific attributes
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in filenames
        ]
        self.image_index: int = 0
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # Update entity size
        self._entity.set_size(self.rect.width, self.rect.height)

    # Delegate all entity properties to the core entity
    @property
    def speed(self):
        return self._entity.speed

    @speed.setter
    def speed(self, value):
        self._entity.speed = value

    @property
    def vel(self):
        return self._entity.vel

    @vel.setter
    def vel(self, value):
        self._entity.vel = value

    @property
    def pos(self):
        return self._entity.pos

    @pos.setter
    def pos(self, value):
        self._entity.pos = value

    @property
    def avoidance_velocity(self):
        return self._entity.avoidance_velocity

    @avoidance_velocity.setter
    def avoidance_velocity(self, value):
        self._entity.avoidance_velocity = value

    @property
    def environment(self):
        return self._entity.environment

    @environment.setter
    def environment(self, value):
        self._entity.environment = value

    def update_position(self) -> None:
        """Update position (delegates to entity)."""
        self._entity.update_position()
        self.rect.topleft = (self.pos.x, self.pos.y)

    def handle_screen_edges(self) -> None:
        """Handle screen edges (delegates to entity)."""
        self._entity.handle_screen_edges()
        self.rect.topleft = (self.pos.x, self.pos.y)

    def get_current_image(self) -> Surface:
        """Get current sprite image."""
        if self.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update_image_index(self, elapsed_time: int) -> None:
        """Update animation frame."""
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // IMAGE_CHANGE_RATE) % len(self.animation_frames)

    def update(self, elapsed_time: int) -> None:
        """Update sprite."""
        self.update_image_index(elapsed_time)
        self._entity.update(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.pos.x, self.pos.y)

    def add_random_velocity_change(self) -> None:
        """Add random velocity change."""
        self._entity.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)

    def avoid(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Avoid other sprites."""
        # Convert sprite list to entity list
        other_entities = [s._entity if hasattr(s, '_entity') else s for s in other_sprites]
        self._entity.avoid(other_entities, min_distance)

    def align_near(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Align with nearby sprites."""
        other_entities = [s._entity if hasattr(s, '_entity') else s for s in other_sprites]
        self._entity.align_near(other_entities, min_distance)

    def get_average_position(self, other_sprites: List['Agent']) -> Vector2:
        """Get average position of other sprites."""
        other_entities = [s._entity if hasattr(s, '_entity') else s for s in other_sprites]
        return self._entity.get_average_position(other_entities)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites: List['Agent'],
                                                           avg_pos: Vector2, min_distance: float) -> None:
        """Adjust velocity based on other sprites."""
        other_entities = [s._entity if hasattr(s, '_entity') else s for s in other_sprites]
        self._entity.adjust_velocity_towards_or_away_from_other_sprites(other_entities, avg_pos, min_distance)

    def move_away(self, dist_vector: Vector2) -> None:
        """Move away from a position."""
        self._entity.move_away(dist_vector)

    def move_towards(self, difference: Vector2) -> None:
        """Move towards a position."""
        self._entity.move_towards(difference)


class Fish(Agent):
    """Backward compatible Fish class."""

    # Re-export class constants
    BABY_AGE = core_entities.Fish.BABY_AGE
    JUVENILE_AGE = core_entities.Fish.JUVENILE_AGE
    ADULT_AGE = core_entities.Fish.ADULT_AGE
    ELDER_AGE = core_entities.Fish.ELDER_AGE
    BASE_MAX_AGE = core_entities.Fish.BASE_MAX_AGE
    BASE_MAX_ENERGY = core_entities.Fish.BASE_MAX_ENERGY
    ENERGY_FROM_FOOD = core_entities.Fish.ENERGY_FROM_FOOD
    BASE_METABOLISM = core_entities.Fish.BASE_METABOLISM
    MOVEMENT_ENERGY_COST = core_entities.Fish.MOVEMENT_ENERGY_COST
    SHARP_TURN_DOT_THRESHOLD = core_entities.Fish.SHARP_TURN_DOT_THRESHOLD
    SHARP_TURN_ENERGY_COST = core_entities.Fish.SHARP_TURN_ENERGY_COST
    REPRODUCTION_ENERGY_THRESHOLD = core_entities.Fish.REPRODUCTION_ENERGY_THRESHOLD
    REPRODUCTION_COOLDOWN = core_entities.Fish.REPRODUCTION_COOLDOWN
    PREGNANCY_DURATION = core_entities.Fish.PREGNANCY_DURATION
    MATING_DISTANCE = core_entities.Fish.MATING_DISTANCE

    def __init__(self, environment: 'Environment', movement_strategy: 'MovementStrategy',
                 filenames: List[str], x: float, y: float, speed: float,
                 genome: Optional[Genome] = None, generation: int = 0,
                 fish_id: Optional[int] = None, ecosystem: Optional['EcosystemManager'] = None) -> None:
        """Initialize a fish sprite."""
        # Create the pure entity first
        species = filenames[0] if filenames else 'fish1.png'
        self._entity = core_entities.Fish(
            environment, movement_strategy, species, x, y, speed,
            genome, generation, fish_id, ecosystem, SCREEN_WIDTH, SCREEN_HEIGHT
        )

        # Initialize sprite
        pygame.sprite.Sprite.__init__(self)

        # Load animation frames
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in filenames
        ]
        self.base_width: int = self.animation_frames[0].get_width()
        self.base_height: int = self.animation_frames[0].get_height()
        self._entity.base_width = self.base_width
        self._entity.base_height = self.base_height

        self.image_index: int = 0
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # Update entity size
        self._entity.set_size(self.rect.width, self.rect.height)

    # Delegate fish-specific properties
    @property
    def genome(self):
        return self._entity.genome

    @property
    def generation(self):
        return self._entity.generation

    @property
    def species(self):
        return self._entity.species

    @property
    def age(self):
        return self._entity.age

    @property
    def max_age(self):
        return self._entity.max_age

    @property
    def life_stage(self):
        return self._entity.life_stage

    @property
    def max_energy(self):
        return self._entity.max_energy

    @property
    def energy(self):
        return self._entity.energy

    @energy.setter
    def energy(self, value):
        self._entity.energy = value

    @property
    def is_pregnant(self):
        return self._entity.is_pregnant

    @property
    def pregnancy_timer(self):
        return self._entity.pregnancy_timer

    @property
    def reproduction_cooldown(self):
        return self._entity.reproduction_cooldown

    @property
    def fish_id(self):
        return self._entity.fish_id

    @property
    def ecosystem(self):
        return self._entity.ecosystem

    @property
    def size(self):
        return self._entity.size

    @property
    def movement_strategy(self):
        return self._entity.movement_strategy

    def get_current_image(self) -> Surface:
        """Get current image with genetic color tint."""
        if self.vel.x > 0:
            base_image = self.animation_frames[self.image_index]
        else:
            base_image = pygame.transform.flip(self.animation_frames[self.image_index], True, False)

        scale_factor = self._entity.size * self.genome.size_modifier
        new_width = int(self.base_width * scale_factor)
        new_height = int(self.base_height * scale_factor)
        scaled_image = pygame.transform.scale(base_image, (new_width, new_height))

        color_tint = self.genome.get_color_tint()
        tinted_image = scaled_image.copy()
        tinted_image.fill(color_tint, special_flags=pygame.BLEND_RGB_MULT)

        return tinted_image

    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional['Fish']:
        """Update fish and return newborn if any."""
        self.update_image_index(elapsed_time)

        # Update entity and get potential newborn
        newborn_entity = self._entity.update(elapsed_time, time_modifier)

        # Update sprite
        self.image = self.get_current_image()
        self.rect.topleft = (self.pos.x, self.pos.y)
        self._entity.set_size(self.rect.width, self.rect.height)

        # Wrap newborn in sprite if exists
        if newborn_entity is not None:
            newborn_sprite = Fish(
                newborn_entity.environment,
                newborn_entity.movement_strategy,
                [newborn_entity.species],
                newborn_entity.pos.x,
                newborn_entity.pos.y,
                newborn_entity.speed / newborn_entity.genome.speed_modifier,
                newborn_entity.genome,
                newborn_entity.generation,
                newborn_entity.fish_id,
                newborn_entity.ecosystem
            )
            # Copy over the entity state
            newborn_sprite._entity = newborn_entity
            return newborn_sprite

        return None

    # Delegate methods
    def update_life_stage(self):
        return self._entity.update_life_stage()

    def consume_energy(self, time_modifier: float = 1.0):
        return self._entity.consume_energy(time_modifier)

    def is_starving(self) -> bool:
        return self._entity.is_starving()

    def is_dead(self) -> bool:
        return self._entity.is_dead()

    def get_death_cause(self) -> str:
        return self._entity.get_death_cause()

    def can_reproduce(self) -> bool:
        return self._entity.can_reproduce()

    def try_mate(self, other: 'Fish') -> bool:
        # Get the entity from the other fish sprite
        other_entity = other._entity if hasattr(other, '_entity') else other
        return self._entity.try_mate(other_entity)

    def eat(self, food: 'Food') -> None:
        food_entity = food._entity if hasattr(food, '_entity') else food
        return self._entity.eat(food_entity)

    def grow(self) -> None:
        """Deprecated - now handled by life stage."""
        pass


class Crab(Agent):
    """Backward compatible Crab class."""

    BASE_MAX_ENERGY = core_entities.Crab.BASE_MAX_ENERGY
    ENERGY_FROM_FISH = core_entities.Crab.ENERGY_FROM_FISH
    ENERGY_FROM_FOOD = core_entities.Crab.ENERGY_FROM_FOOD
    BASE_METABOLISM = core_entities.Crab.BASE_METABOLISM
    HUNT_COOLDOWN = core_entities.Crab.HUNT_COOLDOWN

    def __init__(self, environment: 'Environment', genome: Optional[Genome] = None) -> None:
        """Initialize a crab sprite."""
        self._entity = core_entities.Crab(environment, genome, *INIT_POS['crab'], SCREEN_WIDTH, SCREEN_HEIGHT)

        pygame.sprite.Sprite.__init__(self)
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in FILES['crab']
        ]
        self.image_index: int = 0
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (self._entity.pos.x, self._entity.pos.y)
        self._entity.set_size(self.rect.width, self.rect.height)

    @property
    def genome(self):
        return self._entity.genome

    @property
    def max_energy(self):
        return self._entity.max_energy

    @property
    def energy(self):
        return self._entity.energy

    @property
    def hunt_cooldown(self):
        return self._entity.hunt_cooldown

    def can_hunt(self) -> bool:
        return self._entity.can_hunt()

    def consume_energy(self) -> None:
        return self._entity.consume_energy()

    def eat_fish(self, fish: Fish) -> None:
        fish_entity = fish._entity if hasattr(fish, '_entity') else fish
        return self._entity.eat_fish(fish_entity)

    def eat_food(self, food: 'Food') -> None:
        food_entity = food._entity if hasattr(food, '_entity') else food
        return self._entity.eat_food(food_entity)

    def get_current_image(self) -> Surface:
        """Get current image."""
        if self.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update(self, elapsed_time: int) -> None:
        """Update crab."""
        self.update_image_index(elapsed_time)
        self._entity.update(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.pos.x, self.pos.y)


def sway(image: Surface, angle: float, sway_range: float, sway_speed: float) -> Surface:
    """Sways (rotates) an image back and forth around a fixed point at the bottom."""
    pivot = image.get_rect().midbottom
    sway_angle = math.sin(angle * sway_speed) * sway_range
    rotated_image = pygame.transform.rotate(image, sway_angle)
    rect = rotated_image.get_rect(midbottom=pivot)

    result = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
    result.blit(rotated_image, rect.topleft)

    return result


class Plant(Agent):
    """Backward compatible Plant class."""

    BASE_FOOD_PRODUCTION_RATE = core_entities.Plant.BASE_FOOD_PRODUCTION_RATE
    MAX_FOOD_CAPACITY = core_entities.Plant.MAX_FOOD_CAPACITY
    STATIONARY_FOOD_CHANCE = core_entities.Plant.STATIONARY_FOOD_CHANCE
    STATIONARY_FOOD_TYPE = core_entities.Plant.STATIONARY_FOOD_TYPE

    def __init__(self, environment: 'Environment', plant_type: int) -> None:
        """Initialize a plant sprite."""
        pos = INIT_POS[f'plant{plant_type}']
        self._entity = core_entities.Plant(environment, plant_type, *pos, SCREEN_WIDTH, SCREEN_HEIGHT)

        pygame.sprite.Sprite.__init__(self)
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', FILES['plant'][plant_type - 1]))
        ]
        self.image_index: int = 0
        self.sway_range: float = PLANT_SWAY_RANGE
        self.sway_speed: float = PLANT_SWAY_SPEED
        self.plant_type: int = plant_type

        self.image: Surface = self.animation_frames[self.image_index]
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (self._entity.pos.x, self._entity.pos.y)
        self._entity.set_size(self.rect.width, self.rect.height)

    @property
    def food_production_timer(self):
        return self._entity.food_production_timer

    @property
    def food_production_rate(self):
        return self._entity.food_production_rate

    @property
    def current_food_count(self):
        return self._entity.current_food_count

    def update_position(self) -> None:
        """Plants don't move."""
        pass

    def should_produce_food(self, time_modifier: float = 1.0) -> bool:
        return self._entity.should_produce_food(time_modifier)

    def notify_food_eaten(self) -> None:
        return self._entity.notify_food_eaten()

    def get_current_image(self) -> Surface:
        """Get current image (no flipping for plants)."""
        return self.animation_frames[self.image_index]

    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional['Food']:
        """Update plant and return food if produced."""
        self.update_image_index(elapsed_time)

        # Update entity
        food_entity = self._entity.update(elapsed_time, time_modifier)

        # Apply swaying
        base_image = self.get_current_image()
        self.image = sway(base_image, elapsed_time, self.sway_range, self.sway_speed)
        self.rect.topleft = (self.pos.x, self.pos.y)

        # Wrap food in sprite if exists
        if food_entity is not None:
            food_sprite = Food(
                food_entity.environment,
                food_entity.pos.x,
                food_entity.pos.y,
                source_plant=self,
                food_type=food_entity.food_type
            )
            # Copy over the entity state
            food_sprite._entity = food_entity
            return food_sprite

        return None


class Castle(Agent):
    """Backward compatible Castle class."""

    def __init__(self, environment: 'Environment') -> None:
        """Initialize a castle sprite."""
        self._entity = core_entities.Castle(environment, *INIT_POS['castle'], SCREEN_WIDTH, SCREEN_HEIGHT)

        pygame.sprite.Sprite.__init__(self)
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in FILES['castle']
        ]
        self.image_index: int = 0
        self.image: Surface = self.animation_frames[self.image_index]
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (self._entity.pos.x, self._entity.pos.y)
        self._entity.set_size(self.rect.width, self.rect.height)

    def get_current_image(self) -> Surface:
        """Get current image (no flipping)."""
        return self.animation_frames[self.image_index]


class Food(Agent):
    """Backward compatible Food class."""

    def __init__(self, environment: 'Environment', x: float, y: float,
                 source_plant: Optional[Plant] = None, food_type: Optional[str] = None,
                 allow_stationary_types: bool = True) -> None:
        """Initialize a food sprite."""
        self._entity = core_entities.Food(
            environment, x, y,
            source_plant._entity if source_plant and hasattr(source_plant, '_entity') else source_plant,
            food_type, allow_stationary_types, SCREEN_WIDTH, SCREEN_HEIGHT
        )

        pygame.sprite.Sprite.__init__(self)
        food_files = FOOD_TYPES[self._entity.food_type]['files']
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(os.path.join('images', filename))
            for filename in food_files
        ]
        self.image_index: int = 0
        self.source_plant: Optional[Plant] = source_plant
        self.food_type = self._entity.food_type
        self.food_properties = self._entity.food_properties
        self.is_stationary = self._entity.is_stationary

        self.image: Surface = self.animation_frames[self.image_index]
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self._entity.set_size(self.rect.width, self.rect.height)

    def get_energy_value(self) -> float:
        return self._entity.get_energy_value()

    def get_current_image(self) -> Surface:
        """Get current image (no flipping)."""
        return self.animation_frames[self.image_index]

    def update(self, elapsed_time: int) -> None:
        """Update food."""
        self.update_image_index(elapsed_time)
        self._entity.update(elapsed_time)
        self.image = self.get_current_image()
        self.rect.topleft = (self.pos.x, self.pos.y)

    def sink(self) -> None:
        """Sink based on food type."""
        self._entity.sink()

    def get_eaten(self) -> None:
        """Get eaten."""
        self._entity.get_eaten()
        self.kill()
