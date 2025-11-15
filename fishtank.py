import random
import pygame
from typing import Optional
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE, NUM_SCHOOLING_FISH, FILES, INIT_POS
import agents
import movement_strategy
import environment

class FishTankSimulator:
    """A simulation of a fish tank."""

    def __init__(self) -> None:
        """Initialize the simulation."""
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.start_ticks: int = pygame.time.get_ticks()
        self.agents: pygame.sprite.Group = pygame.sprite.Group()
        self.screen: Optional[pygame.Surface] = None
        self.environment: Optional[environment.Environment] = None

    def setup_game(self) -> None:
        """Setup the game."""
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Couldn't set the display mode. Error: {e}")
            return
        self.environment = environment.Environment(self.agents)
        self.create_initial_agents()

    def create_initial_agents(self) -> None:
        """Create initial sprites in the fish tank."""
        if self.environment is None:
            return
        self.agents.add(
            agents.Fish(self.environment, movement_strategy.SoloFishMovement(), FILES['solo_fish'], *INIT_POS['fish'], 3),
            agents.Crab(self.environment),
            agents.Plant(self.environment, 1),
            agents.Plant(self.environment, 2),
            agents.Castle(self.environment),
        )

        for _ in range(NUM_SCHOOLING_FISH):
            self.agents.add(agents.Fish(self.environment, movement_strategy.SchoolingFishMovement(), FILES['schooling_fish'], *INIT_POS['school'], 4))

    def update(self) -> None:
        """Update the state of the simulation."""
        elapsed_time = pygame.time.get_ticks() - self.start_ticks
        self.handle_collisions()

        for sprite in self.agents:
            sprite.update(elapsed_time)
            self.keep_sprite_on_screen(sprite)
            if isinstance(sprite, agents.Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:
                sprite.kill()

    def handle_collisions(self) -> None:
        """Handle collisions between sprites."""
        self.handle_fish_collisions()
        self.handle_food_collisions()

    def handle_fish_collisions(self) -> None:
        """Handle collisions involving fish."""
        # Iterate over a copy to safely remove sprites during iteration
        for fish in list(self.agents.sprites()):
            if isinstance(fish, agents.Fish):
                collisions = pygame.sprite.spritecollide(fish, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, agents.Crab):
                        fish.kill()
                    elif isinstance(collision_sprite, agents.Food):
                        fish.eat(collision_sprite)

    def handle_food_collisions(self) -> None:
        """Handle collisions involving food."""
        # Iterate over a copy to safely remove sprites during iteration
        for food in list(self.agents.sprites()):
            if isinstance(food, agents.Food):
                collisions = pygame.sprite.spritecollide(food, self.agents, False, pygame.sprite.collide_mask)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, (agents.Fish, agents.Crab)):
                        food.get_eaten()

    def keep_sprite_on_screen(self, sprite: agents.Agent) -> None:
        """Keep a sprite within the bounds of the screen."""
        if self.screen is not None:
            sprite.rect.clamp_ip(self.screen.get_rect())

    def render(self) -> None:
        """Render the current state of the simulation to the screen."""
        if self.screen is not None:
            self.screen.fill((0, 0, 0))
            self.agents.draw(self.screen)
            pygame.display.flip()

    def handle_events(self) -> bool:
        """Handle user input and other events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if self.environment is not None:
                    x = random.randint(0, SCREEN_WIDTH)
                    y = 0  # Food will drop from the top of the screen
                    food = agents.Food(self.environment, x, y)
                    self.agents.add(food)
        return True

    def run(self) -> None:
        """Run the simulation."""
        self.setup_game()
        while self.handle_events():
            self.update()
            self.render()
            self.clock.tick(FRAME_RATE)
        print("Goodbye!")

def main() -> None:
    """Entry point for the simulation."""
    pygame.init()
    game = FishTankSimulator()
    try:
        game.run()
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
