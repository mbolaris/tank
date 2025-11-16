"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without pygame or any visualization code.
"""

import random
import time
from typing import List, Optional, Dict, Any
from core.constants import (SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE,
                       AUTO_FOOD_SPAWN_RATE, AUTO_FOOD_ENABLED)
from core import environment, entities
from core.ecosystem import EcosystemManager
from core.time_system import TimeSystem
from core.behavior_algorithms import get_algorithm_index
from core.fish_poker import PokerInteraction
from core.entity_factory import create_initial_population


class SimulationEngine:
    """A headless simulation engine for the fish tank ecosystem.

    This class runs the simulation without any visualization,
    allowing for faster-than-realtime execution and stats-only reporting.

    Attributes:
        entities_list: All entities in the simulation
        environment: Environment for entity queries
        ecosystem: Ecosystem manager for population tracking
        time_system: Day/night cycle manager
        frame_count: Total frames elapsed
        paused: Whether simulation is paused
        start_time: Real-world start time
    """

    def __init__(self, headless: bool = True) -> None:
        """Initialize the simulation engine.

        Args:
            headless: If True, run without any pygame dependencies
        """
        self.headless = headless
        self.frame_count: int = 0
        self.entities_list: List[entities.Agent] = []
        self.environment: Optional[environment.Environment] = None
        self.ecosystem: Optional[EcosystemManager] = None
        self.time_system: TimeSystem = TimeSystem()
        self.paused: bool = False
        self.auto_food_timer: int = 0
        self.start_time: float = time.time()
        self.poker_events: List[Dict[str, Any]] = []  # Recent poker events

    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize managers
        self.environment = environment.Environment(self.entities_list)
        self.ecosystem = EcosystemManager(max_population=100)

        self.create_initial_entities()

    def create_initial_entities(self) -> None:
        """Create initial entities in the fish tank with multiple species."""
        if self.environment is None or self.ecosystem is None:
            return

        # Use centralized factory function for initial population
        population = create_initial_population(
            self.environment,
            self.ecosystem,
            SCREEN_WIDTH,
            SCREEN_HEIGHT
        )
        self.entities_list.extend(population)

    def update(self) -> None:
        """Update the state of the simulation."""
        if self.paused:
            return

        self.frame_count += 1

        # Update time system
        self.time_system.update()
        time_modifier = self.time_system.get_activity_modifier()

        # Track new entities (births, food production)
        new_entities: List[entities.Agent] = []

        # Update all entities
        for entity in list(self.entities_list):
            # Update based on entity type
            if isinstance(entity, entities.Fish):
                # Fish update returns potential newborn
                newborn = entity.update(self.frame_count, time_modifier)
                if newborn is not None and self.ecosystem is not None:
                    # Check carrying capacity
                    fish_count = len([e for e in self.entities_list if isinstance(e, entities.Fish)])
                    if self.ecosystem.can_reproduce(fish_count):
                        new_entities.append(newborn)

                # Handle fish death
                if entity.is_dead():
                    if self.ecosystem is not None:
                        # Get algorithm ID if fish has a behavior algorithm
                        algorithm_id = None
                        if entity.genome.behavior_algorithm is not None:
                            algorithm_id = get_algorithm_index(entity.genome.behavior_algorithm)
                        self.ecosystem.record_death(
                            entity.fish_id,
                            entity.generation,
                            entity.age,
                            entity.get_death_cause(),
                            entity.genome,
                            algorithm_id=algorithm_id
                        )
                    self.entities_list.remove(entity)

            elif isinstance(entity, entities.Plant):
                # Plant update returns potential food
                food = entity.update(self.frame_count, time_modifier)
                if food is not None:
                    new_entities.append(food)

            else:
                # Other entities (Crab, Castle, Food)
                entity.update(self.frame_count)

            # Keep entity on screen
            self.keep_entity_on_screen(entity)

            # Remove food that fell off screen
            if isinstance(entity, entities.Food) and entity.pos.y >= SCREEN_HEIGHT - entity.height:
                self.entities_list.remove(entity)

        # Add new entities
        if new_entities:
            self.entities_list.extend(new_entities)

        # Automatic food spawning
        if AUTO_FOOD_ENABLED and self.environment is not None:
            self.auto_food_timer += 1
            if self.auto_food_timer >= AUTO_FOOD_SPAWN_RATE:
                self.auto_food_timer = 0
                # Spawn food from the top at random x position
                x = random.randint(0, SCREEN_WIDTH)
                food = entities.Food(
                    self.environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT
                )
                food.pos.y = 0
                self.entities_list.append(food)

        # Handle collisions
        self.handle_collisions()

        # Handle reproduction (mate finding)
        self.handle_reproduction()

        # Update ecosystem stats
        if self.ecosystem is not None:
            fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]
            self.ecosystem.update_population_stats(fish_list)
            self.ecosystem.update(self.frame_count)

    def keep_entity_on_screen(self, entity: entities.Agent) -> None:
        """Keep an entity fully within the bounds of the screen."""
        # Clamp horizontally
        if entity.pos.x < 0:
            entity.pos.x = 0
        elif entity.pos.x + entity.width > SCREEN_WIDTH:
            entity.pos.x = SCREEN_WIDTH - entity.width

        # Clamp vertically
        if entity.pos.y < 0:
            entity.pos.y = 0
        elif entity.pos.y + entity.height > SCREEN_HEIGHT:
            entity.pos.y = SCREEN_HEIGHT - entity.height

    def handle_collisions(self) -> None:
        """Handle collisions between entities using pure geometry."""
        self.handle_fish_collisions()
        self.handle_food_collisions()

    def entities_collide(self, e1: entities.Agent, e2: entities.Agent) -> bool:
        """Check if two entities collide using bounding box collision.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities overlap
        """
        # Simple bounding box collision
        return (e1.pos.x < e2.pos.x + e2.width and
                e1.pos.x + e1.width > e2.pos.x and
                e1.pos.y < e2.pos.y + e2.height and
                e1.pos.y + e1.height > e2.pos.y)

    def handle_fish_collisions(self) -> None:
        """Handle collisions involving fish."""
        fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]

        for fish in list(fish_list):
            if fish not in self.entities_list:  # Fish may have been removed
                continue

            for other in self.entities_list:
                if other == fish:
                    continue

                if self.entities_collide(fish, other):
                    if isinstance(other, entities.Crab):
                        # Mark the predator encounter for death attribution
                        fish.mark_predator_encounter()

                        # Crab can only kill if hunt cooldown is ready
                        if other.can_hunt():
                            # Record death from predation
                            if self.ecosystem is not None:
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
                            other.eat_fish(fish)
                            self.entities_list.remove(fish)
                            break
                    elif isinstance(other, entities.Food):
                        fish.eat(other)
                    elif isinstance(other, entities.Fish):
                        # Fish-to-fish poker interaction
                        poker = PokerInteraction(fish, other)
                        if poker.play_poker():
                            # Track poker event
                            self.add_poker_event(poker)

    def handle_food_collisions(self) -> None:
        """Handle collisions involving food."""
        food_list = [e for e in self.entities_list if isinstance(e, entities.Food)]

        for food in list(food_list):
            if food not in self.entities_list:  # Food may have been eaten
                continue

            for other in self.entities_list:
                if other == food:
                    continue

                if self.entities_collide(food, other):
                    if isinstance(other, entities.Fish):
                        food.get_eaten()
                        if food in self.entities_list:
                            self.entities_list.remove(food)
                        break
                    elif isinstance(other, entities.Crab):
                        other.eat_food(food)
                        food.get_eaten()
                        if food in self.entities_list:
                            self.entities_list.remove(food)
                        break

    def handle_reproduction(self) -> None:
        """Handle fish reproduction by finding mates."""
        fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]

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

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list."""
        if poker.result is None:
            return

        result = poker.result

        # Create event message
        if result.winner_id == -1:
            # Tie
            message = f"Fish #{poker.fish1.fish_id} vs Fish #{poker.fish2.fish_id} - TIE! ({result.hand1.description})"
        else:
            winner_hand = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
            loser_hand = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1
            message = f"Fish #{result.winner_id} beats Fish #{result.loser_id} with {winner_hand.description}! (+{result.energy_transferred:.1f} energy)"

        # Create event data
        event = {
            'frame': self.frame_count,
            'winner_id': result.winner_id,
            'loser_id': result.loser_id,
            'winner_hand': (result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2).description,
            'loser_hand': (result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1).description,
            'energy_transferred': result.energy_transferred,
            'message': message
        }

        self.poker_events.append(event)

        # Keep only last 10 events
        if len(self.poker_events) > 10:
            self.poker_events.pop(0)

    def get_recent_poker_events(self, max_age_frames: int = 180) -> List[Dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        return [
            event for event in self.poker_events
            if self.frame_count - event['frame'] < max_age_frames
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation stats
        """
        if self.ecosystem is None:
            return {}

        stats = self.ecosystem.get_summary_stats()
        stats['frame_count'] = self.frame_count
        stats['time_string'] = self.time_system.get_time_string()
        stats['elapsed_real_time'] = time.time() - self.start_time
        stats['simulation_speed'] = self.frame_count / (30 * (time.time() - self.start_time)) if time.time() > self.start_time else 0

        # Add entity counts
        stats['fish_count'] = len([e for e in self.entities_list if isinstance(e, entities.Fish)])
        stats['food_count'] = len([e for e in self.entities_list if isinstance(e, entities.Food)])
        stats['plant_count'] = len([e for e in self.entities_list if isinstance(e, entities.Plant)])

        return stats

    def print_stats(self) -> None:
        """Print current simulation statistics to console."""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print(f"Frame: {stats.get('frame_count', 0)}")
        print(f"Time: {stats.get('time_string', 'N/A')}")
        print(f"Real Time: {stats.get('elapsed_real_time', 0):.1f}s")
        print(f"Simulation Speed: {stats.get('simulation_speed', 0):.2f}x")
        print("-" * 60)
        print(f"Population: {stats.get('total_population', 0)}/{self.ecosystem.max_population if self.ecosystem else 'N/A'}")
        print(f"Generation: {stats.get('current_generation', 0)}")
        print(f"Total Births: {stats.get('total_births', 0)}")
        print(f"Total Deaths: {stats.get('total_deaths', 0)}")
        print(f"Capacity: {stats.get('capacity_usage', 'N/A')}")
        print("-" * 60)
        print(f"Fish: {stats.get('fish_count', 0)}")
        print(f"Food: {stats.get('food_count', 0)}")
        print(f"Plants: {stats.get('plant_count', 0)}")

        # Death causes
        death_causes = stats.get('death_causes', {})
        if death_causes:
            print("-" * 60)
            print("Death Causes:")
            for cause, count in death_causes.items():
                print(f"  {cause}: {count}")

        print("=" * 60)

    def run_headless(self, max_frames: int = 10000, stats_interval: int = 300) -> None:
        """Run the simulation in headless mode without visualization.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames
        """
        print("=" * 60)
        print("HEADLESS FISH TANK SIMULATION")
        print("=" * 60)
        print(f"Running for {max_frames} frames ({max_frames/30:.1f} seconds of sim time)")
        print(f"Stats will be printed every {stats_interval} frames")
        print("=" * 60)

        self.setup()

        for frame in range(max_frames):
            self.update()

            # Print stats periodically
            if frame > 0 and frame % stats_interval == 0:
                self.print_stats()

        # Print final stats
        print("\n" + "=" * 60)
        print("SIMULATION COMPLETE - Final Statistics")
        print("=" * 60)
        self.print_stats()

        # Generate algorithm performance report if available
        if self.ecosystem is not None:
            print("\n" + "=" * 60)
            print("GENERATING ALGORITHM PERFORMANCE REPORT...")
            print("=" * 60)
            report = self.ecosystem.get_algorithm_performance_report()
            print(report)

            # Save to file
            with open('algorithm_performance_report.txt', 'w') as f:
                f.write(report)
            print("\nReport saved to: algorithm_performance_report.txt")
