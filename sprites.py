import pygame
import os
import random
from pygame.math import Vector2
from constants import FILES, INIT_POS, SCREEN_HEIGHT, SCREEN_WIDTH

class Sprite(pygame.sprite.Sprite):
    """A base class for all sprites in the game."""
    @staticmethod
    def load_image(filename):
        """Load an image from a file."""
        try:
            return pygame.image.load(filename).convert_alpha()
        except pygame.error as e:
            raise SystemExit(f"Couldn't load image: {filename}") from e

    def __init__(self, screen, filenames, x, y, speed):
        """Initialize a sprite."""
        super().__init__()  # initialize the parent class
        self.screen = screen
        self.original_images = [self.load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.vel = Vector2(speed, 0)  # Using a vector for velocity
        self.pos = Vector2(x, y)  # Using a vector for position
        self.image = self.get_current_image()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def get_current_image(self):
        """Get the current image of the sprite."""
        if self.vel.x > 0:
            return self.original_images[self.image_index]
        else:
            return pygame.transform.flip(self.original_images[self.image_index], True, False)

    def display(self):
        """Display the sprite on the screen."""
        self.screen.blit(self.image, self.rect.topleft)

    def update_position(self):
        """Update the position of the sprite."""
        self.pos += self.vel  # Add velocity to position
        # Update rect's position
        self.rect.topleft = self.pos

        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.vel.x *= -1

        # Check if the sprite has moved out of the screen vertically
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def update_image_index(self, elapsed_time):
        """Update the image index of the sprite."""
        if len(self.original_images) > 1:
            self.image_index = (elapsed_time // 500) % len(self.original_images)

    def update(self, elapsed_time):
        """Update the sprite."""
        self.update_image_index(elapsed_time)
        self.update_position()
        self.image = self.get_current_image()

    def add_random_direction_change(self):
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        random_y_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction/10.0
        self.vel.y += random_y_direction/10.0

    def avoid(self, fish_list, min_distance):
        """Avoid other sprites."""
        for fish in fish_list:
            dist = Vector2(fish.rect.x, fish.rect.y) - self.pos
            if dist.length_squared() > 0:  # Check if the vector is not zero
                if dist.length() < min_distance:
                    self.pos -= dist.normalize()

    def align_with_and_avoid(self, fish_list, min_distance):
        avg_pos = Vector2(0, 0)
        for sprite in fish_list:
            avg_pos += Vector2(sprite.rect.x, sprite.rect.y)
        avg_pos /= len(fish_list)

        for fish in fish_list:
            dist = Vector2(fish.rect.x, fish.rect.y) - self.pos
            if dist.length_squared() > 0:  # Check if the vector is not zero
                if dist.length() < min_distance:
                    # If too close, adjust velocity to move away
                    self.vel -= dist.normalize()/20.0
                else:
                    difference = avg_pos - self.pos
                    if difference.length_squared() > 0:  # Check if the difference vector is not zero
                        # If not too close, adjust velocity to move closer to the average position
                        self.vel += difference.normalize()/10.0
        self.vel = self.vel.normalize() * self.speed  # Re-normalize velocity and multiply by speed


class Fish(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['fish'], *INIT_POS['fish'])
        self.sprites = sprites

    def update(self, elapsed_time):
        super().update(elapsed_time)
        self.add_random_direction_change()
        self.avoid([sprite for sprite in self.sprites if isinstance(sprite, Crab)], 100)

class SchoolingFish(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['school'], *INIT_POS['school'])
        self.sprites = sprites

        self.min_distance_to_other_schooling_fish = 50  # Minimum distance to maintain from other schooling fish
        self.min_distance_to_single_fish = 100  # Minimum distance to maintain from individual fish

        self.schooling_fish = [sprite for sprite in self.sprites if isinstance(sprite, SchoolingFish) and sprite != self]
        self.single_fish = [sprite for sprite in self.sprites if isinstance(sprite, Fish) and sprite != self and not isinstance(sprite, SchoolingFish)]
        self.crabs = [sprite for sprite in self.sprites if isinstance(sprite, Crab)]

    def update(self, elapsed_time):
        super().update(elapsed_time)

        # Align with and avoid other schooling fish
        if self.schooling_fish:
            self.align_with_and_avoid(self.schooling_fish, self.min_distance_to_other_schooling_fish)

        # Avoid single fish
        if self.single_fish:
            self.avoid(self.single_fish, self.min_distance_to_single_fish)

        # Avoid crabs
        if self.crabs:
            self.avoid(self.crabs, self.min_distance_to_single_fish)

        self.add_random_direction_change()

class Crab(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['crab'], *INIT_POS['crab'])
        self.sprites = sprites

class Plant(Sprite):
    def __init__(self, screen, plant_type):
        super().__init__(screen, [FILES['plant'][plant_type-1]], *INIT_POS[f'plant{plant_type}'])

class Castle(Sprite):
    def __init__(self, screen):
        super().__init__(screen, FILES['castle'], *INIT_POS['castle'])

class Food(Sprite):
    def __init__(self, screen):
        super().__init__(screen, FILES['food'], random.randint(0, SCREEN_WIDTH), 0, 2)  # Starts from a random position at the top of the screen
        self.vel = Vector2(0, 1)  # Initial velocity is downwards

    def update(self, elapsed_time):
        """Update the sprite."""
        self.add_random_direction_change()
        self.update_position()
        self.image = self.get_current_image()

    def add_random_direction_change(self):
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction/5.0
