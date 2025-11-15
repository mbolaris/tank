"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from collections import defaultdict

if TYPE_CHECKING:
    from agents import Fish


@dataclass
class GenerationStats:
    """Statistics for a generation of fish.

    Attributes:
        generation: Generation number
        population: Number of fish alive
        births: Number of births this generation
        deaths: Number of deaths this generation
        avg_age: Average age at death
        avg_speed: Average speed modifier
        avg_size: Average size modifier
        avg_energy: Average max energy
    """
    generation: int
    population: int = 0
    births: int = 0
    deaths: int = 0
    avg_age: float = 0.0
    avg_speed: float = 1.0
    avg_size: float = 1.0
    avg_energy: float = 1.0


@dataclass
class EcosystemEvent:
    """Represents an event in the ecosystem.

    Attributes:
        frame: Frame number when event occurred
        event_type: Type of event ('birth', 'death', 'starvation', 'old_age', 'predation')
        fish_id: ID of the fish involved
        details: Additional details about the event
    """
    frame: int
    event_type: str
    fish_id: int
    details: str = ""


class EcosystemManager:
    """Manages ecosystem dynamics and statistics.

    This class tracks population, generations, births, deaths, and
    provides ecosystem-level insights and constraints.

    Attributes:
        max_population: Maximum number of fish allowed (carrying capacity)
        current_generation: Current generation number
        total_births: Total fish born since start
        total_deaths: Total fish died since start
        events: Log of ecosystem events
        generation_stats: Statistics per generation
    """

    def __init__(self, max_population: int = 50):
        """Initialize the ecosystem manager.

        Args:
            max_population: Maximum number of fish (carrying capacity)
        """
        self.max_population: int = max_population
        self.current_generation: int = 0
        self.total_births: int = 0
        self.total_deaths: int = 0
        self.frame_count: int = 0

        # Event logging
        self.events: List[EcosystemEvent] = []
        self.max_events: int = 1000  # Keep last 1000 events

        # Statistics tracking
        self.generation_stats: Dict[int, GenerationStats] = {
            0: GenerationStats(generation=0)
        }

        # Death cause tracking
        self.death_causes: Dict[str, int] = defaultdict(int)

        # Next available fish ID
        self.next_fish_id: int = 0

    def update(self, frame: int) -> None:
        """Update ecosystem state.

        Args:
            frame: Current frame number
        """
        self.frame_count = frame

    def get_next_fish_id(self) -> int:
        """Get the next unique fish ID.

        Returns:
            Unique integer ID for a fish
        """
        fish_id = self.next_fish_id
        self.next_fish_id += 1
        return fish_id

    def can_reproduce(self, current_population: int) -> bool:
        """Check if reproduction is allowed based on carrying capacity.

        Args:
            current_population: Current number of fish

        Returns:
            True if population is below carrying capacity
        """
        return current_population < self.max_population

    def record_birth(self, fish_id: int, generation: int, parent_ids: Optional[List[int]] = None) -> None:
        """Record a birth event.

        Args:
            fish_id: ID of the newborn fish
            generation: Generation number
            parent_ids: Optional list of parent IDs
        """
        self.total_births += 1

        # Update generation stats
        if generation not in self.generation_stats:
            self.generation_stats[generation] = GenerationStats(generation=generation)

        self.generation_stats[generation].births += 1
        self.generation_stats[generation].population += 1

        # Update current generation
        if generation > self.current_generation:
            self.current_generation = generation

        # Log event
        details = f"Parents: {parent_ids}" if parent_ids else "Initial spawn"
        self._add_event(EcosystemEvent(
            frame=self.frame_count,
            event_type='birth',
            fish_id=fish_id,
            details=details
        ))

    def record_death(self, fish_id: int, generation: int, age: int,
                     cause: str = 'unknown', genome: Optional['genetics.Genome'] = None) -> None:
        """Record a death event.

        Args:
            fish_id: ID of the fish that died
            generation: Generation of the fish
            age: Age of the fish at death
            cause: Cause of death ('starvation', 'old_age', 'predation', 'unknown')
            genome: Optional genome for statistics
        """
        self.total_deaths += 1

        # Update generation stats
        if generation in self.generation_stats:
            stats = self.generation_stats[generation]
            stats.deaths += 1
            stats.population = max(0, stats.population - 1)

            # Update average age at death
            total_fish = stats.deaths
            stats.avg_age = (stats.avg_age * (total_fish - 1) + age) / total_fish if total_fish > 0 else age

        # Track death causes
        self.death_causes[cause] += 1

        # Log event
        self._add_event(EcosystemEvent(
            frame=self.frame_count,
            event_type=cause,
            fish_id=fish_id,
            details=f"Age: {age}, Generation: {generation}"
        ))

    def update_population_stats(self, fish_list: List['Fish']) -> None:
        """Update population statistics from current fish.

        Args:
            fish_list: List of all living fish
        """
        if not fish_list:
            return

        # Group by generation
        gen_fish: Dict[int, List['Fish']] = defaultdict(list)
        for fish in fish_list:
            if hasattr(fish, 'generation'):
                gen_fish[fish.generation].append(fish)

        # Update stats for each generation
        for generation, fishes in gen_fish.items():
            if generation not in self.generation_stats:
                self.generation_stats[generation] = GenerationStats(generation=generation)

            stats = self.generation_stats[generation]
            stats.population = len(fishes)

            # Calculate averages
            if fishes:
                stats.avg_speed = sum(f.genome.speed_modifier for f in fishes if hasattr(f, 'genome')) / len(fishes)
                stats.avg_size = sum(f.genome.size_modifier for f in fishes if hasattr(f, 'genome')) / len(fishes)
                stats.avg_energy = sum(f.genome.max_energy for f in fishes if hasattr(f, 'genome')) / len(fishes)

    def _add_event(self, event: EcosystemEvent) -> None:
        """Add an event to the log, maintaining max size.

        Args:
            event: Event to log
        """
        self.events.append(event)

        # Trim old events if we exceed max
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_recent_events(self, count: int = 10) -> List[EcosystemEvent]:
        """Get the most recent events.

        Args:
            count: Number of recent events to return

        Returns:
            List of recent events
        """
        return self.events[-count:]

    def get_population_by_generation(self) -> Dict[int, int]:
        """Get current population count by generation.

        Returns:
            Dictionary mapping generation number to population count
        """
        return {gen: stats.population for gen, stats in self.generation_stats.items() if stats.population > 0}

    def get_total_population(self) -> int:
        """Get total current population across all generations.

        Returns:
            Total number of living fish
        """
        return sum(stats.population for stats in self.generation_stats.values())

    def get_summary_stats(self) -> Dict[str, any]:
        """Get summary statistics for the ecosystem.

        Returns:
            Dictionary with key ecosystem metrics
        """
        total_pop = self.get_total_population()

        return {
            'total_population': total_pop,
            'current_generation': self.current_generation,
            'total_births': self.total_births,
            'total_deaths': self.total_deaths,
            'carrying_capacity': self.max_population,
            'capacity_usage': f"{int(100 * total_pop / self.max_population)}%" if self.max_population > 0 else "0%",
            'death_causes': dict(self.death_causes),
            'generations_alive': len([g for g, s in self.generation_stats.items() if s.population > 0]),
        }
