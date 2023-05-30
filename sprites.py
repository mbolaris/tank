import pygame
import os
import random
from pygame.math import Vector2
from constants import FILES, INIT_POS, SCREEN_HEIGHT, SCREEN_WIDTH

class Sprite(pygame.sprite.Sprite):
    """A base class for all sprites in the game."""
    image_cache = {}

    @staticmethod
    def load_image(filename):
        """Load an image from a file."""
        if filename in Sprite.image_cache:
            return Sprite.image_cache[filename]
        else:
            try:
                image = pygame.image.load(filename).convert_alpha()
                Sprite.image_cache[filename] = image
                return image
            except pygame.error as e:
                raise SystemExit(f"Couldn't load image: {filename}") from e

    def __init__(self, screen, filenames, x, y, speed):
        """Initialize a sprite."""
        super().__init__()
        self.screen = screen
        self.animation_frames = [self.load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.vel = Vector2(speed, 0)
        self.pos = Vector2(x, y)
        self.image = self.get_current_image()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.avoidance_velocity = Vector2(0, 0)

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
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.rect.topleft = self.pos

        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.vel.x *= -1

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
                self.avoidance_velocity -= velocity_change
            else:
                # Reset avoidance_velocity when the other sprite is far enough
                self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites, min_distance):
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)
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
        self.vel -= dist_vector.normalize() / 20.0

    def move_towards(self, difference):
        """Adjust velocity to move towards the average position of other sprites."""
        self.vel += difference.normalize() / 10.0

    def get_sprites_of_type(self, sprite_class):
        """Get all other sprites of the given class."""
        return [sprite for sprite in self.sprites if isinstance(sprite, sprite_class) and sprite != self]

class Fish(Sprite):
    def __init__(self, screen, sprites, movement_strategy, filenames, x, y, speed):
        self.size = 1
        self.animation_frames = [self.load_image(os.path.join('images', filename)) for filename in filenames]        
        self.base_width = self.animation_frames[0].get_width()
        self.base_height = self.animation_frames[0].get_height()     
        self.sprites = sprites
        self.movement_strategy = movement_strategy
        super().__init__(screen, filenames, x, y, speed)

    def grow(self):
        """Increase the size of the fish."""
        self.size += 0.1
        
    def update(self, elapsed_time):
        super().update(elapsed_time)
        self.movement_strategy.move(self)
        
    def get_current_image(self):
        """Get the current image of the sprite."""
        current_image = super().get_current_image()
        return pygame.transform.scale(current_image, (int(self.size * self.base_width), int(self.size * self.base_height)))       
        
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
        super().__init__(screen, FILES['food'], random.randint(0, SCREEN_WIDTH), 0, 2)
        self.vel = Vector2(0, 1)

    def update(self, elapsed_time):
        self.update_image_index(elapsed_time)        
        self.add_random_velocity_change()
        self.update_position()

    def add_random_velocity_change(self):
        random_x_direction = random.choices([-1, 0, 1], [0.05, 0.9, 0.05])[0]
        self.vel.x += random_x_direction / 5.0
