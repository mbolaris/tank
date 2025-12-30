"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
EcosystemManager is a facade that composes specialized trackers.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from core.config.ecosystem import (
    ENERGY_STATS_WINDOW_FRAMES,
    MAX_ECOSYSTEM_EVENTS,
)
from core.ecosystem_stats import (
    EcosystemEvent,
    GeneticDiversityStats,
    PokerStats,
    PokerOutcomeRecord,
    PlantPokerOutcomeRecord,
    MixedPokerOutcomeRecord,
)
from core.lineage_tracker import LineageTracker
from core.poker_stats_manager import PokerStatsManager
from core.population_tracker import PopulationTracker
from core.reproduction_stats_manager import ReproductionStatsManager
from core.services.energy_tracker import EnergyTracker
from core.telemetry.events import (
    BirthEvent,
    EnergyBurnEvent,
    EnergyGainEvent,
    FoodEatenEvent,
    ReproductionEvent,
    TelemetryEvent,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome


logger = logging.getLogger(__name__)


class EcosystemManager:
    """Facade for ecosystem subsystems.

    Composes specialized trackers for different concerns:
    - PopulationTracker: births, deaths, generations, algorithm stats
    - LineageTracker: phylogenetic tree data
    - PokerStatsManager: poker game statistics
    - ReproductionStatsManager: reproduction statistics
    - EnergyTracker: energy flow tracking
    - EnhancedStatisticsTracker: time series and correlations

    Attributes:
        max_population: Maximum number of fish allowed (carrying capacity)
    """

    def __init__(self, max_population: int = 75):
        """Initialize the ecosystem manager.

        Args:
            max_population: Maximum number of fish (carrying capacity)
        """
        self.frame_count: int = 0

        # Event logging (simple, kept inline)
        self.events: List[EcosystemEvent] = []
        self.max_events: int = MAX_ECOSYSTEM_EVENTS

        # Population tracking (births, deaths, generations)
        self.population = PopulationTracker(
            max_population=max_population,
            add_event_callback=self._add_event,
            frame_provider=lambda: self.frame_count,
        )

        # Lineage tracking for phylogenetic tree
        self.lineage = LineageTracker()

        # Poker statistics tracking
        self.poker_manager = PokerStatsManager(
            add_event=self._add_event, frame_provider=lambda: self.frame_count
        )

        # Reproduction statistics tracking
        self.reproduction_manager = ReproductionStatsManager(self.population.algorithm_stats)

        # Genetic diversity statistics tracking
        self.genetic_diversity_stats: GeneticDiversityStats = GeneticDiversityStats()

        # Enhanced statistics tracker (time series, correlations, extinctions)
        from core.enhanced_statistics import EnhancedStatisticsTracker

        self.enhanced_stats: EnhancedStatisticsTracker = EnhancedStatisticsTracker(
            max_history_length=1000
        )

        # Energy tracking
        self.energy_tracker = EnergyTracker()

    # =========================================================================
    # Backward-compatible property aliases (delegate to PopulationTracker)
    # =========================================================================

    @property
    def max_population(self) -> int:
        return self.population.max_population

    @max_population.setter
    def max_population(self, value: int) -> None:
        self.population.max_population = value

    @property
    def current_generation(self) -> int:
        return self.population.current_generation

    @current_generation.setter
    def current_generation(self, value: int) -> None:
        self.population.current_generation = value

    @property
    def total_births(self) -> int:
        return self.population.total_births

    @total_births.setter
    def total_births(self, value: int) -> None:
        self.population.total_births = value

    @property
    def total_deaths(self) -> int:
        return self.population.total_deaths

    @total_deaths.setter
    def total_deaths(self, value: int) -> None:
        self.population.total_deaths = value

    @property
    def generation_stats(self) -> Dict:
        return self.population.generation_stats

    @property
    def death_causes(self) -> Dict[str, int]:
        return self.population.death_causes

    @property
    def algorithm_stats(self) -> Dict:
        return self.population.algorithm_stats

    @property
    def next_fish_id(self) -> int:
        return self.population.next_fish_id

    @next_fish_id.setter
    def next_fish_id(self, value: int) -> None:
        self.population.next_fish_id = value

    @property
    def total_extinctions(self) -> int:
        return self.population.total_extinctions

    @property
    def lineage_log(self) -> List[Dict[str, Any]]:
        return self.lineage.lineage_log

    @property
    def poker_stats(self) -> Dict[int, PokerStats]:
        return self.poker_manager.poker_stats

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

    # =========================================================================
    # Core Methods
    # =========================================================================

    def update(self, frame: int) -> None:
        """Update ecosystem state.

        Args:
            frame: Current frame number
        """
        self.energy_tracker.advance_frame(frame)
        self.frame_count = frame

        # Check for algorithm extinctions
        self.enhanced_stats.check_for_extinctions(frame, self)

        # Check for population extinction
        self.population.check_for_extinction(frame)

    def generate_new_fish_id(self) -> int:
        """Generate a new unique fish ID."""
        return self.population.generate_new_fish_id()

    def can_reproduce(self, current_population: int) -> bool:
        """Check if reproduction is allowed based on carrying capacity."""
        return self.population.can_reproduce(current_population)

    def cleanup_dead_fish(self, alive_fish_ids: Set[int]) -> int:
        """Cleanup stats for dead fish."""
        return self.poker_manager.cleanup_dead_fish(alive_fish_ids)

    # =========================================================================
    # Event Logging
    # =========================================================================

    def _add_event(self, event: EcosystemEvent) -> None:
        """Add an event to the log, maintaining max size."""
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def get_recent_events(self, count: int = 10) -> List[EcosystemEvent]:
        """Get the most recent events."""
        return self.events[-count:]

    # =========================================================================
    # Telemetry Event Recording
    # =========================================================================

    def record_event(self, event: TelemetryEvent) -> None:
        """Record a telemetry event emitted by domain entities."""
        if isinstance(event, EnergyGainEvent):
            if event.scope == "plant":
                self.record_plant_energy_gain(event.source, event.amount)
            else:
                self.record_energy_gain(event.source, event.amount)
            return

        if isinstance(event, EnergyBurnEvent):
            if event.scope == "plant":
                self.record_plant_energy_burn(event.source, event.amount)
            else:
                self.record_energy_burn(event.source, event.amount)
            return

        if isinstance(event, FoodEatenEvent):
            if event.food_type == "nectar":
                self.record_nectar_eaten(event.algorithm_id, event.energy_gained)
            elif event.food_type == "live_food":
                self.record_live_food_eaten(
                    event.algorithm_id,
                    event.energy_gained,
                    genome=event.genome,
                    generation=event.generation,
                )
            elif event.food_type == "falling_food":
                self.record_falling_food_eaten(event.algorithm_id, event.energy_gained)
            else:
                self.record_food_eaten(event.algorithm_id, event.energy_gained)
            return

        if isinstance(event, BirthEvent):
            self.record_birth(
                event.fish_id,
                event.generation,
                parent_ids=list(event.parent_ids) if event.parent_ids else None,
                algorithm_id=event.algorithm_id,
                color=event.color_hex,
                algorithm_name=event.algorithm_name,
                tank_name=event.tank_name,
            )
            if event.is_soup_spawn:
                self.record_energy_gain("soup_spawn", event.energy)
            return

        if isinstance(event, ReproductionEvent):
            self.record_reproduction(event.algorithm_id, is_asexual=event.is_asexual)
            return

    # =========================================================================
    # Population Recording (delegate to PopulationTracker)
    # =========================================================================

    def record_birth(
        self,
        fish_id: int,
        generation: int,
        parent_ids: Optional[List[int]] = None,
        algorithm_id: Optional[int] = None,
        color: Optional[str] = None,
        algorithm_name: Optional[str] = None,
        tank_name: Optional[str] = None,
    ) -> None:
        """Record a fish birth."""
        # Use provided algorithm_name if available, otherwise try lookup
        if algorithm_name is None:
            algorithm_name = "Unknown"
            if algorithm_id is not None and algorithm_id in self.algorithm_stats:
                algorithm_name = self.algorithm_stats[algorithm_id].algorithm_name

        # Record in population tracker
        self.population.record_birth(
            fish_id=fish_id,
            generation=generation,
            parent_ids=parent_ids,
            algorithm_id=algorithm_id,
            color=color,
            lineage_log=None,  # We'll handle lineage separately
            enhanced_stats=self.enhanced_stats,
        )

        # Record in lineage tracker
        parent_id = parent_ids[0] if parent_ids else None
        self.lineage.record_birth(
            fish_id=fish_id,
            parent_id=parent_id,
            generation=generation,
            algorithm_name=algorithm_name,
            color=color or "#00ff00",
            birth_frame=self.frame_count,
            tank_name=tank_name,
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
        """Record a fish death."""
        self.population.record_death(
            fish_id=fish_id,
            generation=generation,
            age=age,
            cause=cause,
            genome=genome,
            algorithm_id=algorithm_id,
            remaining_energy=remaining_energy,
            enhanced_stats=self.enhanced_stats,
            record_energy_burn=self.record_energy_burn,
        )

    def update_population_stats(self, fish_list: List["Fish"]) -> None:
        """Update population statistics from current fish list."""
        self.population.update_population_stats(
            fish_list=fish_list,
            enhanced_stats=self.enhanced_stats,
        )
        self._update_genetic_diversity_stats(fish_list)
        self.update_pregnant_count(0)  # No pregnancy in current system

    def _update_genetic_diversity_stats(self, fish_list: List["Fish"]) -> None:
        """Update genetic diversity statistics."""
        if not fish_list:
            self.genetic_diversity_stats = GeneticDiversityStats()
            return

        algorithms = set()
        species = set()
        color_hues = []
        speed_modifiers = []
        size_modifiers = []
        vision_ranges = []

        for fish in fish_list:
            genome = fish.genome

            composable = genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                behavior_id = composable.value.behavior_id
                algorithms.add(hash(behavior_id) % 1000)

            species.add(fish.species)
            color_hues.append(genome.physical.color_hue.value)
            speed_modifiers.append(genome.speed_modifier)
            size_modifiers.append(genome.physical.size_modifier.value)
            vision_ranges.append(genome.vision_range)

        n_fish = len(fish_list)

        color_variance = 0.0
        if n_fish > 1:
            mean_color = sum(color_hues) / n_fish
            color_variance = sum((h - mean_color) ** 2 for h in color_hues) / n_fish

        trait_variances: Dict[str, float] = {}
        if n_fish > 1:
            mean_speed = sum(speed_modifiers) / n_fish
            trait_variances["speed"] = sum((s - mean_speed) ** 2 for s in speed_modifiers) / n_fish

            mean_size = sum(size_modifiers) / n_fish
            trait_variances["size"] = sum((s - mean_size) ** 2 for s in size_modifiers) / n_fish

            mean_vision = sum(vision_ranges) / n_fish
            trait_variances["vision"] = sum((v - mean_vision) ** 2 for v in vision_ranges) / n_fish

        self.genetic_diversity_stats.unique_algorithms = len(algorithms)
        self.genetic_diversity_stats.unique_species = len(species)
        self.genetic_diversity_stats.color_variance = color_variance
        self.genetic_diversity_stats.trait_variances = trait_variances

    # =========================================================================
    # Query Methods (delegate to trackers)
    # =========================================================================

    def get_population_by_generation(self) -> Dict[int, int]:
        """Get current population counts by generation."""
        return self.population.get_population_by_generation()

    def get_total_population(self) -> int:
        """Get total population across all generations."""
        return self.population.get_total_population()

    def get_lineage_data(self, alive_fish_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization."""
        return self.lineage.get_lineage_data(alive_fish_ids)

    def get_summary_stats(self, entities: Optional[List] = None) -> Dict[str, Any]:
        """Get comprehensive ecosystem summary statistics."""
        from statistics import median

        from core.config.ecosystem import ENERGY_STATS_WINDOW_FRAMES
        from core.config.fish import (
            FISH_ADULT_SIZE,
            FISH_SIZE_MODIFIER_MAX,
            FISH_SIZE_MODIFIER_MIN,
        )

        total_pop = self.get_total_population()
        poker_summary = self.get_poker_stats_summary()

        energy_summary = self.get_energy_source_summary()
        recent_energy = self.get_recent_energy_breakdown(window_frames=ENERGY_STATS_WINDOW_FRAMES)
        recent_energy_burn = self.get_recent_energy_burn(window_frames=ENERGY_STATS_WINDOW_FRAMES)
        energy_delta = self.get_energy_delta(window_frames=ENERGY_STATS_WINDOW_FRAMES)

        recent_energy_total = sum(recent_energy.values())
        recent_energy_burn_total = sum(recent_energy_burn.values())
        recent_energy_net = recent_energy_total - recent_energy_burn_total
        energy_accounting_discrepancy = recent_energy_net - energy_delta.get("energy_delta", 0.0)

        plant_energy_summary = self.get_plant_energy_source_summary()
        recent_plant_energy = self.get_recent_plant_energy_breakdown(
            window_frames=ENERGY_STATS_WINDOW_FRAMES
        )
        recent_plant_energy_burn = self.get_recent_plant_energy_burn(
            window_frames=ENERGY_STATS_WINDOW_FRAMES
        )

        total_energy = 0.0
        fish_list = []
        if entities is not None:
            from core.entities import Fish

            fish_list = [e for e in entities if isinstance(e, Fish)]
            total_energy = sum(
                e.energy + e._reproduction_component.overflow_energy_bank for e in fish_list
            )

        alive_generations = [
            g for g, stats in self.generation_stats.items() if stats.population > 0
        ]

        # Calculate adult size stats if we have fish
        adult_size_min = 0.0
        adult_size_max = 0.0
        adult_size_median = 0.0
        adult_size_range = "0.0-0.0"
        if fish_list:
            adult_sizes = [
                FISH_ADULT_SIZE
                * (f.genome.physical.size_modifier.value if hasattr(f, "genome") else 1.0)
                for f in fish_list
            ]
            adult_size_min = min(adult_sizes)
            adult_size_max = max(adult_sizes)
            try:
                adult_size_median = median(adult_sizes)
            except Exception:
                adult_size_median = 0.0
            adult_size_range = f"{adult_size_min:.2f}-{adult_size_max:.2f}"

        return {
            "total_population": total_pop,
            "current_generation": self.current_generation,
            "max_generation": max(alive_generations) if alive_generations else 0,
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "total_extinctions": self.total_extinctions,
            "carrying_capacity": self.max_population,
            "capacity_usage": (
                f"{int(100 * total_pop / self.max_population)}%"
                if self.max_population > 0
                else "0%"
            ),
            "death_causes": dict(self.death_causes),
            "generations_alive": len(alive_generations),
            "poker_stats": poker_summary,
            "total_energy": total_energy,
            "energy_sources": energy_summary,
            "energy_from_nectar": recent_energy.get("nectar", 0.0),
            "energy_from_live_food": recent_energy.get("live_food", 0.0),
            "energy_from_falling_food": recent_energy.get("falling_food", 0.0),
            "energy_from_poker": recent_energy.get("poker_fish", 0.0),
            "energy_from_poker_plant": recent_energy.get("poker_plant", 0.0),
            "energy_from_auto_eval": recent_energy.get("auto_eval", 0.0),
            "energy_from_birth": recent_energy.get("birth", 0.0),
            "energy_from_soup_spawn": recent_energy.get("soup_spawn", 0.0),
            "energy_from_migration_in": recent_energy.get("migration_in", 0.0),
            "energy_burn_recent": recent_energy_burn,
            "energy_burn_total": recent_energy_burn_total,
            "energy_sources_recent": recent_energy,
            "energy_gains_recent_total": recent_energy_total,
            "energy_net_recent": recent_energy_net,
            "energy_accounting_discrepancy": energy_accounting_discrepancy,
            "energy_delta": energy_delta,
            "plant_energy_sources": plant_energy_summary,
            "plant_energy_sources_recent": recent_plant_energy,
            "plant_energy_from_photosynthesis": recent_plant_energy.get("photosynthesis", 0.0),
            "plant_energy_burn_recent": recent_plant_energy_burn,
            "plant_energy_burn_total": sum(recent_plant_energy_burn.values()),
            "adult_size_min": adult_size_min,
            "adult_size_max": adult_size_max,
            "adult_size_median": adult_size_median,
            "adult_size_range": adult_size_range,
            "allowed_adult_size_min": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN,
            "allowed_adult_size_max": FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX,
            "reproduction_stats": self.get_reproduction_summary(),
            "diversity_stats": self.get_diversity_summary(),
        }

    def get_poker_stats_summary(self) -> Dict[str, Any]:
        """Get poker statistics summary."""
        return self.poker_manager.get_poker_stats_summary()

    def get_poker_leaderboard(
        self,
        fish_list: Optional[List] = None,
        limit: int = 10,
        sort_by: str = "net_energy",
    ) -> List[Dict[str, Any]]:
        """Get poker leaderboard."""
        return self.poker_manager.get_poker_leaderboard(fish_list, sort_by=sort_by, limit=limit)

    def get_reproduction_summary(self) -> Dict[str, Any]:
        """Get reproduction statistics summary."""
        return self.reproduction_manager.get_summary()

    def get_diversity_summary(self) -> Dict[str, Any]:
        """Get summary genetic diversity statistics."""
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
        """Get comprehensive enhanced statistics report."""
        return self.enhanced_stats.get_full_report()

    # =========================================================================
    # Reproduction Recording
    # =========================================================================

    def record_reproduction(self, algorithm_id: int, is_asexual: bool = False) -> None:
        """Record a successful reproduction."""
        self.reproduction_manager.record_reproduction(algorithm_id, is_asexual=is_asexual)

    def record_mating_attempt(self, success: bool) -> None:
        """Record a mating attempt."""
        self.reproduction_manager.record_mating_attempt(success)

    def update_pregnant_count(self, count: int) -> None:
        """Update the count of currently pregnant fish."""
        self.reproduction_manager.update_pregnant_count(count)

    # =========================================================================
    # Food Recording
    # =========================================================================

    def record_nectar_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record nectar consumption."""
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1
        self.enhanced_stats.record_energy_from_food(energy_gained)
        self.record_energy_gain("nectar", energy_gained)

    def record_live_food_eaten(
        self,
        algorithm_id: int,
        energy_gained: float = 10.0,
        genome: Optional["Genome"] = None,
        generation: Optional[int] = None,
    ) -> None:
        """Record live food consumption."""
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1
        self.enhanced_stats.record_energy_from_food(energy_gained)
        if genome is not None:
            self.enhanced_stats.record_live_food_capture(
                algorithm_id, energy_gained, genome, generation
            )
        self.record_energy_gain("live_food", energy_gained)

    def record_falling_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record falling food consumption."""
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1
        self.enhanced_stats.record_energy_from_food(energy_gained)
        self.record_energy_gain("falling_food", energy_gained)

    def record_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record generic food consumption."""
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1
        self.enhanced_stats.record_energy_from_food(energy_gained)

    # =========================================================================
    # Poker Recording
    # =========================================================================

    def record_poker_outcome_record(self, record: PokerOutcomeRecord) -> None:
        """Record a poker game outcome from a value object."""
        self.poker_manager.record_poker_outcome(
            record.winner_id,
            record.loser_id,
            record.winner_algo_id,
            record.loser_algo_id,
            record.amount,
            record.winner_hand,
            record.loser_hand,
            record.house_cut,
            record.result,
            record.player1_algo_id,
            record.player2_algo_id,
        )

    def record_plant_poker_game_record(self, record: PlantPokerOutcomeRecord) -> None:
        """Record a plant poker outcome from a value object."""
        self.poker_manager.record_plant_poker_game(
            record.fish_id,
            record.plant_id,
            record.fish_won,
            record.energy_transferred,
            record.fish_hand_rank,
            record.plant_hand_rank,
            record.won_by_fold,
        )
        net_amount = record.energy_transferred if record.fish_won else -record.energy_transferred
        self.record_plant_poker_energy_gain(net_amount)

    def record_mixed_poker_energy_transfer(
        self,
        energy_to_fish: float,
        is_plant_game: bool = True,
        winner_type: str = "",
    ) -> None:
        """Record energy transfer from a mixed poker game.

        Args:
            energy_to_fish: Net energy transferred to fish
            is_plant_game: Whether this game involved plants
            winner_type: "fish" or "plant" - who won the game
        """
        self.poker_manager.record_mixed_poker_energy_transfer(
            energy_to_fish, winner_type=winner_type, is_plant_game=is_plant_game
        )
        self.record_plant_poker_energy_gain(energy_to_fish)

    def record_mixed_poker_outcome_record(self, record: MixedPokerOutcomeRecord) -> None:
        """Record mixed poker outcome with correct per-economy house cut attribution."""
        self.poker_manager.record_mixed_poker_energy_transfer(
            record.fish_delta,
            winner_type=record.winner_type,
            is_plant_game=True,
        )

        winner_is_fish = record.winner_type == "fish"
        house_cut = float(record.house_cut or 0.0)

        if record.fish_delta > 0:
            gross = record.fish_delta + (house_cut if winner_is_fish else 0.0)
            self.record_energy_gain("poker_plant", gross)
            if winner_is_fish and house_cut > 0:
                self.record_energy_burn("poker_house_cut", house_cut)
        elif record.fish_delta < 0:
            self.record_energy_burn("poker_plant_loss", -record.fish_delta)

        if (not winner_is_fish) and house_cut > 0:
            self.record_plant_energy_gain("poker", house_cut)
            self.record_plant_energy_burn("poker_house_cut", house_cut)

    def record_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-fish poker."""
        self.record_energy_gain("poker_fish", amount)

    def record_plant_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-plant poker."""
        if amount >= 0:
            self.record_energy_gain("poker_plant", amount)
        else:
            self.record_energy_burn("poker_plant_loss", -amount)

    def record_auto_eval_energy_gain(self, amount: float) -> None:
        """Track energy awarded through auto-evaluation benchmarks."""
        self.record_energy_gain("auto_eval", amount)

    # =========================================================================
    # Energy Recording (delegate to EnergyTracker)
    # =========================================================================

    def record_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate energy gains by source."""
        self.energy_tracker.record_energy_gain(source, amount)

    def record_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate energy spent."""
        self.energy_tracker.record_energy_burn(source, amount)

    def record_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed energy delta."""
        self.energy_tracker.record_energy_delta(source, delta, negative_source=negative_source)

    def record_energy_transfer(self, source: str, amount: float) -> None:
        """Record an internal transfer as both a gain and a burn."""
        self.energy_tracker.record_energy_transfer(source, amount)

    def record_plant_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate plant energy gains."""
        self.energy_tracker.record_plant_energy_gain(source, amount)

    def record_plant_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate plant energy spent."""
        self.energy_tracker.record_plant_energy_burn(source, amount)

    def record_plant_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed plant energy delta."""
        self.energy_tracker.record_plant_energy_delta(
            source, delta, negative_source=negative_source
        )

    def record_plant_energy_transfer(self, source: str, amount: float) -> None:
        """Record a plant internal transfer."""
        self.energy_tracker.record_plant_energy_transfer(source, amount)

    def get_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated energy gains."""
        return self.energy_tracker.get_energy_source_summary()

    def get_plant_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated plant energy gains."""
        return self.energy_tracker.get_plant_energy_source_summary()

    def get_recent_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get energy source breakdown over recent frames."""
        return self.energy_tracker.get_recent_energy_breakdown(window_frames=window_frames)

    def get_recent_plant_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy source breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_breakdown(window_frames=window_frames)

    def get_recent_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_energy_burn(window_frames=window_frames)

    def get_recent_plant_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_burn(window_frames=window_frames)

    def record_energy_snapshot(self, total_fish_energy: float, fish_count: int) -> None:
        """Record a snapshot of total fish energy."""
        self.energy_tracker.record_energy_snapshot(total_fish_energy, fish_count)

    def get_energy_delta(self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES) -> Dict[str, Any]:
        """Calculate the true change in fish population energy over a time window."""
        return self.energy_tracker.get_energy_delta(window_frames=window_frames)

    # =========================================================================
    # Algorithm Performance
    # =========================================================================

    def get_algorithm_performance_report(self, min_sample_size: int = 5) -> str:
        """Get algorithm performance report."""
        from core import algorithm_reporter

        return algorithm_reporter.get_algorithm_performance_report(self, min_sample_size)

    def get_poker_strategy_distribution(self, fish_list: List["Fish"]) -> Dict[str, Any]:
        """Get distribution of poker strategies in the population."""
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

            if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
                ps = fish.poker_stats
                if ps.total_games > 0:
                    strategy_win_rates[strat.strategy_id].append(ps.get_win_rate())

        result = {
            "total_fish": len(fish_list),
            "strategy_counts": dict(strategy_counts),
            "dominant_strategy": (
                strategy_counts.most_common(1)[0][0] if strategy_counts else None
            ),
            "diversity": len(strategy_counts),
            "strategy_avg_win_rates": {},
        }

        for strat_id, rates in strategy_win_rates.items():
            if rates:
                result["strategy_avg_win_rates"][strat_id] = sum(rates) / len(rates)

        return result

    def log_poker_evolution_status(self, fish_list: List["Fish"]) -> None:
        """Log current poker evolution status to console."""
        dist = self.get_poker_strategy_distribution(fish_list)

        if not dist["strategy_counts"]:
            logger.info("Poker Evolution: No fish with poker strategies")
            return

        sorted_strats = sorted(dist["strategy_counts"].items(), key=lambda x: x[1], reverse=True)

        strat_str = ", ".join(f"{s}:{c}" for s, c in sorted_strats[:5])
        dominant = dist["dominant_strategy"]
        diversity = dist["diversity"]
        dom_win_rate = dist["strategy_avg_win_rates"].get(dominant, 0)

        logger.info(
            f"Poker Evolution [Gen {self.current_generation}]: "
            f"Dominant={dominant} ({dom_win_rate:.1%} win rate), "
            f"Diversity={diversity}, Distribution=[{strat_str}]"
        )
