import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT
import sprites

# Define constants
FRAME_RATE = 30

class FishTankSimulator:
    """A simulation of a fish tank."""
    def __init__(self):
        """Initialize the simulation."""
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Couldn't set the display mode. Error: {e}")
            return
        self.clock = pygame.time.Clock()
        self.start_ticks = pygame.time.get_ticks()
        self.sprites = pygame.sprite.Group()
        self.create_initial_sprites()

    def create_initial_sprites(self):
        """Create initial sprites in the fish tank."""
        fish1 = sprites.Fish(self.screen, self.sprites)
        
        self.sprites.add(
            fish1,
            sprites.Crab(self.screen, self.sprites),
            sprites.Plant(self.screen, 1),
            sprites.Plant(self.screen, 2),
            sprites.Castle(self.screen),
        )

        # Create multiple schooling fish
        for _ in range(5):
            schooling_fish = sprites.SchoolingFish(self.screen, self.sprites)
            self.sprites.add(schooling_fish)

    def update(self):
        """Update the state of the simulation."""
        elapsed_time = pygame.time.get_ticks() - self.start_ticks
        self.handle_collisions()

        for sprite in self.sprites:
            sprite.update(elapsed_time)
            self.keep_sprite_on_screen(sprite)
            if isinstance(sprite, sprites.Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:  # If the food has reached the bottom of the screen...
                sprite.kill()  # ...remove it

    def handle_collisions(self):
        """Handle collisions between sprites."""
        for sprite in self.sprites:  # Check all sprites
            if isinstance(sprite, (sprites.Fish, sprites.SchoolingFish)):  # Only handle fish-type sprites
                collisions = pygame.sprite.spritecollide(sprite, self.sprites, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, sprites.Crab):
                        sprite.kill()

            if isinstance(sprite, sprites.Food):  # Handle food-type sprites
                collisions = pygame.sprite.spritecollide(sprite, self.sprites, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, (sprites.Fish, sprites.SchoolingFish, sprites.Crab)):
                        sprite.kill()  # Remove the food if it collides with a fish, schooling fish, or crab

    def keep_sprite_on_screen(self, sprite):
        """Keep a sprite within the bounds of the screen."""
        sprite.rect.clamp_ip(self.screen.get_rect())

    def render(self):
        """Render the current state of the simulation to the screen."""
        self.screen.fill((0, 0, 0))
        self.sprites.draw(self.screen)
        pygame.display.flip()

    def handle_events(self):
        """Handle events from the user."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not any(isinstance(sprite, sprites.Food) for sprite in self.sprites):
                    # If the key pressed is the spacebar and there is no food already present
                    food = sprites.Food(self.screen)  # Create a new food sprite
                    self.sprites.add(food)  # Add it to the sprites group
        return True

    def run(self):
        """Run the simulation."""
        while self.handle_events():
            self.update()
            self.render()
            self.clock.tick(FRAME_RATE)
        print("Goodbye!")

def main():
    """Entry point for the simulation."""
    pygame.init()
    game = FishTankSimulator()
    game.run()
    pygame.quit()

main()
