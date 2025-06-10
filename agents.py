import pygame
from pygame.math import Vector2
import os
from image_loader import ImageLoader
from constants import FILES, INIT_POS, SCREEN_WIDTH, SCREEN_HEIGHT, IMAGE_CHANGE_RATE, AVOIDANCE_SPEED_CHANGE, ALIGNMENT_SPEED_CHANGE
import random
import math


class Agent(pygame.sprite.Sprite):
    """A base class for all sprites in the game."""

    def __init__(self, environment, filenames, x, y, speed):
        """Initialize a sprite."""
        super().__init__()
        self.animation_frames = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.vel = Vector2(speed, 0)
        self.pos = Vector2(x, y)
        self.image = self.get_current_image()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.avoidance_velocity = Vector2(0, 0)
        self.environment = environment

    def update_position(self):
        """Update the position of the sprite."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.rect.topleft = self.pos
        self.handle_screen_edges()

    def handle_screen_edges(self):
        """Handle the sprite hitting the edge of the screen."""
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.vel.x *= -1
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def get_current_image(self):
        """Get the current image of the sprite."""
        if self.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update_image_index(self, elapsed_time):
        """Update the image index of the sprite."""
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // IMAGE_CHANGE_RATE) % len(self.animation_frames)

    def update(self, elapsed_time):
        """Update the sprite."""
        self.update_image_index(elapsed_time)
        self.update_position()
        self.image = self.get_current_image()

    def add_random_velocity_change(self):
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        random_y_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction / 10.0
        self.vel.y += random_y_direction / 10.0

    def avoid(self, other_sprites, min_distance):
        """Avoid other sprites."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                velocity_change = dist_vector.normalize() 
                if isinstance(other, Crab):
                    velocity_change.y = abs(velocity_change.y)
                self.avoidance_velocity -= velocity_change * AVOIDANCE_SPEED_CHANGE
            else:
                # Reset avoidance_velocity when the other sprite is far enough
                self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites, min_distance):
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)
        if self.vel.x != 0 or self.vel.y != 0:  # Checking if it's a zero vector
            self.vel = self.vel.normalize() * abs(self.speed)

    def get_average_position(self, other_sprites):
        """Calculate the average position of other sprites."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites, avg_pos, min_distance):
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

    def move_away(self, dist_vector):
        """Adjust velocity to move away from another sprite."""
        self.vel -= dist_vector.normalize() * AVOIDANCE_SPEED_CHANGE

    def move_towards(self, difference):
        """Adjust velocity to move towards the average position of other sprites."""
        self.vel += difference.normalize() * ALIGNMENT_SPEED_CHANGE

class Fish(Agent):
    """A fish sprite."""
    def __init__(self, environment, movement_strategy, filenames, x, y, speed):
        self.size = 1
        self.animation_frames = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.base_width = self.animation_frames[0].get_width()
        self.base_height = self.animation_frames[0].get_height()     
        self.movement_strategy = movement_strategy
        super().__init__(environment, filenames, x, y, speed)

    def grow(self):
        """Increase the size of the fish."""
        self.size += 0.1

    def update(self, elapsed_time):
        """Update the sprite."""
        super().update(elapsed_time)
        self.movement_strategy.move(self)

    def eat(self, food):
        """Eat food."""
        # For example, grow the fish when it eats food
        self.grow()

class Crab(Agent):
    def __init__(self, environment):
        super().__init__(environment, FILES['crab'], *INIT_POS['crab'], 2)

    def update(self, elapsed_time):
        food_sprites = self.environment.agents_to_align_with(self, 1, Food)
        if food_sprites:
            self.align_near(food_sprites, 1)
        self.vel.y = 0        
        super().update(elapsed_time)


def sway(image, angle, sway_range, sway_speed):
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
    def __init__(self, environment, plant_type):
        super().__init__(environment, [FILES['plant'][plant_type-1]], *INIT_POS[f'plant{plant_type}'], 0)
        self.sway_range = 5  
        self.sway_speed = 0.0005  

    def update_position(self):
        """Don't update the position of the plant."""
        pass

    def update(self, elapsed_time):
        """Update the sprite."""
        super().update(elapsed_time)

        # Sway the plant image back and forth
        self.image = sway(self.image, elapsed_time, self.sway_range, self.sway_speed)

class Castle(Agent):
    """A castle sprite."""
    def __init__(self, environment):
        super().__init__(environment, FILES['castle'], *INIT_POS['castle'], 0)

class Food(Agent):
    """A food sprite."""
    def __init__(self, environment, x, y):
        super().__init__(environment, FILES['food'], x, y, 0)

    def update(self, elapsed_time):
        """Update the sprite."""
        super().update(elapsed_time)
        self.sink()

    def sink(self):
        """Make the food sink."""
        self.vel.y += 0.01
        
    def get_eaten(self):
        """Get eaten."""
        # For example, remove the food from the game
        self.kill()        