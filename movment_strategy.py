from pygame import Vector2
import pygame
from sprites import Crab, Food, Fish

class MovementStrategy:
    def move(self, sprite):
        pass

class SoloFishMovement(MovementStrategy):
    def move(self, sprite):
        sprite.add_random_velocity_change()
        sprite.avoid(sprite.get_sprites_of_type(Crab), 200)
        sprite.align_near(sprite.get_sprites_of_type(Food), 0)
        # Check for collision with food
        for food in sprite.get_sprites_of_type(Food):
            if pygame.sprite.collide_rect(sprite, food):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0

class SchoolingFishMovement(MovementStrategy):
    def move(self, sprite):
        # Align with and avoid other schooling fish
        schooling_fish_sprites = [other_sprite for other_sprite in sprite.get_sprites_of_type(Fish)
                                  if other_sprite.animation_frames == sprite.animation_frames]
        sprite.align_near(schooling_fish_sprites, 25)

        sprite.add_random_velocity_change()

        # Avoid single fish
        solo_fish_sprites = [other_sprite for other_sprite in sprite.get_sprites_of_type(Fish)
                             if other_sprite.animation_frames != sprite.animation_frames]
        sprite.avoid(solo_fish_sprites, 100)

        # Avoid crabs
        sprite.avoid(sprite.get_sprites_of_type(Crab), 200)
        
        # Seek food
        sprite.align_near(sprite.get_sprites_of_type(Food), 0)
        for food in sprite.get_sprites_of_type(Food):
            if pygame.sprite.collide_rect(sprite, food):
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


