import random
import pygame
from typing import Optional, List
from core.constants import (SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE, NUM_SCHOOLING_FISH, FILES, INIT_POS,
                       AUTO_FOOD_SPAWN_RATE, AUTO_FOOD_ENABLED)
import agents
import movement_strategy
from core import environment
from core.ecosystem import EcosystemManager
from core.time_system import TimeSystem
from core.genetics import Genome
from core.behavior_algorithms import get_algorithm_index
from evolution_viz import EvolutionVisualizer, SpeciesTracker
from core.fish_poker import PokerInteraction

class FishTankSimulator:
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
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.start_ticks: int = pygame.time.get_ticks()
        self.frame_count: int = 0
        self.agents: pygame.sprite.Group = pygame.sprite.Group()
        self.screen: Optional[pygame.Surface] = None
        self.environment: Optional[environment.Environment] = None
        self.ecosystem: Optional[EcosystemManager] = None
        self.time_system: TimeSystem = TimeSystem()
        self.stats_font: Optional[pygame.font.Font] = None
        self.paused: bool = False
        self.show_stats_hud: bool = True  # Toggle for stats and health bars
        self.auto_food_timer: int = 0  # Timer for automatic food spawning

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

        # Initialize managers
        self.environment = environment.Environment(self.agents)
        self.ecosystem = EcosystemManager(max_population=100)  # Increased from 50 for natural growth

        self.create_initial_agents()

    def create_initial_agents(self) -> None:
        """Create initial sprites in the fish tank with multiple species."""
        if self.environment is None or self.ecosystem is None:
            return

        # Species 1: Solo fish with traditional AI (rule-based)
        solo_fish = agents.Fish(
            self.environment,
            movement_strategy.SoloFishMovement(),
            FILES['solo_fish'],
            *INIT_POS['fish'],
            3,
            generation=0,
            ecosystem=self.ecosystem
        )

        # Species 2: Algorithmic fish with parametrizable behavior algorithms (NEW!)
        # These fish use the new algorithmic evolution system
        algorithmic_fish = []
        for i in range(2):  # Start with 2 algorithmic fish for sustainable population
            x = INIT_POS['school'][0] + random.randint(-80, 80)
            y = INIT_POS['school'][1] + random.randint(-50, 50)
            # Create genome WITH behavior algorithm but WITHOUT neural brain
            genome = Genome.random(use_brain=False, use_algorithm=True)
            fish = agents.Fish(
                self.environment,
                movement_strategy.AlgorithmicMovement(),
                FILES['schooling_fish'],
                x, y,
                4,
                genome=genome,
                generation=0,
                ecosystem=self.ecosystem
            )
            algorithmic_fish.append(fish)

        # Species 3: Schooling fish with neural network brains (learning AI)
        neural_schooling_fish = []
        for i in range(2):  # Fewer neural fish to start
            x = INIT_POS['school'][0] + random.randint(-50, 50)
            y = INIT_POS['school'][1] + random.randint(-30, 30)
            # Neural fish should NOT have algorithmic behavior (use brain instead)
            genome = Genome.random(use_brain=True, use_algorithm=False)
            fish = agents.Fish(
                self.environment,
                movement_strategy.NeuralMovement(),
                FILES['schooling_fish'],
                x, y,
                4,
                genome=genome,
                generation=0,
                ecosystem=self.ecosystem
            )
            neural_schooling_fish.append(fish)

        # Species 4: Traditional schooling fish (rule-based AI)
        schooling_fish = []
        for i in range(2):  # Also 2 traditional schooling fish
            x = INIT_POS['school'][0] + random.randint(-50, 50)
            y = INIT_POS['school'][1] + random.randint(-30, 30)
            # Create genome without neural brain or algorithm (uses movement strategy only)
            genome = Genome.random(use_brain=False, use_algorithm=False)
            fish = agents.Fish(
                self.environment,
                movement_strategy.SchoolingFishMovement(),
                FILES['schooling_fish'],
                x, y,
                4,
                genome=genome,
                generation=0,
                ecosystem=self.ecosystem
            )
            schooling_fish.append(fish)

        # Create plants
        plant1 = agents.Plant(self.environment, 1)
        plant2 = agents.Plant(self.environment, 2)
        # Third plant manually positioned
        plant3 = agents.Plant(self.environment, 1)
        plant3.pos.x = INIT_POS['plant3'][0]
        plant3.pos.y = INIT_POS['plant3'][1]
        plant3.rect.topleft = (plant3.pos.x, plant3.pos.y)

        # Add all agents
        self.agents.add(
            solo_fish,
            *algorithmic_fish,  # NEW: Algorithmic evolution fish!
            *neural_schooling_fish,  # Neural network fish
            *schooling_fish,  # Traditional rule-based fish
            agents.Crab(self.environment),  # Re-enabled with better balance!
            plant1,
            plant2,
            plant3,
            agents.Castle(self.environment),
        )

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
                    fish_count = len([a for a in self.agents if isinstance(a, agents.Fish)])
                    if self.ecosystem.can_reproduce(fish_count):
                        new_agents.append(newborn)

                # Handle fish death
                if sprite.is_dead():
                    if self.ecosystem is not None:
                        # Get algorithm ID if fish has a behavior algorithm
                        algorithm_id = None
                        if sprite.genome.behavior_algorithm is not None:
                            algorithm_id = get_algorithm_index(sprite.genome.behavior_algorithm)
                        self.ecosystem.record_death(
                            sprite.fish_id,
                            sprite.generation,
                            sprite.age,
                            sprite.get_death_cause(),
                            sprite.genome,
                            algorithm_id=algorithm_id
                        )
                    sprite.kill()

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
        if new_agents:
            self.agents.add(*new_agents)

        # Automatic food spawning
        if AUTO_FOOD_ENABLED and self.environment is not None:
            self.auto_food_timer += 1
            if self.auto_food_timer >= AUTO_FOOD_SPAWN_RATE:
                self.auto_food_timer = 0
                # Spawn food from the top at random x position
                x = random.randint(0, SCREEN_WIDTH)
                food = agents.Food(
                    self.environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False
                )
                # Ensure the food starts exactly at the top edge before falling
                food.pos.y = 0
                food.rect.y = 0
                self.agents.add(food)

        # Handle collisions
        self.handle_collisions()

        # Handle reproduction (mate finding)
        self.handle_reproduction()

        # Update ecosystem stats
        if self.ecosystem is not None:
            fish_list = [a for a in self.agents if isinstance(a, agents.Fish)]
            self.ecosystem.update_population_stats(fish_list)
            self.ecosystem.update(self.frame_count)

    def handle_collisions(self) -> None:
        """Handle collisions between sprites."""
        self.handle_fish_collisions()
        self.handle_food_collisions()

    def handle_fish_collisions(self) -> None:
        """Handle collisions involving fish."""
        # Iterate over a copy to safely remove sprites during iteration
        for fish in list(self.agents.sprites()):
            if isinstance(fish, agents.Fish):
                collisions = pygame.sprite.spritecollide(fish, self.agents, False, pygame.sprite.collide_rect)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, agents.Crab):
                        # Crab can only kill if hunt cooldown is ready
                        if collision_sprite.can_hunt():
                            # Record death from predation
                            if self.ecosystem is not None:
                                # Get algorithm ID if fish has a behavior algorithm
                                algorithm_id = None
                                if fish.genome.behavior_algorithm is not None:
                                    algorithm_id = get_algorithm_index(fish.genome.behavior_algorithm)
                                self.ecosystem.record_death(
                                    fish.fish_id,
                                    fish.generation,
                                    fish.age,
                                    'predation',
                                    fish.genome,
                                    algorithm_id=algorithm_id
                                )
                            collision_sprite.eat_fish(fish)
                            fish.kill()
                    elif isinstance(collision_sprite, agents.Food):
                        fish.eat(collision_sprite)
                    elif isinstance(collision_sprite, agents.Fish):
                        # Fish-to-fish poker interaction
                        poker = PokerInteraction(fish, collision_sprite)
                        poker.play_poker()

    def handle_food_collisions(self) -> None:
        """Handle collisions involving food."""
        # Iterate over a copy to safely remove sprites during iteration
        for food in list(self.agents.sprites()):
            if isinstance(food, agents.Food):
                collisions = pygame.sprite.spritecollide(food, self.agents, False, pygame.sprite.collide_rect)
                for collision_sprite in collisions:
                    if isinstance(collision_sprite, agents.Fish):
                        food.get_eaten()
                    elif isinstance(collision_sprite, agents.Crab):
                        collision_sprite.eat_food(food)
                        food.get_eaten()

    def handle_reproduction(self) -> None:
        """Handle fish reproduction by finding mates."""
        # Get all fish
        fish_list = [a for a in self.agents if isinstance(a, agents.Fish)]

        # Try to mate fish that are ready
        for fish in fish_list:
            if not fish.can_reproduce():
                continue

            # Look for nearby compatible mates
            for potential_mate in fish_list:
                if potential_mate == fish:
                    continue

                # Attempt mating
                if fish.try_mate(potential_mate):
                    break  # Found a mate, stop looking

    def keep_sprite_on_screen(self, sprite: agents.Agent) -> None:
        """Keep a sprite fully within the bounds of the screen."""
        if self.screen is not None:
            # Clamp horizontally
            if sprite.rect.left < 0:
                sprite.rect.left = 0
                sprite.pos.x = sprite.rect.left
            elif sprite.rect.right > SCREEN_WIDTH:
                sprite.rect.right = SCREEN_WIDTH
                sprite.pos.x = sprite.rect.left

            # Clamp vertically
            if sprite.rect.top < 0:
                sprite.rect.top = 0
                sprite.pos.y = sprite.rect.top
            elif sprite.rect.bottom > SCREEN_HEIGHT:
                sprite.rect.bottom = SCREEN_HEIGHT
                sprite.pos.y = sprite.rect.top

    def draw_health_bar(self, fish: agents.Fish) -> None:
        """Draw health/energy bar above a fish.

        Args:
            fish: The fish to draw health bar for
        """
        if self.screen is None:
            return

        # Health bar dimensions
        bar_width = 30
        bar_height = 4
        bar_x = fish.rect.centerx - bar_width // 2
        bar_y = fish.rect.top - 8

        # Background (empty bar)
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        # Foreground (filled based on energy)
        energy_ratio = fish.energy / fish.max_energy
        filled_width = int(bar_width * energy_ratio)

        # Color based on energy level
        if energy_ratio > 0.6:
            color = (50, 200, 50)  # Green
        elif energy_ratio > 0.3:
            color = (200, 200, 50)  # Yellow
        else:
            color = (200, 50, 50)  # Red

        if filled_width > 0:
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, filled_width, bar_height))

        # Display algorithm number if fish has a behavior algorithm
        if fish.genome.behavior_algorithm is not None:
            algo_index = get_algorithm_index(fish.genome.behavior_algorithm)

            if algo_index >= 0:
                # Create a small font for the algorithm number
                small_font = pygame.font.Font(None, 16)
                algo_text = f"#{algo_index}"
                text_surface = small_font.render(algo_text, True, (200, 200, 200))

                # Position text below the health bar, centered
                text_x = fish.rect.centerx - text_surface.get_width() // 2
                text_y = bar_y + bar_height + 1

                self.screen.blit(text_surface, (text_x, text_y))

    def draw_stats_panel(self) -> None:
        """Draw statistics panel showing ecosystem data."""
        if self.screen is None or self.stats_font is None or self.ecosystem is None:
            return

        # Semi-transparent background (larger to fit poker stats)
        panel_surface = pygame.Surface((280, 300))
        panel_surface.set_alpha(200)
        panel_surface.fill((20, 20, 40))
        self.screen.blit(panel_surface, (10, 10))

        # Get stats
        stats = self.ecosystem.get_summary_stats()
        time_str = self.time_system.get_time_string()

        # Render text lines
        y_offset = 15
        lines = [
            f"Time: {time_str}",
            f"Population: {stats['total_population']}/{self.ecosystem.max_population}",
            f"Generation: {stats['current_generation']}",
            f"Births: {stats['total_births']}",
            f"Deaths: {stats['total_deaths']}",
            f"Capacity: {stats['capacity_usage']}",
        ]

        # Add death causes
        if stats['death_causes']:
            lines.append("Death Causes:")
            for cause, count in stats['death_causes'].items():
                lines.append(f"  {cause}: {count}")

        # Add poker stats (always show, even if no games played yet)
        poker = stats.get('poker_stats', {})
        if poker:
            lines.append("")
            lines.append("Poker Stats:")
            if poker.get('total_games', 0) == 0:
                lines.append(("  No poker games yet (need 10+ energy & collision)", (150, 150, 150)))
            else:
                lines.append(f"  Games: {poker['total_games']}")
                lines.append(f"  Wins/Losses/Ties: {poker['total_wins']}/{poker['total_losses']}/{poker['total_ties']}")
                lines.append(f"  Energy Won: {poker['total_energy_won']:.1f}")
                lines.append(f"  Energy Lost: {poker['total_energy_lost']:.1f}")
                net_energy = poker['net_energy']
                net_color = (100, 255, 100) if net_energy >= 0 else (255, 100, 100)
                lines.append((f"  Net Energy: {net_energy:+.1f}", net_color))
                lines.append(f"  Best Hand: {poker['best_hand_name']}")

        for line in lines:
            # Check if line is a tuple (text, color)
            if isinstance(line, tuple):
                text, color = line
                text_surface = self.stats_font.render(text, True, color)
            else:
                text_surface = self.stats_font.render(line, True, (220, 220, 255))
            self.screen.blit(text_surface, (20, y_offset))
            y_offset += 22

        # Show pause indicator
        if self.paused:
            pause_text = self.stats_font.render("PAUSED", True, (255, 200, 100))
            self.screen.blit(pause_text, (SCREEN_WIDTH // 2 - 40, 10))

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
        if self.show_stats_hud:
            # Draw health bars for fish
            for sprite in self.agents:
                if isinstance(sprite, agents.Fish):
                    self.draw_health_bar(sprite)

            # Draw stats panel
            self.draw_stats_panel()

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
            stats = self.ecosystem.get_summary_stats()
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
