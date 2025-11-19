"""Pure simulation engine without visualization dependencies.

This module provides a headless simulation engine that can run the fish tank
simulation without any visualization code.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from core import entities, environment
from core.constants import (
    CRITICAL_POPULATION_THRESHOLD,
    FILES,
    FRAME_RATE,
    MAX_DIVERSITY_SPAWN_ATTEMPTS,
    MAX_POKER_EVENTS,
    MAX_POPULATION,
    POKER_EVENT_MAX_AGE_FRAMES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEPARATOR_WIDTH,
    SPAWN_MARGIN_PIXELS,
    TOTAL_ALGORITHM_COUNT,
)
from core.ecosystem import EcosystemManager
from core.entity_factory import create_initial_population
from core.fish_poker import PokerInteraction
from core.simulators.base_simulator import BaseSimulator
from core.time_system import TimeSystem

logger = logging.getLogger(__name__)


class AgentsWrapper:
    """Wrapper to provide a group-like API for managing entities."""

    def __init__(self, entities_list: List):
        self._entities = entities_list

    def add(self, *entities):
        """Add entities to the list."""
        for entity in entities:
            if entity not in self._entities:
                self._entities.append(entity)
                # Track this group in the entity for kill() method
                if hasattr(entity, "add_internal"):
                    entity.add_internal(self)

    def remove(self, *entities):
        """Remove entities from the list."""
        for entity in entities:
            if entity in self._entities:
                self._entities.remove(entity)

    def empty(self):
        """Remove all entities from the list."""
        self._entities.clear()

    def __contains__(self, entity):
        """Check if entity is in the list."""
        return entity in self._entities

    def __iter__(self):
        """Iterate over entities."""
        return iter(self._entities)

    def __len__(self):
        """Get number of entities."""
        return len(self._entities)


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
            headless: If True, run without any visualization
        """
        super().__init__()
        self.headless = headless
        self.entities_list: List[entities.Agent] = []
        self.environment: Optional[environment.Environment] = None
        self.time_system: TimeSystem = TimeSystem()
        self.start_time: float = time.time()
        self.poker_events: List[Dict[str, Any]] = []  # Recent poker events
        self._agents_wrapper: Optional[AgentsWrapper] = None

    @property
    def agents(self) -> AgentsWrapper:
        """Get agents wrapper for compatibility with tests."""
        if self._agents_wrapper is None:
            self._agents_wrapper = AgentsWrapper(self.entities_list)
        return self._agents_wrapper

    def setup(self) -> None:
        """Setup the simulation."""
        # Initialize managers
        self.environment = environment.Environment(self.entities_list, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.ecosystem = EcosystemManager(max_population=MAX_POPULATION)

        self.create_initial_entities()

    def create_initial_entities(self) -> None:
        """Create initial entities in the fish tank with multiple species."""
        if self.environment is None or self.ecosystem is None:
            return

        # Use centralized factory function for initial population
        population = create_initial_population(
            self.environment, self.ecosystem, SCREEN_WIDTH, SCREEN_HEIGHT
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
        return (
            e1.pos.x < e2.pos.x + e2.width
            and e1.pos.x + e1.width > e2.pos.x
            and e1.pos.y < e2.pos.y + e2.height
            and e1.pos.y + e1.height > e2.pos.y
        )

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle the result of a poker game by logging to events list.

        Also handles post-poker reproduction if it occurred.
        """
        self.add_poker_event(poker)

        if (
            poker.result is not None
            and poker.result.reproduction_occurred
            and poker.result.offspring is not None
        ):
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
                    fish_count = len(
                        [e for e in self.entities_list if isinstance(e, entities.Fish)]
                    )
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

            # Auto-spawn fish if population drops below critical threshold
            if len(fish_list) < CRITICAL_POPULATION_THRESHOLD:
                self.spawn_emergency_fish()

    def spawn_emergency_fish(self) -> None:
        """Spawn a new fish when population drops below critical threshold.

        This emergency spawning helps maintain genetic diversity and
        prevents population extinction.
        """
        if self.environment is None or self.ecosystem is None:
            return

        import random

        from core import movement_strategy
        from core.algorithms import get_algorithm_index
        from core.genetics import Genome

        # Get current fish to analyze diversity
        fish_list = [e for e in self.entities_list if isinstance(e, entities.Fish)]

        # If we have existing fish, try to spawn diverse genomes
        # Otherwise, spawn completely random
        if fish_list:
            # Get existing algorithms (as indices)
            existing_algorithms = set()
            existing_species = set()
            for fish in fish_list:
                if hasattr(fish, "genome") and hasattr(fish.genome, "behavior_algorithm"):
                    algo_idx = get_algorithm_index(fish.genome.behavior_algorithm)
                    if algo_idx >= 0:
                        existing_algorithms.add(algo_idx)
                if hasattr(fish, "species"):
                    existing_species.add(fish.species)

            # Create genome with an algorithm not currently in population (if possible)
            # This helps maintain diversity
            genome = Genome.random(use_algorithm=True)

            # Try to pick a different algorithm than existing ones (up to MAX_DIVERSITY_SPAWN_ATTEMPTS)
            for _ in range(MAX_DIVERSITY_SPAWN_ATTEMPTS):
                if hasattr(genome, "behavior_algorithm"):
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
            FILES["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,  # Reset generation for emergency spawns
            ecosystem=self.ecosystem,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
        )

        self.add_entity(new_fish)
        logger.info(f"Population critical! Spawned emergency fish at ({x}, {y})")

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list."""
        if poker.result is None:
            return

        result = poker.result

        # Create event message
        if result.winner_id == -1:
            # Tie
            hand1_desc = result.hand1.description if result.hand1 is not None else "Unknown"
            message = (
                f"Fish #{poker.fish1.fish_id} vs Fish #{poker.fish2.fish_id} - TIE! ({hand1_desc})"
            )
        else:
            winner_hand = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
            winner_desc = winner_hand.description if winner_hand is not None else "Unknown"
            # Show winner's actual gain (not loser's loss) to make it clear they're different
            message = f"Fish #{result.winner_id} beats Fish #{result.loser_id} with {winner_desc}! (+{result.winner_actual_gain:.1f} energy)"

        # Create event data
        winner_hand_obj = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
        loser_hand_obj = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1

        event = {
            "frame": self.frame_count,
            "winner_id": result.winner_id,
            "loser_id": result.loser_id,
            "winner_hand": (
                winner_hand_obj.description if winner_hand_obj is not None else "Unknown"
            ),
            "loser_hand": loser_hand_obj.description if loser_hand_obj is not None else "Unknown",
            "energy_transferred": result.energy_transferred,
            "message": message,
            "is_jellyfish": False,
        }

        self.poker_events.append(event)

        # Keep only last MAX_POKER_EVENTS
        if len(self.poker_events) > MAX_POKER_EVENTS:
            self.poker_events.pop(0)

    def add_jellyfish_poker_event(self, fish_id: int, fish_won: bool,
                                   fish_hand: str, jellyfish_hand: str,
                                   energy_transferred: float) -> None:
        """Add a jellyfish poker event to the recent events list.

        Args:
            fish_id: ID of the fish that played
            fish_won: Whether the fish won
            fish_hand: Description of the fish's hand
            jellyfish_hand: Description of the jellyfish's hand
            energy_transferred: Amount of energy transferred
        """
        # Create event message with jellyfish emoji indicator
        if fish_won:
            message = f"Fish #{fish_id} beats Jellyfish with {fish_hand}! (+{energy_transferred:.1f} energy)"
        else:
            message = f"Jellyfish beats Fish #{fish_id} with {jellyfish_hand}! (-{energy_transferred:.1f} energy)"

        # Create event data
        event = {
            "frame": self.frame_count,
            "winner_id": fish_id if fish_won else -2,  # -2 indicates jellyfish won
            "loser_id": -2 if fish_won else fish_id,  # -2 indicates jellyfish lost
            "winner_hand": fish_hand if fish_won else jellyfish_hand,
            "loser_hand": jellyfish_hand if fish_won else fish_hand,
            "energy_transferred": energy_transferred,
            "message": message,
            "is_jellyfish": True,
        }

        self.poker_events.append(event)

        # Keep only last MAX_POKER_EVENTS
        if len(self.poker_events) > MAX_POKER_EVENTS:
            self.poker_events.pop(0)

    def get_recent_poker_events(
        self, max_age_frames: int = POKER_EVENT_MAX_AGE_FRAMES
    ) -> List[Dict[str, Any]]:
        """Get recent poker events (within max_age_frames)."""
        return [
            event
            for event in self.poker_events
            if self.frame_count - event["frame"] < max_age_frames
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation stats
        """
        if self.ecosystem is None:
            return {}

        stats = self.ecosystem.get_summary_stats(self.get_all_entities())
        stats["frame_count"] = self.frame_count
        stats["time_string"] = self.time_system.get_time_string()
        stats["elapsed_real_time"] = time.time() - self.start_time
        stats["simulation_speed"] = (
            self.frame_count / (FRAME_RATE * (time.time() - self.start_time))
            if time.time() > self.start_time
            else 0
        )

        # Add entity counts
        stats["fish_count"] = len([e for e in self.entities_list if isinstance(e, entities.Fish)])
        stats["food_count"] = len([e for e in self.entities_list if isinstance(e, entities.Food)])
        stats["plant_count"] = len([e for e in self.entities_list if isinstance(e, entities.Plant)])

        return stats

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive simulation statistics to JSON file for LLM analysis.

        This export is designed to be consumed by LLMs to:
        - Analyze which behavior algorithms are successful/unsuccessful
        - Identify patterns in survival, reproduction, and energy efficiency
        - Generate insights for creating new/improved algorithms
        - Track evolution of parameters over generations

        Args:
            filename: Output JSON file path
        """
        if self.ecosystem is None:
            logger.warning("Cannot export stats: ecosystem not initialized")
            return

        import json

        from core.algorithms import get_algorithm_name
        from core.registry import get_algorithm_metadata

        # Get algorithm source mapping for AI agent
        algorithm_metadata = get_algorithm_metadata()

        # Gather comprehensive stats
        export_data = {
            "simulation_metadata": {
                "total_frames": self.frame_count,
                "total_sim_time_seconds": self.frame_count / FRAME_RATE,
                "elapsed_real_time_seconds": time.time() - self.start_time,
                "simulation_speed_multiplier": (
                    self.frame_count / (FRAME_RATE * (time.time() - self.start_time))
                    if time.time() > self.start_time
                    else 0
                ),
                "max_population": self.ecosystem.max_population,
            },
            "population_summary": {
                "total_births": self.ecosystem.total_births,
                "total_deaths": self.ecosystem.total_deaths,
                "current_generation": self.ecosystem.current_generation,
                "final_population": len(
                    [e for e in self.entities_list if isinstance(e, entities.Fish)]
                ),
            },
            "death_causes": dict(self.ecosystem.death_causes),
            "algorithm_registry": algorithm_metadata,
            "algorithm_performance": {},
            "poker_statistics": {},
            "generation_trends": [],
            "recommendations": {
                "top_performers": [],
                "worst_performers": [],
                "extinct_algorithms": [],
            },
        }

        # Export per-algorithm performance stats
        for algo_id, stats in self.ecosystem.algorithm_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            # Get source file info from registry
            metadata = algorithm_metadata.get(algo_name, {})
            source_file = metadata.get("source_file", "unknown")
            category = metadata.get("category", "unknown")

            export_data["algorithm_performance"][algo_name] = {
                "algorithm_id": algo_id,
                "source_file": source_file,
                "category": category,
                "total_births": stats.total_births,
                "total_deaths": stats.total_deaths,
                "current_population": stats.current_population,
                "avg_lifespan_frames": stats.get_avg_lifespan(),
                "survival_rate": stats.get_survival_rate(),
                "reproduction_rate": stats.get_reproduction_rate(),
                "total_reproductions": stats.total_reproductions,
                "total_food_eaten": stats.total_food_eaten,
                "death_breakdown": {
                    "starvation": stats.deaths_starvation,
                    "old_age": stats.deaths_old_age,
                    "predation": stats.deaths_predation,
                },
                # Performance metrics for LLM analysis
                "energy_efficiency": (
                    stats.total_food_eaten / stats.total_births if stats.total_births > 0 else 0.0
                ),
                "reproductive_success": (
                    stats.total_reproductions / stats.total_deaths
                    if stats.total_deaths > 0
                    else 0.0
                ),
            }

        # Export poker statistics per algorithm
        for algo_id, poker_stats in self.ecosystem.poker_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            if poker_stats.total_games > 0:
                export_data["poker_statistics"][algo_name] = {
                    "algorithm_id": algo_id,
                    "total_games": poker_stats.total_games,
                    "win_rate": poker_stats.get_win_rate(),
                    "fold_rate": poker_stats.get_fold_rate(),
                    "net_energy": poker_stats.get_net_energy(),
                    "roi": poker_stats.get_roi(),
                    "vpip": poker_stats.get_vpip(),
                    "aggression_factor": poker_stats.get_aggression_factor(),
                    "showdown_win_rate": poker_stats.get_showdown_win_rate(),
                    "bluff_success_rate": poker_stats.get_bluff_success_rate(),
                    "positional_advantage": poker_stats.get_positional_advantage(),
                }

        # Export generation trends
        for gen_num, gen_stats in sorted(self.ecosystem.generation_stats.items()):
            export_data["generation_trends"].append(
                {
                    "generation": gen_num,
                    "population": gen_stats.population,
                    "births": gen_stats.births,
                    "deaths": gen_stats.deaths,
                    "avg_age": gen_stats.avg_age,
                    "avg_speed": gen_stats.avg_speed,
                    "avg_size": gen_stats.avg_size,
                    "avg_energy": gen_stats.avg_energy,
                }
            )

        # Identify top performers (for LLM to learn from)
        algorithms_with_data = [
            (algo_id, stats)
            for algo_id, stats in self.ecosystem.algorithm_stats.items()
            if stats.total_births >= 5  # Minimum sample size
        ]

        # Sort by reproductive success
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate(), reverse=True)

        for algo_id, stats in algorithms_with_data[:5]:  # Top 5
            algo_name = get_algorithm_name(algo_id)
            export_data["recommendations"]["top_performers"].append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "survival_rate": stats.get_survival_rate(),
                    "reason": f"High reproduction rate ({stats.get_reproduction_rate():.2%}) and survival",
                }
            )

        # Identify worst performers (for LLM to learn what to avoid)
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate())
        for algo_id, stats in algorithms_with_data[:5]:  # Bottom 5
            algo_name = get_algorithm_name(algo_id)
            main_death_cause = "unknown"
            if (
                stats.deaths_starvation > stats.deaths_old_age
                and stats.deaths_starvation > stats.deaths_predation
            ):
                main_death_cause = "starvation"
            elif stats.deaths_old_age > stats.deaths_predation:
                main_death_cause = "old_age"
            elif stats.deaths_predation > 0:
                main_death_cause = "predation"

            export_data["recommendations"]["worst_performers"].append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "main_death_cause": main_death_cause,
                    "reason": f"Low reproduction rate ({stats.get_reproduction_rate():.2%}), main death: {main_death_cause}",
                }
            )

        # Identify extinct algorithms
        for algo_id, stats in self.ecosystem.algorithm_stats.items():
            if stats.total_births > 0 and stats.current_population == 0:
                algo_name = get_algorithm_name(algo_id)
                export_data["recommendations"]["extinct_algorithms"].append(
                    {
                        "algorithm_name": algo_name,
                        "algorithm_id": algo_id,
                        "total_births": stats.total_births,
                        "avg_lifespan": stats.get_avg_lifespan(),
                    }
                )

        # Write to file
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Comprehensive stats exported to: {filename}")
        logger.info(f"Export includes {len(export_data['algorithm_performance'])} algorithms")
        logger.info("Use this data for LLM-based behavior analysis and improvement!")

    def print_stats(self) -> None:
        """Print current simulation statistics to console."""
        stats = self.get_stats()

        logger.info("")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info(f"Frame: {stats.get('frame_count', 0)}")
        logger.info(f"Time: {stats.get('time_string', 'N/A')}")
        logger.info(f"Real Time: {stats.get('elapsed_real_time', 0):.1f}s")
        logger.info(f"Simulation Speed: {stats.get('simulation_speed', 0):.2f}x")
        logger.info("-" * SEPARATOR_WIDTH)
        logger.info(
            f"Population: {stats.get('total_population', 0)}/{self.ecosystem.max_population if self.ecosystem else 'N/A'}"
        )
        logger.info(f"Generation: {stats.get('current_generation', 0)}")
        logger.info(f"Total Births: {stats.get('total_births', 0)}")
        logger.info(f"Total Deaths: {stats.get('total_deaths', 0)}")
        logger.info(f"Capacity: {stats.get('capacity_usage', 'N/A')}")
        logger.info("-" * SEPARATOR_WIDTH)
        logger.info(f"Fish: {stats.get('fish_count', 0)}")
        logger.info(f"Food: {stats.get('food_count', 0)}")
        logger.info(f"Plants: {stats.get('plant_count', 0)}")

        # Death causes
        death_causes = stats.get("death_causes", {})
        if death_causes:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Death Causes:")
            for cause, count in death_causes.items():
                logger.info(f"  {cause}: {count}")

        # Reproduction stats
        repro_stats = stats.get("reproduction_stats", {})
        if repro_stats:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Reproduction Stats:")
            logger.info(f"  Total Reproductions: {repro_stats.get('total_reproductions', 0)}")
            logger.info(f"  Mating Attempts: {repro_stats.get('total_mating_attempts', 0)}")
            logger.info(f"  Failed Attempts: {repro_stats.get('total_failed_attempts', 0)}")
            logger.info(f"  Success Rate: {repro_stats.get('success_rate_pct', 'N/A')}")
            logger.info(f"  Currently Pregnant: {repro_stats.get('current_pregnant_fish', 0)}")
            logger.info(f"  Total Offspring: {repro_stats.get('total_offspring', 0)}")

        # Genetic diversity stats
        diversity_stats = stats.get("diversity_stats", {})
        if diversity_stats:
            logger.info("-" * SEPARATOR_WIDTH)
            logger.info("Genetic Diversity:")
            logger.info(
                f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/{TOTAL_ALGORITHM_COUNT}"
            )
            logger.info(f"  Unique Species: {diversity_stats.get('unique_species', 0)}/4")
            logger.info(f"  Diversity Score: {diversity_stats.get('diversity_score_pct', 'N/A')}")
            logger.info(f"  Color Variance: {diversity_stats.get('color_variance', 0):.4f}")
            logger.info(f"  Speed Variance: {diversity_stats.get('speed_variance', 0):.4f}")
            logger.info(f"  Size Variance: {diversity_stats.get('size_variance', 0):.4f}")
            logger.info(f"  Vision Variance: {diversity_stats.get('vision_variance', 0):.4f}")

        logger.info("=" * SEPARATOR_WIDTH)

    def run_headless(
        self,
        max_frames: int = 10000,
        stats_interval: int = 300,
        export_json: Optional[str] = None,
    ) -> None:
        """Run the simulation in headless mode without visualization.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames
            export_json: Optional filename to export JSON stats for LLM analysis
        """
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("HEADLESS FISH TANK SIMULATION")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info(
            f"Running for {max_frames} frames ({max_frames / FRAME_RATE:.1f} seconds of sim time)"
        )
        logger.info(f"Stats will be printed every {stats_interval} frames")
        if export_json:
            logger.info(f"Stats will be exported to: {export_json}")
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
            logger.info(f"{report}")

            # Save to file
            with open("algorithm_performance_report.txt", "w") as f:
                f.write(report)
            logger.info("")
            logger.info("Report saved to: algorithm_performance_report.txt")

            # Export JSON stats if requested
            if export_json:
                logger.info("")
                logger.info("=" * SEPARATOR_WIDTH)
                logger.info("EXPORTING JSON STATISTICS FOR LLM ANALYSIS...")
                logger.info("=" * SEPARATOR_WIDTH)
                self.export_stats_json(export_json)


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
