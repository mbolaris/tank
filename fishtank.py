import random
import pygame
from typing import Optional, List
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE,
    POKER_NOTIFICATION_DURATION, POKER_NOTIFICATION_MAX_COUNT,
    POKER_TIE_COLOR, POKER_WIN_COLOR
)
import agents
from core import environment
from core.ecosystem import EcosystemManager
from core.time_system import TimeSystem
from core.fish_poker import PokerInteraction
from core.simulators.base_simulator import BaseSimulator
from rendering.ui_renderer import UIRenderer
from agents_factory import create_initial_agents

class FishTankSimulator(BaseSimulator):
    """A simulation of a fish tank with full ecosystem dynamics.

    Attributes:
        agents: All agents in the simulation
        environment: Environment for agent queries
        ecosystem: Ecosystem manager for population tracking
        time_system: Day/night cycle manager
        screen: Pygame display surface
        clock: Pygame clock for frame rate
        frame_count: Total frames elapsed
        stats_font: Font for rendering statistics
        paused: Whether simulation is paused
    """

    def __init__(self) -> None:
        """Initialize the simulation."""
        super().__init__()
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.start_ticks: int = pygame.time.get_ticks()
        self.agents: pygame.sprite.Group = pygame.sprite.Group()
        self.screen: Optional[pygame.Surface] = None
        self.environment: Optional[environment.Environment] = None
        self.time_system: TimeSystem = TimeSystem()
        self.stats_font: Optional[pygame.font.Font] = None
        self.ui_renderer: Optional[UIRenderer] = None
        self.show_stats_hud: bool = True  # Toggle for stats and health bars
        self.poker_notifications: List[dict] = []  # List of poker game notifications

    def setup_game(self) -> None:
        """Setup the game."""
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("ALife Fish Tank - Ecosystem Simulation")
        except pygame.error as e:
            print(f"Couldn't set the display mode. Error: {e}")
            return

        # Initialize font for stats
        self.stats_font = pygame.font.Font(None, 24)

        # Initialize UI renderer
        self.ui_renderer = UIRenderer(self.screen, self.stats_font)

        # Initialize managers
        self.environment = environment.Environment(self.agents)
        self.ecosystem = EcosystemManager(max_population=100)  # Increased from 50 for natural growth

        self.create_initial_agents()

    def create_initial_agents(self) -> None:
        """Create initial sprites in the fish tank with multiple species."""
        if self.environment is None or self.ecosystem is None:
            return

        # Use centralized factory function for initial population
        population = create_initial_agents(self.environment, self.ecosystem)
        self.agents.add(*population)

    # Implement abstract methods from BaseSimulator
    def get_all_entities(self) -> List[agents.Agent]:
        """Get all entities in the simulation."""
        return list(self.agents.sprites())

    def add_entity(self, entity: agents.Agent) -> None:
        """Add an entity to the simulation."""
        self.agents.add(entity)

    def remove_entity(self, entity: agents.Agent) -> None:
        """Remove an entity from the simulation."""
        entity.kill()

    def check_collision(self, e1: agents.Agent, e2: agents.Agent) -> bool:
        """Check if two entities collide using pygame collision detection."""
        return pygame.sprite.collide_rect(e1, e2)

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle the result of a poker game by adding a notification."""
        self.add_poker_notification(poker)

    def update(self) -> None:
        """Update the state of the simulation."""
        if self.paused:
            return

        elapsed_time = pygame.time.get_ticks() - self.start_ticks
        self.frame_count += 1

        # Update time system
        self.time_system.update()
        time_modifier = self.time_system.get_activity_modifier()

        # Track new agents (births, food production)
        new_agents: List[agents.Agent] = []

        # Update all agents
        for sprite in list(self.agents):
            # Update based on agent type
            if isinstance(sprite, agents.Fish):
                # Fish update returns potential newborn
                newborn = sprite.update(elapsed_time, time_modifier)
                if newborn is not None and self.ecosystem is not None:
                    # Check carrying capacity
                    if self.ecosystem.can_reproduce(self.get_fish_count()):
                        new_agents.append(newborn)

                # Handle fish death
                if sprite.is_dead():
                    self.record_fish_death(sprite)

            elif isinstance(sprite, agents.Plant):
                # Plant update returns potential food
                food = sprite.update(elapsed_time, time_modifier)
                if food is not None:
                    new_agents.append(food)

            else:
                # Other agents (Crab, Castle, Food)
                sprite.update(elapsed_time)

            # Keep sprite on screen
            self.keep_sprite_on_screen(sprite)

            # Remove food that fell off screen
            if isinstance(sprite, agents.Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:
                sprite.kill()

        # Add new agents
        for new_agent in new_agents:
            self.add_entity(new_agent)

        # Automatic food spawning
        if self.environment is not None:
            self.spawn_auto_food(self.environment)
            # Update pygame rect for the last spawned food
            for sprite in self.agents:
                if isinstance(sprite, agents.Food) and sprite.pos.y == 0:
                    sprite.rect.y = 0

        # Handle collisions
        self.handle_collisions()

        # Handle reproduction (mate finding)
        self.handle_reproduction()

        # Update poker notifications
        self.update_poker_notifications()

        # Update ecosystem stats
        if self.ecosystem is not None:
            self.ecosystem.update_population_stats(self.get_fish_list())
            self.ecosystem.update(self.frame_count)

        # Update UI renderer frame count
        if self.ui_renderer is not None:
            self.ui_renderer.set_frame_count(self.frame_count)


    def add_poker_notification(self, poker: PokerInteraction) -> None:
        """Add a notification for a poker game result."""
        if poker.result is None:
            return

        # Create notification message
        result = poker.result
        if result.winner_id == -1:
            # Tie
            message = f"Poker: Fish #{result.loser_id} vs Fish #{result.winner_id} - TIE! ({result.hand1.description})"
            color = POKER_TIE_COLOR
        else:
            # Winner
            winner_hand = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
            loser_hand = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1
            message = f"Poker: Fish #{result.winner_id} beats Fish #{result.loser_id} with {winner_hand.description}! (+{result.energy_transferred:.1f} energy)"
            color = POKER_WIN_COLOR

        # Add to notification list with timestamp
        notification = {
            'message': message,
            'color': color,
            'frame': self.frame_count,
            'duration': POKER_NOTIFICATION_DURATION
        }
        self.poker_notifications.append(notification)

        # Keep only last N notifications
        if len(self.poker_notifications) > POKER_NOTIFICATION_MAX_COUNT:
            self.poker_notifications.pop(0)

    def update_poker_notifications(self) -> None:
        """Update poker notifications and remove expired ones."""
        # Remove expired notifications
        self.poker_notifications = [
            notif for notif in self.poker_notifications
            if self.frame_count - notif['frame'] < notif['duration']
        ]

    def keep_sprite_on_screen(self, sprite: agents.Agent) -> None:
        """Keep a sprite fully within the bounds of the screen.

        This is a pygame-specific wrapper around the base class method.
        """
        if self.screen is not None:
            # Call base class method
            self.keep_entity_on_screen(sprite)
            # Update pygame rect to match position
            sprite.rect.left = int(sprite.pos.x)
            sprite.rect.top = int(sprite.pos.y)

    def render(self) -> None:
        """Render the current state of the simulation to the screen."""
        if self.screen is None:
            return

        # Fill with base color (dark water)
        self.screen.fill((10, 30, 50))

        # Apply day/night tint
        brightness = self.time_system.get_brightness()
        tint_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        tint_color = self.time_system.get_screen_tint()
        tint_surface.fill(tint_color)
        tint_surface.set_alpha(int((1.0 - brightness) * 100))
        self.screen.blit(tint_surface, (0, 0))

        # Draw all sprites
        self.agents.draw(self.screen)

        # Draw health bars and stats panel (if HUD is enabled)
        if self.show_stats_hud and self.ui_renderer is not None and self.ecosystem is not None:
            # Draw health bars for fish
            for sprite in self.agents:
                if isinstance(sprite, agents.Fish):
                    self.ui_renderer.draw_health_bar(sprite)

            # Draw stats panel
            self.ui_renderer.draw_stats_panel(self.ecosystem, self.time_system, self.paused, self.get_all_entities())

        # Draw poker notifications (always visible)
        if self.ui_renderer is not None:
            self.ui_renderer.draw_poker_notifications(self.poker_notifications)

        pygame.display.flip()

    def handle_events(self) -> bool:
        """Handle user input and other events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Drop food manually (still available)
                    if self.environment is not None:
                        x = random.randint(0, SCREEN_WIDTH)
                        y = 0  # Food will drop from the top of the screen
                        food = agents.Food(self.environment, x, y, allow_stationary_types=False)
                        self.agents.add(food)
                elif event.key == pygame.K_p:
                    # Toggle pause
                    self.paused = not self.paused
                elif event.key == pygame.K_h:
                    # Toggle stats and health bars HUD
                    self.show_stats_hud = not self.show_stats_hud
                elif event.key == pygame.K_r:
                    # Print algorithm performance report
                    if self.ecosystem is not None:
                        print("\n" + "=" * 80)
                        print("GENERATING ALGORITHM PERFORMANCE REPORT...")
                        print("=" * 80)
                        report = self.ecosystem.get_algorithm_performance_report()
                        print(report)
                        # Also save to file
                        with open('algorithm_performance_report.txt', 'w') as f:
                            f.write(report)
                        print("\nReport saved to: algorithm_performance_report.txt")
                        print("=" * 80 + "\n")
                elif event.key == pygame.K_ESCAPE:
                    # Quit
                    return False
        return True

    def run(self) -> None:
        """Run the simulation."""
        self.setup_game()

        # Print welcome message
        print("=" * 60)
        print("ARTIFICIAL LIFE FISH TANK SIMULATION")
        print("=" * 60)
        print("Controls:")
        print("  SPACE - Drop food manually")
        print("  P     - Pause/Resume")
        print("  H     - Toggle stats/health bars")
        print("  R     - Generate algorithm performance report")
        print("  ESC   - Quit")
        print()
        print("Features:")
        print("  * Genetics & Evolution")
        print("  * ALGORITHMIC EVOLUTION - 48 Behavior Algorithms! (NEW)")
        print("  * Energy & Metabolism")
        print("  * Life Cycles (Baby -> Juvenile -> Adult -> Elder)")
        print("  * Reproduction with genetic mixing")
        print("  * Parameter mutations for algorithm tuning")
        print("  * Day/Night cycles")
        print("  * Plants produce food")
        print("  * Population dynamics")
        print("=" * 60)
        print()

        while self.handle_events():
            self.update()
            self.render()
            self.clock.tick(FRAME_RATE)

        # Print final statistics
        if self.ecosystem is not None:
            print("\n" + "=" * 60)
            print("SIMULATION ENDED - Final Statistics")
            print("=" * 60)
            stats = self.ecosystem.get_summary_stats(self.get_all_entities())
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print("=" * 60)

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
