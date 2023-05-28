import pygame
import random

# Initialize pygame
pygame.init()

# Screen parameters
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Setup the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Setup the clock for framerate control
clock = pygame.time.Clock()

class Sprite:
    def __init__(self, filenames: list, x: int, y: int, speed: int):
        self.original_images = [pygame.image.load(filename).convert_alpha() for filename in filenames]
        self.image_index = 0
        self.speed = speed
        self.rect = self.original_images[self.image_index].get_rect()
        self.rect.topleft = (x, y)
        self.image = self.get_current_image()

    def flip_image(self, image):
        return pygame.transform.flip(image, True, False)

    def get_current_image(self):
        if self.speed > 0:  # Moving right
            return self.original_images[self.image_index]
        else:  # Moving left
            # Make sure the images are flipped
            return self.flip_image(self.original_images[self.image_index])

    def display(self, screen):
        screen.blit(self.image, self.rect.topleft)

    def update(self, elapsed_time):
        self.rect.x += self.speed
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.speed *= -1  # Change the direction first

        self.image = self.get_current_image()  # Update self.image according to the new direction

        # Check if sprite has multiple images
        if len(self.original_images) > 1:
            # Update the image index based on elapsed time
            self.image_index = (elapsed_time // 500) % len(self.original_images)
            self.image = self.get_current_image()

        if self == sprites['school']:
            self.rect.y += random.randint(-1, 1)


# Define all the sprites with their initial positions
sprites = {
    'fish': Sprite(['george1.png', 'george2.png'], 275, 80, -4),  # Now we only need one image for 'fish' sprite
    'crab': Sprite(['crab1.png', 'crab2.png'], 250, 542, 1),
    'school': Sprite(['school.png'], 300, 30, 5),  # Now we only need one image for 'school' sprite
    'plant': Sprite(['plant1.png'], 250, 500, 0),
    'plants': Sprite(['plant2.png'], 10, 500, 0),
    'castle': Sprite(['castle.png'], 100, 500, 0),
}

# Main game loop
start_ticks = pygame.time.get_ticks()  # Starter tick
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()

    screen.fill((0, 0, 0))
    elapsed_time = pygame.time.get_ticks() - start_ticks

    for sprite in sprites.values():
        sprite.display(screen)
        sprite.update(elapsed_time)

    pygame.display.flip()
    clock.tick(30)
