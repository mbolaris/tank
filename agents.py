import pygame
from pygame.math import Vector2
from pygame.surface import Surface
import os
from typing import List, TYPE_CHECKING
from image_loader import ImageLoader
from constants import (FILES, INIT_POS, SCREEN_WIDTH, SCREEN_HEIGHT, IMAGE_CHANGE_RATE,
                       AVOIDANCE_SPEED_CHANGE, ALIGNMENT_SPEED_CHANGE, RANDOM_MOVE_PROBABILITIES,
                       RANDOM_VELOCITY_DIVISOR, FISH_GROWTH_RATE, PLANT_SWAY_RANGE,
                       PLANT_SWAY_SPEED, FOOD_SINK_ACCELERATION)
import random
import math

if TYPE_CHECKING:
    import environment
    from movement_strategy import MovementStrategy


class Agent(pygame.sprite.Sprite):
    """A base class for all sprites in the game."""

    def __init__(self, environment: 'environment.Environment', filenames: List[str],
                 x: float, y: float, speed: float) -> None:
        """Initialize a sprite."""
        super().__init__()
        self.animation_frames: List[Surface] = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index: int = 0
        self.speed: float = speed
        self.vel: Vector2 = Vector2(speed, 0)
        self.pos: Vector2 = Vector2(x, y)
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.avoidance_velocity: Vector2 = Vector2(0, 0)
        self.environment: 'environment.Environment' = environment

    def update_position(self) -> None:
        """Update the position of the sprite."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.rect.topleft = self.pos
        self.handle_screen_edges()

    def handle_screen_edges(self) -> None:
        """Handle the sprite hitting the edge of the screen."""
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.vel.x *= -1
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def get_current_image(self) -> Surface:
        """Get the current image of the sprite."""
        if self.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update_image_index(self, elapsed_time: int) -> None:
        """Update the image index of the sprite."""
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // IMAGE_CHANGE_RATE) % len(self.animation_frames)

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        self.update_image_index(elapsed_time)
        self.update_position()
        self.image = self.get_current_image()

    def add_random_velocity_change(self) -> None:
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], RANDOM_MOVE_PROBABILITIES)[0]
        random_y_direction = random.choices([-1, 0, 1], RANDOM_MOVE_PROBABILITIES)[0]
        self.vel.x += random_x_direction / RANDOM_VELOCITY_DIVISOR
        self.vel.y += random_y_direction / RANDOM_VELOCITY_DIVISOR

    def avoid(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Avoid other sprites."""
        any_sprite_close = False

        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                any_sprite_close = True
                # Safety check: only normalize if vector has length
                if dist_length > 0:
                    velocity_change = dist_vector.normalize()
                    if isinstance(other, Crab):
                        velocity_change.y = abs(velocity_change.y)
                    self.avoidance_velocity -= velocity_change * AVOIDANCE_SPEED_CHANGE

        # Only reset avoidance_velocity when no sprites are close
        if not any_sprite_close:
            self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites: List['Agent'], min_distance: float) -> None:
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)
        if self.vel.x != 0 or self.vel.y != 0:  # Checking if it's a zero vector
            self.vel = self.vel.normalize() * abs(self.speed)

    def get_average_position(self, other_sprites: List['Agent']) -> Vector2:
        """Calculate the average position of other sprites."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites: List['Agent'],
                                                           avg_pos: Vector2, min_distance: float) -> None:
        """Adjust velocity based on the position of other sprites."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()
            if 0 < dist_length < min_distance:
                self.move_away(dist_vector)
            else:
                difference = avg_pos - self.pos
                difference_length = difference.length()

                if difference_length > 0:
                    self.move_towards(difference)

    def move_away(self, dist_vector: Vector2) -> None:
        """Adjust velocity to move away from another sprite."""
        dist_length = dist_vector.length()
        if dist_length > 0:
            self.vel -= dist_vector.normalize() * AVOIDANCE_SPEED_CHANGE

    def move_towards(self, difference: Vector2) -> None:
        """Adjust velocity to move towards the average position of other sprites."""
        diff_length = difference.length()
        if diff_length > 0:
            self.vel += difference.normalize() * ALIGNMENT_SPEED_CHANGE

class Fish(Agent):
    """A fish sprite."""
    def __init__(self, environment: 'environment.Environment', movement_strategy: 'MovementStrategy',
                 filenames: List[str], x: float, y: float, speed: float) -> None:
        self.size: float = 1
        self.animation_frames = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.base_width: int = self.animation_frames[0].get_width()
        self.base_height: int = self.animation_frames[0].get_height()
        self.movement_strategy: 'MovementStrategy' = movement_strategy
        super().__init__(environment, filenames, x, y, speed)

    def grow(self) -> None:
        """Increase the size of the fish."""
        self.size += FISH_GROWTH_RATE

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        super().update(elapsed_time)
        self.movement_strategy.move(self)

    def eat(self, food: 'Food') -> None:
        """Eat food."""
        # For example, grow the fish when it eats food
        self.grow()

class Crab(Agent):
    def __init__(self, environment: 'environment.Environment') -> None:
        super().__init__(environment, FILES['crab'], *INIT_POS['crab'], 2)

    def update(self, elapsed_time: int) -> None:
        food_sprites = self.environment.agents_to_align_with(self, 1, Food)
        if food_sprites:
            self.align_near(food_sprites, 1)
        self.vel.y = 0
        super().update(elapsed_time)


def sway(image: Surface, angle: float, sway_range: float, sway_speed: float) -> Surface:
    """Sways (rotates) an image back and forth around a fixed point at the bottom."""
    pivot = image.get_rect().midbottom
    sway_angle = math.sin(angle * sway_speed) * sway_range
    rotated_image = pygame.transform.rotate(image, sway_angle)
    rect = rotated_image.get_rect(midbottom=pivot)

    # Create a new surface to hold the rotated image at the correct position
    result = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
    result.blit(rotated_image, rect.topleft)

    return result

class Plant(Agent):
    """A plant sprite."""
    def __init__(self, environment: 'environment.Environment', plant_type: int) -> None:
        super().__init__(environment, [FILES['plant'][plant_type-1]], *INIT_POS[f'plant{plant_type}'], 0)
        self.sway_range: float = PLANT_SWAY_RANGE
        self.sway_speed: float = PLANT_SWAY_SPEED

    def update_position(self) -> None:
        """Don't update the position of the plant."""
        pass

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        super().update(elapsed_time)

        # Sway the plant image back and forth
        self.image = sway(self.image, elapsed_time, self.sway_range, self.sway_speed)

class Castle(Agent):
    """A castle sprite."""
    def __init__(self, environment: 'environment.Environment') -> None:
        super().__init__(environment, FILES['castle'], *INIT_POS['castle'], 0)

class Food(Agent):
    """A food sprite."""
    def __init__(self, environment: 'environment.Environment', x: float, y: float) -> None:
        super().__init__(environment, FILES['food'], x, y, 0)

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        super().update(elapsed_time)
        self.sink()

    def sink(self) -> None:
        """Make the food sink."""
        self.vel.y += FOOD_SINK_ACCELERATION

    def get_eaten(self) -> None:
        """Get eaten."""
        self.kill()


