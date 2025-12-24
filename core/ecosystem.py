"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from core.config.ecosystem import (
    ENERGY_STATS_WINDOW_FRAMES,
    MAX_ECOSYSTEM_EVENTS,
    TOTAL_ALGORITHM_COUNT,
)
from core.ecosystem_stats import (
    AlgorithmStats,
    EcosystemEvent,
    GenerationStats,
    GeneticDiversityStats,
    PokerStats,
)
from core.poker_stats_manager import PokerStatsManager
from core.reproduction_stats_manager import ReproductionStatsManager
from core.services.energy_tracker import EnergyTracker

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
        self.lineage_log: List[Dict[str, Any]] = []

        # Next available fish ID
        self.next_fish_id: int = 0

        # Extinction tracking
        self.total_extinctions: int = 0  # Count of times population went to 0
        self._last_max_generation: int = 0  # Track previous max generation to detect drops

        self.energy_tracker = EnergyTracker()






    @property
    def reproduction_stats(self):
        return self.reproduction_manager.reproduction_stats

    @property
    def energy_sources(self) -> Dict[str, float]:
        return self.energy_tracker.energy_sources

    @property
    def energy_burn(self) -> Dict[str, float]:
        return self.energy_tracker.energy_burn

    @property
    def plant_energy_sources(self) -> Dict[str, float]:
        return self.energy_tracker.plant_energy_sources

    @property
    def plant_energy_burn(self) -> Dict[str, float]:
        return self.energy_tracker.plant_energy_burn

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
            from core.algorithms.registry import ALL_ALGORITHMS

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
        # Snapshot energy stats from the previous frame before moving to new frame.
        self.energy_tracker.advance_frame(frame)
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

    def generate_new_fish_id(self) -> int:
        """Generate a new unique fish ID.

        Returns:
            Unique integer ID for a fish
        """
        fish_id = self.next_fish_id
        self.next_fish_id += 1
        return fish_id

    def cleanup_dead_fish(self, alive_fish_ids: Set[int]) -> int:
        """Cleanup stats for dead fish.

        Args:
            alive_fish_ids: Set of currently living fish IDs.

        Returns:
            Number of records removed.
        """
        return self.poker_manager.cleanup_dead_fish(alive_fish_ids)

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

    def record_reproduction(self, algorithm_id: int, is_asexual: bool = False) -> None:
        """Record a successful reproduction by a fish with the given algorithm."""
        self.reproduction_manager.record_reproduction(algorithm_id, is_asexual=is_asexual)

    def record_mating_attempt(self, success: bool) -> None:
        """Record a mating attempt (successful or failed)."""
        self.reproduction_manager.record_mating_attempt(success)

    def update_pregnant_count(self, count: int) -> None:
        """Update the count of currently pregnant fish."""
        self.reproduction_manager.update_pregnant_count(count)

    def record_nectar_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record nectar consumption by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
            energy_gained: Energy gained from nectar
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1

        # NEW: Track energy from nectar for efficiency metrics
        self.enhanced_stats.record_energy_from_food(energy_gained)
        self.record_energy_gain('nectar', energy_gained)

    def record_live_food_eaten(
        self,
        algorithm_id: int,
        energy_gained: float = 10.0,
        genome: Optional["Genome"] = None,
        generation: Optional[int] = None,
    ) -> None:
        """Record live food consumption by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
            energy_gained: Energy gained from live food
            genome: Optional genome so we can attribute trait correlations
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1

        # NEW: Track energy from live food for efficiency metrics
        self.enhanced_stats.record_energy_from_food(energy_gained)
        if genome is not None:
            self.enhanced_stats.record_live_food_capture(
                algorithm_id, energy_gained, genome, generation
            )

        self.record_energy_gain('live_food', energy_gained)

    def record_falling_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record falling food consumption by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
            energy_gained: Energy gained from falling food
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1

        # NEW: Track energy from falling food for efficiency metrics
        self.enhanced_stats.record_energy_from_food(energy_gained)
        self.record_energy_gain('falling_food', energy_gained)

    def record_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record generic food consumption by a fish with the given algorithm.

        This is a convenience method that increments the food eaten counter
        without specifying the food type. For detailed tracking, use the
        specific methods: record_nectar_eaten, record_live_food_eaten, or
        record_falling_food_eaten.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
            energy_gained: Energy gained from food (default 10.0)
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1
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

        # Record energy flow for stats window
        net_amount = energy_transferred if fish_won else -energy_transferred
        self.record_plant_poker_energy_gain(net_amount)

    def record_mixed_poker_energy_transfer(
        self,
        energy_to_fish: float,
        is_plant_game: bool = True,
    ) -> None:
        """Record energy transfer from a mixed poker game (fish + plants).

        Args:
            energy_to_fish: Net energy transferred to fish (positive = fish gained from plants,
                           negative = plants gained from fish)
            is_plant_game: Whether this game involved plants (for counting)
        """
        self.poker_manager.record_mixed_poker_energy_transfer(energy_to_fish, is_plant_game)

        # Record energy flow for stats window
        self.record_plant_poker_energy_gain(energy_to_fish)

    def record_mixed_poker_outcome(
        self,
        *,
        fish_delta: float,
        plant_delta: float,
        house_cut: float,
        winner_type: str,
    ) -> None:
        """Record mixed poker outcome with correct per-economy house cut attribution.

        Mixed poker changes both fish and plant energies (internal transfer), and may
        also remove energy from the winner via house cut (true external outflow).

        Policy:
        - If winner is a fish: show house cut in fish economy only.
        - If winner is a plant: show house cut in plant economy only.
        - Keep net accounting consistent by "grossing up" the winner-side poker transfer
          by the house cut when we surface it as a separate burn.
        """
        self.poker_manager.record_mixed_poker_energy_transfer(fish_delta, is_plant_game=True)

        winner_is_fish = winner_type == "fish"
        house_cut = float(house_cut or 0.0)

        # Fish economy: show house cut only when fish wins.
        if fish_delta > 0:
            gross = fish_delta + (house_cut if winner_is_fish else 0.0)
            self.record_energy_gain("poker_plant", gross)
            if winner_is_fish and house_cut > 0:
                self.record_energy_burn("poker_house_cut", house_cut)
        elif fish_delta < 0:
            # When plants win, the fish loss already includes the cut implicitly;
            # do not surface it separately in the fish economy panel.
            self.record_energy_burn("poker_plant_loss", -fish_delta)

        # Plant economy: show house cut only when plant wins.
        if (not winner_is_fish) and house_cut > 0:
            # Plant deltas are already recorded on the plant itself under "poker"
            # (net after house cut). Gross it up so we can show the cut without
            # changing the net.
            self.record_plant_energy_gain("poker", house_cut)
            self.record_plant_energy_burn("poker_house_cut", house_cut)

    def record_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-fish poker."""
        self.record_energy_gain('poker_fish', amount)

    def record_plant_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-plant poker."""
        if amount >= 0:
            self.record_energy_gain('poker_plant', amount)
        else:
            # Negative amount means fish lost to plant
            self.record_energy_burn('poker_plant_loss', -amount)

    def record_auto_eval_energy_gain(self, amount: float) -> None:
        """Track energy awarded through auto-evaluation benchmarks."""
        self.record_energy_gain('auto_eval', amount)

    def record_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate energy gains by source for downstream stats."""
        self.energy_tracker.record_energy_gain(source, amount)

    def record_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate energy spent so we can prove metabolism/movement costs are applied."""
        self.energy_tracker.record_energy_burn(source, amount)

    def record_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed energy delta as either a gain or a burn."""
        self.energy_tracker.record_energy_delta(
            source, delta, negative_source=negative_source
        )

    def record_energy_transfer(self, source: str, amount: float) -> None:
        """Record an internal transfer as both a gain and a burn (net zero)."""
        self.energy_tracker.record_energy_transfer(source, amount)

    def record_plant_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate plant energy gains by source for downstream stats."""
        self.energy_tracker.record_plant_energy_gain(source, amount)

    def record_plant_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate plant energy spent for downstream stats."""
        self.energy_tracker.record_plant_energy_burn(source, amount)

    def record_plant_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed plant energy delta as either a gain or a burn."""
        self.energy_tracker.record_plant_energy_delta(
            source, delta, negative_source=negative_source
        )

    def record_plant_energy_transfer(self, source: str, amount: float) -> None:
        """Record a plant internal transfer as both a gain and a burn (net zero)."""
        self.energy_tracker.record_plant_energy_transfer(source, amount)

    def get_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated energy gains."""
        return self.energy_tracker.get_energy_source_summary()

    def get_plant_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated plant energy gains."""
        return self.energy_tracker.get_plant_energy_source_summary()

    def get_recent_energy_breakdown(self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES) -> Dict[str, float]:
        """Get energy source breakdown over recent frames.

        Args:
            window_frames: Number of recent frames to include (default 1800 = 60 seconds at 30fps)

        Returns:
            Dictionary mapping source names to net energy gained in the window
        """
        return self.energy_tracker.get_recent_energy_breakdown(window_frames=window_frames)

    def get_recent_plant_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy source breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_breakdown(
            window_frames=window_frames
        )

    def get_recent_energy_burn(self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES) -> Dict[str, float]:
        """Get energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_energy_burn(window_frames=window_frames)

    def get_recent_plant_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_burn(
            window_frames=window_frames
        )

    def record_energy_snapshot(self, total_fish_energy: float, fish_count: int) -> None:
        """Record a snapshot of total fish energy for delta calculations.

        Call this method periodically (e.g., every frame or every few frames)
        with the current total energy of all fish in the tank.

        Args:
            total_fish_energy: Sum of energy across all living fish
            fish_count: Number of fish currently alive
        """
        self.energy_tracker.record_energy_snapshot(total_fish_energy, fish_count)

    def get_energy_delta(self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES) -> Dict[str, Any]:
        """Calculate the true change in fish population energy over a time window.

        This returns the actual delta in total fish energy, which may differ
        from the "net external flow" due to:
        - Fish dying with remaining energy (energy lost)
        - Fish reproducing (internal transfer)
        - Energy capping (overflow wasted)

        Args:
            window_frames: Number of frames to look back (default 1800 = 60s at 30fps)

        Returns:
            Dict with:
            - energy_delta: Change in total fish energy (current - past)
            - energy_now: Current total fish energy
            - energy_then: Total fish energy at window start
            - fish_count_now: Current fish count
            - fish_count_then: Fish count at window start
            - avg_energy_delta: Change in average energy per fish
        """
        return self.energy_tracker.get_energy_delta(window_frames=window_frames)

    def get_algorithm_performance_report(self, min_sample_size: int = 5) -> str:
        from core import algorithm_reporter

        return algorithm_reporter.get_algorithm_performance_report(self, min_sample_size)

    def get_poker_strategy_distribution(self, fish_list: List["Fish"]) -> Dict[str, Any]:
        """Get distribution of poker strategies in the population.

        This method helps visualize poker evolution by showing which strategies
        are currently dominant in the population.

        Args:
            fish_list: List of all fish in the simulation

        Returns:
            Dictionary with strategy counts, dominant strategy, and avg win rates
        """
        from collections import Counter

        strategy_counts: Counter = Counter()
        strategy_win_rates: Dict[str, List[float]] = defaultdict(list)
        strategy_params: Dict[str, List[Dict[str, float]]] = defaultdict(list)

        for fish in fish_list:
            if not hasattr(fish, "genome") or fish.genome is None:
                continue

            trait = fish.genome.behavioral.poker_strategy
            strat = trait.value if trait else None
            if strat is None:
                continue

            strategy_counts[strat.strategy_id] += 1
            strategy_params[strat.strategy_id].append(strat.parameters.copy())

            # Get win rate from fish poker stats if available
            if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
                ps = fish.poker_stats
                if ps.total_games > 0:
                    win_rate = ps.total_wins / ps.total_games
                    strategy_win_rates[strat.strategy_id].append(win_rate)

        # Calculate averages
        result = {
            "total_fish": len(fish_list),
            "strategy_counts": dict(strategy_counts),
            "dominant_strategy": strategy_counts.most_common(1)[0][0] if strategy_counts else None,
            "diversity": len(strategy_counts),
            "strategy_avg_win_rates": {},
        }

        for strat_id, rates in strategy_win_rates.items():
            if rates:
                result["strategy_avg_win_rates"][strat_id] = sum(rates) / len(rates)

        return result

    def log_poker_evolution_status(self, fish_list: List["Fish"]) -> None:
        """Log current poker evolution status to console.

        Call this periodically (e.g., every 30 seconds) to see evolution happening.

        Args:
            fish_list: List of all fish in the simulation
        """
        dist = self.get_poker_strategy_distribution(fish_list)

        if not dist["strategy_counts"]:
            logger.info("Poker Evolution: No fish with poker strategies")
            return

        # Format strategy distribution
        sorted_strats = sorted(
            dist["strategy_counts"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        strat_str = ", ".join(f"{s}:{c}" for s, c in sorted_strats[:5])
        dominant = dist["dominant_strategy"]
        diversity = dist["diversity"]

        # Get win rate for dominant strategy
        dom_win_rate = dist["strategy_avg_win_rates"].get(dominant, 0)

        logger.info(
            f"Poker Evolution [Gen {self.current_generation}]: "
            f"Dominant={dominant} ({dom_win_rate:.1%} win rate), "
            f"Diversity={diversity}, Distribution=[{strat_str}]"
        )

    def get_lineage_data(self, alive_fish_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization.

        Args:
            alive_fish_ids: Set of fish IDs that are currently alive

        Returns:
            List of lineage records with parent-child relationships and alive status
        """
        if alive_fish_ids is None:
            alive_fish_ids = set()

        # Build set of valid IDs (include explicit 'root')
        valid_ids = {rec.get("id") for rec in self.lineage_log}
        valid_ids.add("root")

        enriched_lineage: List[Dict[str, Any]] = []
        orphan_count = 0

        for record in self.lineage_log:
            # Normalize string ids and parent references
            rec_id = record.get("id")
            parent_id = record.get("parent_id", "root")

            # If parent_id references a missing id, remap to root and record the orphan
            if parent_id not in valid_ids:
                orphan_count += 1
                logger.warning(
                    "Lineage: Orphaned record detected - id=%s parent_id=%s; remapping to root",
                    rec_id,
                    parent_id,
                )
                # Create a shallow copy and preserve original parent for audit
                sanitized = dict(record)
                sanitized["parent_id"] = "root"
                sanitized["_original_parent_id"] = parent_id
            else:
                sanitized = dict(record)

            # Determine alive status (root is not a living fish)
            try:
                fish_numeric_id = int(sanitized["id"]) if sanitized.get("id") != "root" else -1
            except Exception:
                fish_numeric_id = -1

            sanitized["is_alive"] = fish_numeric_id in alive_fish_ids
            enriched_lineage.append(sanitized)

        if orphan_count > 0:
            logger.info("Lineage: Fixed %d orphaned lineage record(s) by remapping parents to root", orphan_count)

        return enriched_lineage
