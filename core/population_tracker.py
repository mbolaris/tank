"""Population tracking for the ecosystem.

This module tracks fish population dynamics: births, deaths, generations,
and death causes. It consolidates state and logic that was previously
split between EcosystemManager and ecosystem_population module.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from core.config.ecosystem import MAX_ECOSYSTEM_EVENTS, TOTAL_ALGORITHM_COUNT
from core.ecosystem_stats import (
    AlgorithmStats,
    EcosystemEvent,
    GenerationStats,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome

logger = logging.getLogger(__name__)


class PopulationTracker:
    """Tracks population dynamics: births, deaths, generations.

    This class owns all population-related state and provides methods
    for recording births/deaths and querying population statistics.

    Attributes:
        max_population: Maximum number of fish allowed (carrying capacity)
        current_generation: Highest generation number seen
        total_births: Total fish born since start
        total_deaths: Total fish died since start
    """

    def __init__(
        self,
        max_population: int = 75,
        add_event_callback: Optional[Callable[[EcosystemEvent], None]] = None,
        frame_provider: Optional[Callable[[], int]] = None,
    ):
        """Initialize the population tracker.

        Args:
            max_population: Maximum number of fish (carrying capacity)
            add_event_callback: Callback to add events to the ecosystem log
            frame_provider: Callback to get the current frame number
        """
        self.max_population = max_population
        self.current_generation: int = 0
        self.total_births: int = 0
        self.total_deaths: int = 0

        # Callbacks for integration with EcosystemManager
        self._add_event = add_event_callback or (lambda e: None)
        self._get_frame = frame_provider or (lambda: 0)

        # Generation statistics
        self.generation_stats: Dict[int, GenerationStats] = {
            0: GenerationStats(generation=0)
        }

        # Death cause tracking
        self.death_causes: Dict[str, int] = defaultdict(int)

        # Algorithm performance tracking
        self.algorithm_stats: Dict[int, AlgorithmStats] = {}
        self._init_algorithm_stats()

        # Extinction tracking
        self.total_extinctions: int = 0
        self._last_max_generation: int = 0

        # Fish ID generation
        self.next_fish_id: int = 0

    def _init_algorithm_stats(self) -> None:
        """Initialize algorithm stats for all algorithms."""
        try:
            from core.algorithms.registry import ALL_ALGORITHMS

            for i, algo_class in enumerate(ALL_ALGORITHMS):
                algo_name = algo_class.__name__
                self.algorithm_stats[i] = AlgorithmStats(
                    algorithm_id=i, algorithm_name=algo_name
                )
        except ImportError:
            for i in range(TOTAL_ALGORITHM_COUNT):
                self.algorithm_stats[i] = AlgorithmStats(
                    algorithm_id=i, algorithm_name=f"Algorithm_{i}"
                )

    def generate_new_fish_id(self) -> int:
        """Generate a new unique fish ID.

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

    def record_birth(
        self,
        fish_id: int,
        generation: int,
        parent_ids: Optional[List[int]] = None,
        algorithm_id: Optional[int] = None,
        color: Optional[str] = None,
        lineage_log: Optional[List[Dict[str, Any]]] = None,
        enhanced_stats: Optional[Any] = None,
    ) -> None:
        """Record a fish birth.

        Args:
            fish_id: ID of the new fish
            generation: Generation number of the new fish
            parent_ids: IDs of parent fish (if any)
            algorithm_id: Algorithm ID of the fish
            color: Color hex string for visualization
            lineage_log: List to append lineage record to
            enhanced_stats: EnhancedStatisticsTracker for additional recording
        """
        self.total_births += 1

        if generation not in self.generation_stats:
            self.generation_stats[generation] = GenerationStats(generation=generation)

        self.generation_stats[generation].births += 1
        self.generation_stats[generation].population += 1

        if generation > self.current_generation:
            self.current_generation = generation

        if algorithm_id is not None and algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_births += 1
            self.algorithm_stats[algorithm_id].current_population += 1

        if enhanced_stats is not None:
            enhanced_stats.record_offspring_birth(energy_cost=0.0)

        # Build lineage record
        parent_id = parent_ids[0] if parent_ids else None
        algorithm_name = "Unknown"
        if algorithm_id is not None and algorithm_id in self.algorithm_stats:
            algorithm_name = self.algorithm_stats[algorithm_id].algorithm_name

        if lineage_log is not None:
            lineage_record = {
                "id": str(fish_id),
                "parent_id": str(parent_id) if parent_id is not None else "root",
                "generation": generation,
                "algorithm": algorithm_name,
                "color": color if color else "#00ff00",
                "birth_time": self._get_frame(),
            }
            lineage_log.append(lineage_record)

            # Cap lineage log size
            MAX_LINEAGE_LOG_SIZE = 5000
            if len(lineage_log) > MAX_LINEAGE_LOG_SIZE:
                lineage_log.pop(0)

        # Log event
        details = f"Parents: {parent_ids}" if parent_ids else "Initial spawn"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(
            EcosystemEvent(
                frame=self._get_frame(),
                event_type="birth",
                fish_id=fish_id,
                details=details,
            )
        )

    def record_death(
        self,
        fish_id: int,
        generation: int,
        age: int,
        cause: str = "unknown",
        genome: Optional["Genome"] = None,
        algorithm_id: Optional[int] = None,
        remaining_energy: float = 0.0,
        enhanced_stats: Optional[Any] = None,
        record_energy_burn: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """Record a fish death.

        Args:
            fish_id: ID of the deceased fish
            generation: Generation number of the fish
            age: Age of the fish at death
            cause: Cause of death
            genome: Fish's genome (for tracking)
            algorithm_id: Algorithm ID of the fish
            remaining_energy: Energy remaining at death
            enhanced_stats: EnhancedStatisticsTracker for additional recording
            record_energy_burn: Callback to record energy burn
        """
        self.total_deaths += 1

        if generation in self.generation_stats:
            stats = self.generation_stats[generation]
            stats.deaths += 1
            stats.population = max(0, stats.population - 1)

            total_fish = stats.deaths
            if total_fish > 0:
                stats.avg_age = (stats.avg_age * (total_fish - 1) + age) / total_fish
            else:
                stats.avg_age = age

        self.death_causes[cause] += 1

        if algorithm_id is not None and algorithm_id in self.algorithm_stats:
            algo_stats = self.algorithm_stats[algorithm_id]
            algo_stats.total_deaths += 1
            algo_stats.current_population = max(0, algo_stats.current_population - 1)
            algo_stats.total_lifespan += age

            if cause == "starvation":
                algo_stats.deaths_starvation += 1
            elif cause == "old_age":
                algo_stats.deaths_old_age += 1
            elif cause == "predation":
                algo_stats.deaths_predation += 1

        if enhanced_stats is not None:
            enhanced_stats.record_death_energy_loss(remaining_energy)

        if record_energy_burn is not None:
            record_energy_burn(f"death_{cause}", remaining_energy)

        # Log event
        details = f"Age: {age}, Generation: {generation}"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(
            EcosystemEvent(
                frame=self._get_frame(),
                event_type=cause,
                fish_id=fish_id,
                details=details,
            )
        )

    def update_population_stats(
        self,
        fish_list: List["Fish"],
        enhanced_stats: Optional[Any] = None,
    ) -> None:
        """Update population statistics from current fish list.

        Args:
            fish_list: List of all living fish
            enhanced_stats: EnhancedStatisticsTracker for snapshots
        """
        if not fish_list:
            return

        gen_fish: Dict[int, List["Fish"]] = defaultdict(list)
        for fish in fish_list:
            if hasattr(fish, "generation"):
                gen_fish[fish.generation].append(fish)

        for generation, fishes in gen_fish.items():
            if generation not in self.generation_stats:
                self.generation_stats[generation] = GenerationStats(generation=generation)

            stats = self.generation_stats[generation]
            stats.population = len(fishes)

            fishes_with_genome = [f for f in fishes if hasattr(f, "genome")]
            if fishes_with_genome:
                stats.avg_speed = sum(
                    f.genome.speed_modifier for f in fishes_with_genome
                ) / len(fishes)
                stats.avg_size = sum(
                    f.genome.physical.size_modifier.value for f in fishes_with_genome
                ) / len(fishes)
                stats.avg_energy = stats.avg_size  # Max energy is based on size

        # Record snapshots periodically
        if enhanced_stats is not None and self._get_frame() % 10 == 0:
            enhanced_stats.record_frame_snapshot(
                frame=self._get_frame(),
                fish_list=fish_list,
                births_this_frame=0,
                deaths_this_frame=0,
            )

    def check_for_extinction(self, frame: int) -> None:
        """Check if population has gone extinct.

        Args:
            frame: Current frame number
        """
        alive_generations = [
            g for g, s in self.generation_stats.items() if s.population > 0
        ]
        current_max_gen = max(alive_generations) if alive_generations else 0

        if self._last_max_generation > 0 and current_max_gen == 0:
            self.total_extinctions += 1
            logger.info(
                f"Population extinction #{self.total_extinctions} detected at frame {frame}"
            )

        self._last_max_generation = current_max_gen

    def get_population_by_generation(self) -> Dict[int, int]:
        """Get current population counts by generation.

        Returns:
            Dictionary mapping generation number to population count
        """
        return {
            gen: stats.population
            for gen, stats in self.generation_stats.items()
            if stats.population > 0
        }

    def get_total_population(self) -> int:
        """Get total population across all generations.

        Returns:
            Total number of living fish
        """
        return sum(stats.population for stats in self.generation_stats.values())
