import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE, NUM_SCHOOLING_FISH, FILES, INIT_POS
import agents
import movment_strategy
import environment

class FishTankSimulator:
    """A simulation of a fish tank."""
    def __init__(self):
        """Initialize the simulation."""
        self.clock = pygame.time.Clock()
        self.start_ticks = pygame.time.get_ticks()
        self.agents = pygame.sprite.Group()

    def setup_game(self):
        """Setup the game."""
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Couldn't set the display mode. Error: {e}")
            return
        self.environment  = environment.Environment(self.agents)
        self.create_initial_agents()

    def create_initial_agents(self):
        """Create initial sprites in the fish tank."""
        self.agents.add(
            agents.Fish(self.environment, movment_strategy.SoloFishMovement(), FILES['solo_fish'], *INIT_POS['fish'], 3),
            agents.Crab(self.environment),
            agents.Plant(self.environment, 1),
            agents.Plant(self.environment, 2),
            agents.Castle(self.environment),
        )

        # Create multiple schooling fish
        for _ in range(NUM_SCHOOLING_FISH):
            self.agents.add(agents.Fish(self.environment, movment_strategy.SchoolingFishMovement(), FILES['schooling_fish'], *INIT_POS['school'], 4))

    def update(self):
        """Update the state of the simulation."""
        elapsed_time = pygame.time.get_ticks() - self.start_ticks
        self.handle_collisions()

        for sprite in self.agents:
            sprite.update(elapsed_time)
            self.keep_sprite_on_screen(sprite)
            if isinstance(sprite, agents.Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:  # If the food has reached the bottom of the screen...
                sprite.kill()  # ...remove it

    def handle_collisions(self):
        """Handle collisions between sprites."""
        for sprite in self.agents:  # Check all sprites
            if isinstance(sprite, (agents.Fish)):  # Only handle fish-type sprites
                collisions = pygame.sprite.spritecollide(sprite, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, agents.Crab):
                        sprite.kill()
                    elif isinstance(collision_sprite, agents.Food):
                        sprite.grow()  # Grow the fish if it eats food
                        collision_sprite.kill()  # Remove the food

            if isinstance(sprite, agents.Food):  # Handle food-type sprites
                collisions = pygame.sprite.spritecollide(sprite, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, (agents.Fish, agents.Crab)):
                        sprite.kill()  # Remove the food if it collides with a fish, schooling fish, or crab

    def keep_sprite_on_screen(self, sprite):
        """Keep a sprite within the bounds of the screen."""
        sprite.rect.clamp_ip(self.screen.get_rect())

    def render(self):
        """Render the current state of the simulation to the screen."""
        self.screen.fill((0, 0, 0))
        self.agents.draw(self.screen)
        pygame.display.flip()

    def handle_events(self):
        """Handle events from the user."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # If the key pressed is the spacebar and there is no food already present
                    food = agents.Food(environment)  # Create a new food sprite
                    self.agents.add(food)  # Add it to the sprites group
        return True

    def run(self):
        """Run the simulation."""
        self.setup_game()
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
