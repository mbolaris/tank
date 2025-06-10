import random
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE, NUM_SCHOOLING_FISH, FILES, INIT_POS
import agents
import movement_strategy
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
            agents.Fish(self.environment, movement_strategy.SoloFishMovement(), FILES['solo_fish'], *INIT_POS['fish'], 3),
            agents.Crab(self.environment),
            agents.Plant(self.environment, 1),
            agents.Plant(self.environment, 2),
            agents.Castle(self.environment),
        )

        for _ in range(NUM_SCHOOLING_FISH):
            self.agents.add(agents.Fish(self.environment, movement_strategy.SchoolingFishMovement(), FILES['schooling_fish'], *INIT_POS['school'], 4))

    def update(self):
        """Update the state of the simulation."""
        elapsed_time = pygame.time.get_ticks() - self.start_ticks
        self.handle_collisions()

        for sprite in self.agents:
            sprite.update(elapsed_time)
            self.keep_sprite_on_screen(sprite)
            if isinstance(sprite, agents.Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:
                sprite.kill()

    def handle_collisions(self):
        """Handle collisions between sprites."""
        self.handle_fish_collisions()
        self.handle_food_collisions()

    def handle_fish_collisions(self):
        """Handle collisions involving fish."""
        for fish in self.agents.sprites():
            if isinstance(fish, agents.Fish):
                collisions = pygame.sprite.spritecollide(fish, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, agents.Crab):
                        fish.kill()
                    elif isinstance(collision_sprite, agents.Food):
                        fish.eat(collision_sprite)

    def handle_food_collisions(self):
        """Handle collisions involving food."""
        for food in self.agents.sprites():
            if isinstance(food, agents.Food):
                collisions = pygame.sprite.spritecollide(food, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, (agents.Fish, agents.Crab)):
                        food.get_eaten()

    def keep_sprite_on_screen(self, sprite):
        """Keep a sprite within the bounds of the screen."""
        sprite.rect.clamp_ip(self.screen.get_rect())

    def render(self):
        """Render the current state of the simulation to the screen."""
        self.screen.fill((0, 0, 0))
        self.agents.draw(self.screen)
        pygame.display.flip()

    def handle_events(self):
        """Handle user input and other events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                x = random.randint(0, SCREEN_WIDTH)
                y = 0  # Food will drop from the top of the screen
                food = agents.Food(self.environment, x, y)
                self.agents.add(food)
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
    try:
        game.run()
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
