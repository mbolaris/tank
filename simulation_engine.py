"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without pygame or any visualization code.
"""

import time
from typing import List, Optional, Dict, Any
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core import environment, entities
from core.ecosystem import EcosystemManager
from core.time_system import TimeSystem
from core.fish_poker import PokerInteraction
from core.entity_factory import create_initial_population
from core.simulators.base_simulator import BaseSimulator


class SimulationEngine(BaseSimulator):
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
        super().__init__()
        self.headless = headless
        self.entities_list: List[entities.Agent] = []
        self.environment: Optional[environment.Environment] = None
        self.time_system: TimeSystem = TimeSystem()
        self.start_time: float = time.time()
        self.poker_events: List[Dict[str, Any]] = []  # Recent poker events

    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize managers
        self.environment = environment.Environment(self.entities_list, SCREEN_WIDTH, SCREEN_HEIGHT)
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

    # Implement abstract methods from BaseSimulator
    def get_all_entities(self) -> List[entities.Agent]:
        """Get all entities in the simulation."""
        return self.entities_list

    def add_entity(self, entity: entities.Agent) -> None:
        """Add an entity to the simulation."""
        self.entities_list.append(entity)

    def remove_entity(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation."""
        if entity in self.entities_list:
            self.entities_list.remove(entity)

    def check_collision(self, e1: entities.Agent, e2: entities.Agent) -> bool:
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

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle the result of a poker game by logging to events list."""
        self.add_poker_event(poker)

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
                    self.record_fish_death(entity)

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
                self.remove_entity(entity)

        # Add new entities
        for new_entity in new_entities:
            self.add_entity(new_entity)

        # Automatic food spawning
        if self.environment is not None:
            self.spawn_auto_food(self.environment)

        # Update spatial grid after all entity movements
        self.update_spatial_grid()

        # Handle collisions (uses spatial grid for efficiency)
        self.handle_collisions()

        # Handle reproduction (mate finding)
        self.handle_reproduction()

        # Update ecosystem stats
        if self.ecosystem is not None:
            fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]
            self.ecosystem.update_population_stats(fish_list)
            self.ecosystem.update(self.frame_count)


    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list."""
        if poker.result is None:
            return

        result = poker.result

        # Create event message
        if result.winner_id == -1:
            # Tie
            hand1_desc = result.hand1.description if result.hand1 is not None else "Unknown"
            message = f"Fish #{poker.fish1.fish_id} vs Fish #{poker.fish2.fish_id} - TIE! ({hand1_desc})"
        else:
            winner_hand = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
            loser_hand = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1
            winner_desc = winner_hand.description if winner_hand is not None else "Unknown"
            message = f"Fish #{result.winner_id} beats Fish #{result.loser_id} with {winner_desc}! (+{result.energy_transferred:.1f} energy)"

        # Create event data
        winner_hand_obj = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
        loser_hand_obj = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1

        event = {
            'frame': self.frame_count,
            'winner_id': result.winner_id,
            'loser_id': result.loser_id,
            'winner_hand': winner_hand_obj.description if winner_hand_obj is not None else "Unknown",
            'loser_hand': loser_hand_obj.description if loser_hand_obj is not None else "Unknown",
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

        stats = self.ecosystem.get_summary_stats(self.get_all_entities())
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


class HeadlessSimulator(SimulationEngine):
    """Wrapper class for CI/testing with simplified interface.

    This class provides a simpler interface for headless testing,
    accepting max_frames in the constructor and providing a simple run() method.
    """

    def __init__(self, max_frames: int = 100, stats_interval: int = 0) -> None:
        """Initialize the headless simulator.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames (0 = no stats during run)
        """
        super().__init__(headless=True)
        self.max_frames = max_frames
        self.stats_interval = stats_interval if stats_interval > 0 else max_frames + 1

    def run(self) -> None:
        """Run the simulation for the configured number of frames."""
        self.run_headless(max_frames=self.max_frames, stats_interval=self.stats_interval)
