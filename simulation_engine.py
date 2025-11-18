"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without pygame or any visualization code.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FILES, FRAME_RATE,
    MAX_DIVERSITY_SPAWN_ATTEMPTS, SPAWN_MARGIN_PIXELS,
    MAX_POKER_EVENTS, POKER_EVENT_MAX_AGE_FRAMES,
    SEPARATOR_WIDTH, TOTAL_ALGORITHM_COUNT
)
from core import environment, entities
from core.ecosystem import EcosystemManager
from core.time_system import TimeSystem
from core.fish_poker import PokerInteraction
from core.entity_factory import create_initial_population
from core.simulators.base_simulator import BaseSimulator

logger = logging.getLogger(__name__)


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
        """Handle the result of a poker game by logging to events list.

        Also handles post-poker reproduction if it occurred.
        """
        self.add_poker_event(poker)

        if poker.result is not None and poker.result.reproduction_occurred and poker.result.offspring is not None:
            offspring = poker.result.offspring
            self.add_entity(offspring)
            # Note: Birth is automatically recorded by Fish.__init__ when ecosystem is provided

    def update(self) -> None:
        """Update the state of the simulation."""
        if self.paused:
            return

        self.frame_count += 1

        self.time_system.update()
        time_modifier = self.time_system.get_activity_modifier()

        new_entities: List[entities.Agent] = []

        for entity in list(self.entities_list):
            if isinstance(entity, entities.Fish):
                newborn = entity.update(self.frame_count, time_modifier)
                if newborn is not None and self.ecosystem is not None:
                    fish_count = len([e for e in self.entities_list if isinstance(e, entities.Fish)])
                    if self.ecosystem.can_reproduce(fish_count):
                        new_entities.append(newborn)

                if entity.is_dead():
                    self.record_fish_death(entity)

            elif isinstance(entity, entities.Plant):
                food = entity.update(self.frame_count, time_modifier)
                if food is not None:
                    new_entities.append(food)

            elif isinstance(entity, entities.Jellyfish):
                entity.update(self.frame_count)
                # Remove dead jellyfish
                if entity.is_dead():
                    self.remove_entity(entity)
                    logger.info(f"Jellyfish #{entity.jellyfish_id} died at age {entity.age}")

            else:
                entity.update(self.frame_count)

            self.keep_entity_on_screen(entity)

            if isinstance(entity, entities.Food) and entity.pos.y >= SCREEN_HEIGHT - entity.height:
                self.remove_entity(entity)

        for new_entity in new_entities:
            self.add_entity(new_entity)

        if self.environment is not None:
            self.spawn_auto_food(self.environment)

        self.update_spatial_grid()

        # Uses spatial grid for efficiency
        self.handle_collisions()

        # Mate finding
        self.handle_reproduction()

        if self.ecosystem is not None:
            fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]
            self.ecosystem.update_population_stats(fish_list)
            self.ecosystem.update(self.frame_count)

            # Auto-spawn fish if population drops below 3
            if len(fish_list) < 3:
                self.spawn_emergency_fish()

    def spawn_emergency_fish(self) -> None:
        """Spawn a new fish when population drops below critical threshold.

        This emergency spawning helps maintain genetic diversity and
        prevents population extinction.
        """
        if self.environment is None or self.ecosystem is None:
            return

        import random
        from core.genetics import Genome
        from core import movement_strategy
        from core.algorithms import get_algorithm_index

        # Get current fish to analyze diversity
        fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]

        # If we have existing fish, try to spawn diverse genomes
        # Otherwise, spawn completely random
        if fish_list:
            # Get existing algorithms (as indices)
            existing_algorithms = set()
            existing_species = set()
            for fish in fish_list:
                if hasattr(fish, 'genome') and hasattr(fish.genome, 'behavior_algorithm'):
                    algo_idx = get_algorithm_index(fish.genome.behavior_algorithm)
                    if algo_idx >= 0:
                        existing_algorithms.add(algo_idx)
                if hasattr(fish, 'species'):
                    existing_species.add(fish.species)

            # Create genome with an algorithm not currently in population (if possible)
            # This helps maintain diversity
            genome = Genome.random(use_algorithm=True)

            # Try to pick a different algorithm than existing ones (up to MAX_DIVERSITY_SPAWN_ATTEMPTS)
            for _ in range(MAX_DIVERSITY_SPAWN_ATTEMPTS):
                if hasattr(genome, 'behavior_algorithm'):
                    algo_idx = get_algorithm_index(genome.behavior_algorithm)
                    if algo_idx >= 0 and algo_idx not in existing_algorithms:
                        break
                genome = Genome.random(use_algorithm=True)
        else:
            # No existing fish, spawn completely random
            genome = Genome.random(use_algorithm=True)

        # Random spawn position (avoid edges)
        x = random.randint(SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS)
        y = random.randint(SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS)

        # Create the new fish
        new_fish = entities.Fish(
            self.environment,
            movement_strategy.AlgorithmicMovement(),
            FILES['schooling_fish'][0],
            x, y,
            4,
            genome=genome,
            generation=0,  # Reset generation for emergency spawns
            ecosystem=self.ecosystem,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT
        )

        self.add_entity(new_fish)
        logger.info("Population critical! Spawned emergency fish at (%d, %d)", x, y)

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

        # Keep only last MAX_POKER_EVENTS
        if len(self.poker_events) > MAX_POKER_EVENTS:
            self.poker_events.pop(0)

    def get_recent_poker_events(self, max_age_frames: int = POKER_EVENT_MAX_AGE_FRAMES) -> List[Dict[str, Any]]:
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
        stats['simulation_speed'] = self.frame_count / (FRAME_RATE * (time.time() - self.start_time)) if time.time() > self.start_time else 0

        # Add entity counts
        stats['fish_count'] = len([e for e in self.entities_list if isinstance(e, entities.Fish)])
        stats['food_count'] = len([e for e in self.entities_list if isinstance(e, entities.Food)])
        stats['plant_count'] = len([e for e in self.entities_list if isinstance(e, entities.Plant)])

        return stats

    def print_stats(self) -> None:
        """Print current simulation statistics to console."""
        stats = self.get_stats()

        logger.info("")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("Frame: %d", stats.get('frame_count', 0))
        logger.info("Time: %s", stats.get('time_string', 'N/A'))
        logger.info("Real Time: %.1fs", stats.get('elapsed_real_time', 0))
        logger.info("Simulation Speed: %.2fx", stats.get('simulation_speed', 0))
        logger.info("-" * SEPARATOR_WIDTH)
        logger.info("Population: %d/%s", stats.get('total_population', 0), self.ecosystem.max_population if self.ecosystem else 'N/A')
        logger.info("Generation: %d", stats.get('current_generation', 0))
        logger.info("Total Births: %d", stats.get('total_births', 0))
        logger.info("Total Deaths: %d", stats.get('total_deaths', 0))
        logger.info("Capacity: %s", stats.get('capacity_usage', 'N/A'))
        logger.info("-" * SEPARATOR_WIDTH)
        logger.info("Fish: %d", stats.get('fish_count', 0))
        logger.info("Food: %d", stats.get('food_count', 0))
        logger.info("Plants: %d", stats.get('plant_count', 0))

        # Death causes
        death_causes = stats.get('death_causes', {})
        if death_causes:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Death Causes:")
            for cause, count in death_causes.items():
                logger.info("  %s: %d", cause, count)

        # Reproduction stats
        repro_stats = stats.get('reproduction_stats', {})
        if repro_stats:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Reproduction Stats:")
            logger.info("  Total Reproductions: %d", repro_stats.get('total_reproductions', 0))
            logger.info("  Mating Attempts: %d", repro_stats.get('total_mating_attempts', 0))
            logger.info("  Failed Attempts: %d", repro_stats.get('total_failed_attempts', 0))
            logger.info("  Success Rate: %s", repro_stats.get('success_rate_pct', 'N/A'))
            logger.info("  Currently Pregnant: %d", repro_stats.get('current_pregnant_fish', 0))
            logger.info("  Total Offspring: %d", repro_stats.get('total_offspring', 0))

        # Genetic diversity stats
        diversity_stats = stats.get('diversity_stats', {})
        if diversity_stats:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Genetic Diversity:")
            logger.info("  Unique Algorithms: %d/%d", diversity_stats.get('unique_algorithms', 0), TOTAL_ALGORITHM_COUNT)
            logger.info("  Unique Species: %d/4", diversity_stats.get('unique_species', 0))
            logger.info("  Diversity Score: %s", diversity_stats.get('diversity_score_pct', 'N/A'))
            logger.info("  Color Variance: %.4f", diversity_stats.get('color_variance', 0))
            logger.info("  Speed Variance: %.4f", diversity_stats.get('speed_variance', 0))
            logger.info("  Size Variance: %.4f", diversity_stats.get('size_variance', 0))
            logger.info("  Vision Variance: %.4f", diversity_stats.get('vision_variance', 0))

        logger.info("=" * SEPARATOR_WIDTH)

    def run_headless(self, max_frames: int = 10000, stats_interval: int = 300) -> None:
        """Run the simulation in headless mode without visualization.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames
        """
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("HEADLESS FISH TANK SIMULATION")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("Running for %d frames (%.1f seconds of sim time)", max_frames, max_frames / FRAME_RATE)
        logger.info("Stats will be printed every %d frames", stats_interval)
        logger.info("=" * SEPARATOR_WIDTH)

        self.setup()

        for frame in range(max_frames):
            self.update()

            # Print stats periodically
            if frame > 0 and frame % stats_interval == 0:
                self.print_stats()

        # Print final stats
        logger.info("")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("SIMULATION COMPLETE - Final Statistics")
        logger.info("=" * SEPARATOR_WIDTH)
        self.print_stats()

        # Generate algorithm performance report if available
        if self.ecosystem is not None:
            logger.info("")
            logger.info("=" * SEPARATOR_WIDTH)
            logger.info("GENERATING ALGORITHM PERFORMANCE REPORT...")
            logger.info("=" * SEPARATOR_WIDTH)
            report = self.ecosystem.get_algorithm_performance_report()
            logger.info("%s", report)

            # Save to file
            with open('algorithm_performance_report.txt', 'w') as f:
                f.write(report)
            logger.info("")
            logger.info("Report saved to: algorithm_performance_report.txt")


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
