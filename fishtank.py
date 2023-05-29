import pygame
import os
import random

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

FILES = {
    'fish': ['george1.png', 'george2.png'],
    'crab': ['crab1.png', 'crab2.png'],
    'school': ['school.png'],
    'plant': ['plant1.png', 'plant2.png'],
    'castle': ['castle.png'],
}

INIT_POS = {
    'fish': (275, 80, -4),
    'crab': (250, 542, 1),
    'school': (300, 30, 5),
    'plant1': (250, 500, 0),
    'plant2': (10, 500, 0),
    'castle': (100, 500, 0),
}

def load_image(filename):
    return pygame.image.load(filename).convert_alpha()

class Sprite:
    def __init__(self, screen, filenames, x, y, speed):
        self.screen = screen
        self.original_images = [load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.rect = self.original_images[self.image_index].get_rect()
        self.rect.topleft = (x, y)
        self.image = self.get_current_image()

    def get_current_image(self):
        if self.speed > 0:
            return self.original_images[self.image_index]
        else:
            return pygame.transform.flip(self.original_images[self.image_index], True, False)

    def display(self):
        self.screen.blit(self.image, self.rect.topleft)

    def update(self, elapsed_time):
        self.rect.x += self.speed
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.speed *= -1

        # Check if the sprite has moved out of the screen vertically
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

        if len(self.original_images) > 1:
            self.image_index = (elapsed_time // 500) % len(self.original_images)
        self.image = self.get_current_image()

class Fish(Sprite):
    def __init__(self, screen):
        super().__init__(screen, FILES['fish'], *INIT_POS['fish'])

    def update(self, elapsed_time):
        super().update(elapsed_time)
        self.add_random_motion()

    def add_random_motion(self):
        # Add small random motion to the fish
        random_motion = random.randint(-1, 1)
        self.rect.y += random_motion

class SchoolingFish(Fish):
    def __init__(self, screen, sprites):
        super().__init__(screen)
        self.original_images = [load_image(os.path.join('images', filename)) for filename in FILES['school']]
        self.sprites = sprites

        self.min_distance_to_other_schooling_fish = 50  # Minimum distance to maintain from other schooling fish
        self.min_distance_to_single_fish = 100  # Minimum distance to maintain from individual fish

    def update(self, elapsed_time):
        self.rect.x += self.speed
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.speed *= -1

        schooling_fish = [sprite for sprite in self.sprites if isinstance(sprite, SchoolingFish) and sprite != self]
        single_fish = [sprite for sprite in self.sprites if isinstance(sprite, Fish) and sprite != self and not isinstance(sprite, SchoolingFish)]

        # Align with and avoid other schooling fish
        if schooling_fish:
            self.align_with_and_avoid(schooling_fish, self.min_distance_to_other_schooling_fish)

        # Avoid single fish
        if single_fish:
            self.avoid(single_fish, self.min_distance_to_single_fish)

        self.add_random_motion()

        # Check if the sprite has moved out of the screen horizontally
        if self.rect.x < 0:
            self.rect.x = 0
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Check if the sprite has moved out of the screen vertically
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

        if len(self.original_images) > 1:
            self.image_index = (elapsed_time // 500) % len(self.original_images)
        self.image = self.get_current_image()

    def align_with_and_avoid(self, fish_list, min_distance):
        avg_x = sum(sprite.rect.x for sprite in fish_list) / len(fish_list)
        avg_y = sum(sprite.rect.y for sprite in fish_list) / len(fish_list)

        for fish in fish_list:
            distance_x = abs(self.rect.x - fish.rect.x)
            distance_y = abs(self.rect.y - fish.rect.y)
            if distance_x < min_distance or distance_y < min_distance:
                # If too close, move away
                if distance_x < min_distance:
                    self.rect.x -= (fish.rect.x - self.rect.x) / (distance_x + 1e-7)
                if distance_y < min_distance:
                    self.rect.y -= (fish.rect.y - self.rect.y) / (distance_y + 1e-7)
            else:
                # If not too close, move closer to the average position
                self.rect.x += (avg_x - self.rect.x) / (abs(avg_x - self.rect.x) + 1e-7)
                self.rect.y += (avg_y - self.rect.y) / (abs(avg_y - self.rect.y) + 1e-7)

    def avoid(self, fish_list, min_distance):
        for fish in fish_list:
            if abs(self.rect.x - fish.rect.x) < min_distance:
                self.rect.x -= (fish.rect.x - self.rect.x) / (abs(fish.rect.x - self.rect.x) + 1e-7)  # Move horizontally
            if abs(self.rect.y - fish.rect.y) < min_distance:
                self.rect.y -= (fish.rect.y - self.rect.y) / (abs(fish.rect.y - self.rect.y) + 1e-7)  # Move vertically

    def add_random_motion(self):
        # Add random motion in both x and y direction
        self.rect.x += random.randint(-1, 1)
        self.rect.y += random.randint(-1, 1)



class Crab(Sprite):
    def __init__(self, screen):
        super().__init__(screen, FILES['crab'], *INIT_POS['crab'])

class Plant(Sprite):
    def __init__(self, screen, plant_type):
        super().__init__(screen, [FILES['plant'][plant_type-1]], *INIT_POS[f'plant{plant_type}'])

class Castle(Sprite):
    def __init__(self, screen):
        super().__init__(screen, FILES['castle'], *INIT_POS['castle'])

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.start_ticks = pygame.time.get_ticks()

        self.sprites = []
        self.create_initial_sprites()
        self.create_schooling_fish()

    def create_initial_sprites(self):
        self.sprites.extend([
            Fish(self.screen),
            Crab(self.screen),
            Plant(self.screen, 1),
            Plant(self.screen, 2),
            Castle(self.screen),
        ])

    def create_schooling_fish(self):
        self.sprites.extend([
            SchoolingFish(self.screen, self.sprites),
            SchoolingFish(self.screen, self.sprites),
            SchoolingFish(self.screen, self.sprites),
        ])

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

    def update_sprites(self, elapsed_time):
        for sprite in self.sprites:
            sprite.update(elapsed_time)
            self.keep_sprite_on_screen(sprite)

    def keep_sprite_on_screen(self, sprite):
        if sprite.rect.y < 0:
            sprite.rect.y = 0
        elif sprite.rect.bottom > SCREEN_HEIGHT:
            sprite.rect.bottom = SCREEN_HEIGHT

    def render_sprites(self):
        for sprite in self.sprites:
            sprite.display()

    def run(self):
        while True:
            self.handle_events()

            self.screen.fill((0, 0, 0))
            elapsed_time = pygame.time.get_ticks() - self.start_ticks

            self.update_sprites(elapsed_time)
            self.render_sprites()

            pygame.display.flip()
            self.clock.tick(30)

def main():
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()

