import pygame
import random

# Initialize pygame
pygame.init()

class Constants:
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600

    FILES = {
        'fish': ['george1.png', 'george2.png'],
        'crab': ['crab1.png', 'crab2.png'],
        'school': ['school.png'],
        'plant': ['plant1.png'],
        'plants': ['plant2.png'],
        'castle': ['castle.png'],
    }

    INIT_POS = {
        'fish': (275, 80, -4),
        'crab': (250, 542, 1),
        'school': (300, 30, 5),
        'plant': (250, 500, 0),
        'plants': (10, 500, 0),
        'castle': (100, 500, 0),
    }

def flip_image(image):
    return pygame.transform.flip(image, True, False)

class MoveStrategy:
    def move(self, sprite, elapsed_time):
        sprite.rect.x += sprite.speed
        if sprite.rect.x < 0 or sprite.rect.right > Constants.SCREEN_WIDTH:
            sprite.speed *= -1  # Change the direction first
        sprite.image = sprite.get_current_image()  # Update self.image according to the new direction
        if len(sprite.original_images) > 1:
            sprite.image_index = (elapsed_time // 500) % len(sprite.original_images)
            sprite.image = sprite.get_current_image()

class SchoolMoveStrategy(MoveStrategy):
    def move(self, sprite, elapsed_time):
        super().move(sprite, elapsed_time)
        sprite.rect.y += random.randint(-1, 1)

class Sprite:
    def __init__(self, screen, filenames: list, x: int, y: int, speed: int, move_strategy: MoveStrategy = MoveStrategy()):
        self.screen = screen
        self.original_images = [pygame.image.load(filename).convert_alpha() for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.rect = self.original_images[self.image_index].get_rect()
        self.rect.topleft = (x, y)
        self.image = self.get_current_image()
        self.move_strategy = move_strategy

    def get_current_image(self):
        if self.speed > 0:  # Moving right
            return self.original_images[self.image_index]
        else:  # Moving left
            # Make sure the images are flipped
            return flip_image(self.original_images[self.image_index])

    def display(self):
        self.screen.blit(self.image, self.rect.topleft)

    def update(self, elapsed_time):
        self.move_strategy.move(self, elapsed_time)

class Fish(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['fish'], *Constants.INIT_POS['fish'])

class Crab(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['crab'], *Constants.INIT_POS['crab'])

class School(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['school'], *Constants.INIT_POS['school'], move_strategy=SchoolMoveStrategy())

class Plant(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['plant'], *Constants.INIT_POS['plant'])

class Plants(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['plants'], *Constants.INIT_POS['plants'])

class Castle(Sprite):
    def __init__(self, screen):
        super().__init__(screen, Constants.FILES['castle'], *Constants.INIT_POS['castle'])

class Game:
    def __init__(self):
        # Setup the display
        self.screen = pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))

        # Setup the clock for framerate control
        self.clock = pygame.time.Clock()

        self.sprites = [
            Fish(self.screen),
            Crab(self.screen),
            School(self.screen),
            Plant(self.screen),
            Plants(self.screen),
            Castle(self.screen),
        ]
        self.start_ticks = pygame.time.get_ticks()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

            self.screen.fill((0, 0, 0))
            elapsed_time = pygame.time.get_ticks() - self.start_ticks

            for sprite in self.sprites:
                sprite.display()
                sprite.update(elapsed_time)

            pygame.display.flip()
            self.clock.tick(30)

if __name__ == "__main__":
    game = Game()
    game.run()
