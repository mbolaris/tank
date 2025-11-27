"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from core.constants import MAX_ECOSYSTEM_EVENTS, TOTAL_ALGORITHM_COUNT
from core.ecosystem_stats import (
    AlgorithmStats,
    EcosystemEvent,
    GenerationStats,
    GeneticDiversityStats,
    PokerStats,
)
from core.poker_stats_manager import PokerStatsManager
from core.reproduction_stats_manager import ReproductionStatsManager

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome


logger = logging.getLogger(__name__)


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

    def __init__(self, max_population: int = 75):
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
        self.max_events: int = MAX_ECOSYSTEM_EVENTS

        # Statistics tracking
        self.generation_stats: Dict[int, GenerationStats] = {0: GenerationStats(generation=0)}

        # Death cause tracking
        self.death_causes: Dict[str, int] = defaultdict(int)

        # Algorithm performance tracking
        self.algorithm_stats: Dict[int, AlgorithmStats] = {}
        self._init_algorithm_stats()

        # Poker statistics tracking
        self.poker_manager = PokerStatsManager(
            add_event=self._add_event, frame_provider=lambda: self.frame_count
        )
        self.poker_stats: Dict[int, PokerStats] = self.poker_manager.poker_stats

        # Reproduction statistics tracking
        self.reproduction_manager = ReproductionStatsManager(self.algorithm_stats)

        # Genetic diversity statistics tracking
        self.genetic_diversity_stats: GeneticDiversityStats = GeneticDiversityStats()

        # NEW: Enhanced statistics tracker (time series, correlations, extinctions, etc.)
        from core.enhanced_statistics import EnhancedStatisticsTracker

        self.enhanced_stats: EnhancedStatisticsTracker = EnhancedStatisticsTracker(
            max_history_length=1000
        )

        # NEW: Lineage tracking for phylogenetic tree
        # Each entry: {id, parent_id, generation, algorithm, color, birth_time}
        self.lineage_log: List[Dict[str, Any]] = []

        # Next available fish ID
        self.next_fish_id: int = 0
        
        # Extinction tracking
        self.total_extinctions: int = 0  # Count of times population went to 0
        self._last_max_generation: int = 0  # Track previous max generation to detect drops

    @property
    def reproduction_stats(self):
        return self.reproduction_manager.reproduction_stats

    @property
    def total_fish_poker_games(self) -> int:
        return self.poker_manager.total_fish_poker_games

    @total_fish_poker_games.setter
    def total_fish_poker_games(self, value: int) -> None:
        self.poker_manager.total_fish_poker_games = value

    @property
    def total_plant_poker_games(self) -> int:
        return self.poker_manager.total_plant_poker_games

    @total_plant_poker_games.setter
    def total_plant_poker_games(self, value: int) -> None:
        self.poker_manager.total_plant_poker_games = value

    @property
    def total_plant_poker_energy_transferred(self) -> float:
        return self.poker_manager.total_plant_poker_energy_transferred

    @total_plant_poker_energy_transferred.setter
    def total_plant_poker_energy_transferred(self, value: float) -> None:
        self.poker_manager.total_plant_poker_energy_transferred = value

    def _init_algorithm_stats(self) -> None:
        """Initialize algorithm stats for all algorithms."""
        # Import here to avoid circular dependency
        try:
            from core.algorithms import ALL_ALGORITHMS

            for i, algo_class in enumerate(ALL_ALGORITHMS):
                # Get algorithm name from class
                algo_name = algo_class.__name__
                self.algorithm_stats[i] = AlgorithmStats(algorithm_id=i, algorithm_name=algo_name)
        except ImportError:
            # If behavior_algorithms not available, just initialize empty
            for i in range(TOTAL_ALGORITHM_COUNT):
                self.algorithm_stats[i] = AlgorithmStats(
                    algorithm_id=i, algorithm_name=f"Algorithm_{i}"
                )

    def update(self, frame: int) -> None:
        """Update ecosystem state.

        Args:
            frame: Current frame number
        """
        self.frame_count = frame

        # NEW: Check for algorithm extinctions
        self.enhanced_stats.check_for_extinctions(frame, self)
        
        # Check for population extinction (max generation drops to 0)
        alive_generations = [g for g, s in self.generation_stats.items() if s.population > 0]
        current_max_gen = max(alive_generations) if alive_generations else 0
        
        # If we had fish before but now have none, increment extinction counter
        if self._last_max_generation > 0 and current_max_gen == 0:
            self.total_extinctions += 1
            logger.info(f"Population extinction #{self.total_extinctions} detected at frame {frame}")
        
        self._last_max_generation = current_max_gen

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

    def record_birth(
        self,
        fish_id: int,
        generation: int,
        parent_ids: Optional[List[int]] = None,
        algorithm_id: Optional[int] = None,
        color: Optional[str] = None,
    ) -> None:
        from core import ecosystem_population

        ecosystem_population.record_birth(
            self, fish_id, generation, parent_ids, algorithm_id, color
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
    ) -> None:
        from core import ecosystem_population

        ecosystem_population.record_death(
            self,
            fish_id,
            generation,
            age,
            cause,
            genome,
            algorithm_id,
            remaining_energy,
        )

    def update_population_stats(self, fish_list: List["Fish"]) -> None:
        from core import ecosystem_population

        ecosystem_population.update_population_stats(self, fish_list)

    def update_genetic_diversity_stats(self, fish_list: List["Fish"]) -> None:
        from core import ecosystem_population

        ecosystem_population.update_genetic_diversity_stats(self, fish_list)

    def _add_event(self, event: EcosystemEvent) -> None:
        """Add an event to the log, maintaining max size.

        Args:
            event: Event to log
        """
        self.events.append(event)

        # Trim old events if we exceed max
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def get_recent_events(self, count: int = 10) -> List[EcosystemEvent]:
        """Get the most recent events.

        Args:
            count: Number of recent events to return

        Returns:
            List of recent events
        """
        return self.events[-count:]

    def get_population_by_generation(self) -> Dict[int, int]:
        from core import ecosystem_population

        return ecosystem_population.get_population_by_generation(self)

    def get_total_population(self) -> int:
        from core import ecosystem_population

        return ecosystem_population.get_total_population(self)

    def get_summary_stats(self, entities: Optional[List] = None) -> Dict[str, Any]:
        from core import ecosystem_population

        return ecosystem_population.get_summary_stats(self, entities)

    def get_poker_stats_summary(self) -> Dict[str, Any]:
        return self.poker_manager.get_poker_stats_summary()

    def get_poker_leaderboard(
        self, fish_list: Optional[List] = None, limit: int = 10, sort_by: str = "net_energy"
    ) -> List[Dict[str, Any]]:
        return self.poker_manager.get_poker_leaderboard(
            fish_list, sort_by=sort_by, limit=limit
        )

    def get_reproduction_summary(self) -> Dict[str, Any]:
        return self.reproduction_manager.get_summary()

    def get_diversity_summary(self) -> Dict[str, Any]:
        """Get summary genetic diversity statistics.

        Returns:
            Dictionary with diversity metrics
        """
        diversity_score = self.genetic_diversity_stats.get_diversity_score()
        trait_vars = self.genetic_diversity_stats.trait_variances

        return {
            "unique_algorithms": self.genetic_diversity_stats.unique_algorithms,
            "unique_species": self.genetic_diversity_stats.unique_species,
            "color_variance": self.genetic_diversity_stats.color_variance,
            "speed_variance": trait_vars.get("speed", 0.0),
            "size_variance": trait_vars.get("size", 0.0),
            "vision_variance": trait_vars.get("vision", 0.0),
            "diversity_score": diversity_score,
            "diversity_score_pct": f"{diversity_score:.1%}",
        }

    def get_enhanced_stats_summary(self) -> Dict[str, Any]:
        """Get comprehensive enhanced statistics report.

        Returns:
            Dictionary with all enhanced statistics
        """
        return self.enhanced_stats.get_full_report()

    def record_reproduction(self, algorithm_id: int) -> None:
        """Record a successful reproduction by a fish with the given algorithm."""
        self.reproduction_manager.record_reproduction(algorithm_id)

    def record_mating_attempt(self, success: bool) -> None:
        """Record a mating attempt (successful or failed)."""
        self.reproduction_manager.record_mating_attempt(success)

    def update_pregnant_count(self, count: int) -> None:
        """Update the count of currently pregnant fish."""
        self.reproduction_manager.update_pregnant_count(count)

    def record_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record food consumption by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
            energy_gained: Energy gained from food
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1

        # NEW: Track energy from food for efficiency metrics
        self.enhanced_stats.record_energy_from_food(energy_gained)

    def record_poker_outcome(
        self,
        winner_id: int,
        loser_id: int,
        winner_algo_id: Optional[int],
        loser_algo_id: Optional[int],
        amount: float,
        winner_hand: "PokerHand",
        loser_hand: "PokerHand",
        house_cut: float = 0.0,
        result: Optional["PokerResult"] = None,
        player1_algo_id: Optional[int] = None,
        player2_algo_id: Optional[int] = None,
    ) -> None:
        """Record a poker game outcome with detailed statistics."""
        self.poker_manager.record_poker_outcome(
            winner_id,
            loser_id,
            winner_algo_id,
            loser_algo_id,
            amount,
            winner_hand,
            loser_hand,
            house_cut,
            result,
            player1_algo_id,
            player2_algo_id,
        )

    def record_plant_poker_game(
        self,
        fish_id: int,
        plant_id: int,
        fish_won: bool,
        energy_transferred: float,
        fish_hand_rank: int,
        plant_hand_rank: int,
        won_by_fold: bool,
    ) -> None:
        """Record a poker game between a fish and a fractal plant."""
        self.poker_manager.record_plant_poker_game(
            fish_id,
            plant_id,
            fish_won,
            energy_transferred,
            fish_hand_rank,
            plant_hand_rank,
            won_by_fold,
        )

    def get_algorithm_performance_report(self, min_sample_size: int = 5) -> str:
        from core import algorithm_reporter

        return algorithm_reporter.get_algorithm_performance_report(self, min_sample_size)

    def get_lineage_data(self, alive_fish_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization.

        Args:
            alive_fish_ids: Set of fish IDs that are currently alive

        Returns:
            List of lineage records with parent-child relationships and alive status
        """
        if alive_fish_ids is None:
            alive_fish_ids = set()

        # Add is_alive flag to each lineage record
        enriched_lineage = []
        for record in self.lineage_log:
            fish_id = int(record["id"]) if record["id"] != "root" else -1
            enriched_record = {
                **record,
                "is_alive": fish_id in alive_fish_ids
            }
            enriched_lineage.append(enriched_record)

        return enriched_lineage
