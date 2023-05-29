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
        self.animation_frames = [self.load_image(os.path.join('images', filename)) for filename in filenames]
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
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

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
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // 250) % len(self.animation_frames)

    def update(self, elapsed_time):
        """Update the sprite."""
        self.update_image_index(elapsed_time)
        self.update_position()
        self.image = self.get_current_image()

    def add_random_velocity_change(self):
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        random_y_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction/10.0
        self.vel.y += random_y_direction/10.0

    def avoid(self, other_sprites, min_distance):
        """Avoid other sprites."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                self.pos -= dist_vector.normalize()

    def align_near(self, other_sprites, min_distance):
        if not other_sprites:
            return

        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)

        self.vel = self.vel.normalize() * abs(self.speed)  # Re-normalize velocity and multiply by speed

    def get_average_position(self, other_sprites):
        """Calculate the average position of other sprites."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites, avg_pos, min_distance):
        """Adjust velocity based on the position of other sprites."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                # If too close, adjust velocity to move away
                self.move_away(dist_vector)
            else:
                difference = avg_pos - self.pos
                difference_length = difference.length()

                if difference_length > 0:  # Check if the difference vector is not zero
                    # If not too close, adjust velocity to move closer to the average position
                    self.move_towards(difference)

    def move_away(self, dist_vector):
        """Adjust velocity to move away from another sprite."""
        self.vel -= dist_vector.normalize() / 20.0

    def move_towards(self, difference):
        """Adjust velocity to move towards the average position of other sprites."""
        self.vel += difference.normalize() / 10.0

    def get_sprites_of_type(self, sprite_class):
        """Get all other sprites of the given class."""
        return [sprite for sprite in self.sprites if isinstance(sprite, sprite_class) and sprite != self]


class Fish(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['fish'], *INIT_POS['fish'])
        self.sprites = sprites

    def update(self, elapsed_time):
        super().update(elapsed_time)
        self.add_random_velocity_change()
        self.avoid(self.get_sprites_of_type(Crab), 100)
        self.align_near(self.get_sprites_of_type(Food), 0)

class SchoolingFish(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['school'], *INIT_POS['school'])
        self.sprites = sprites

        self.min_distance_to_other_schooling_fish = 40  # Minimum distance to maintain from other schooling fish
        self.min_distance_to_single_fish = 150  # Minimum distance to maintain from individual fish

    def update(self, elapsed_time):
        super().update(elapsed_time)

        # Align with and avoid other schooling fish
        self.align_near(self.get_sprites_of_type(SchoolingFish), self.min_distance_to_other_schooling_fish)

        # Avoid single fish
        self.avoid(self.get_sprites_of_type(Fish), self.min_distance_to_single_fish)

        # Avoid crabs
        self.avoid(self.get_sprites_of_type(Crab), self.min_distance_to_single_fish)

        self.add_random_velocity_change()
        self.align_near([sprite for sprite in self.sprites if isinstance(sprite, Food)], 0)
        
class Crab(Sprite):
    def __init__(self, screen, sprites):
        super().__init__(screen, FILES['crab'], *INIT_POS['crab'])
        self.sprites = sprites

    def update(self, elapsed_time):
        self.align_near([food for food in self.sprites if isinstance(food, Food)], 1)
        self.vel.y = 0        
        super().update(elapsed_time)

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
        self.add_random_velocity_change()
        self.update_position()
        self.image = self.get_current_image()

    def add_random_velocity_change(self):
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction/5.0
