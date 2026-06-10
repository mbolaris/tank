"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
EcosystemManager is a facade that composes specialized trackers.

The heavier bodies live in focused collaborators; the facade keeps thin
delegating methods so the public API and test monkeypatch points stay
unchanged:

- core/ecosystem_telemetry.py: EventBus subscriptions, telemetry event
  routing, energy delta ingestion, food-consumption recording
- core/poker_outcome_recorder.py: poker outcome -> stats/energy recording
- core/genetic_diversity_tracker.py: genetic diversity stats + summary
- core/ecosystem_reporting.py: summary-stats building, poker strategy
  distribution reports
"""

from typing import TYPE_CHECKING, Any, Optional

from core import ecosystem_reporting
from core.config.ecosystem import ENERGY_STATS_WINDOW_FRAMES, MAX_ECOSYSTEM_EVENTS
from core.ecosystem_stats import (
    EcosystemEvent,
    GeneticDiversityStats,
    MixedPokerOutcomeRecord,
    PlantPokerOutcomeRecord,
    PokerOutcomeRecord,
    PokerStats,
)
from core.ecosystem_telemetry import EcosystemTelemetryRouter
from core.genetic_diversity_tracker import GeneticDiversityTracker
from core.lineage_tracker import LineageTracker
from core.poker_outcome_recorder import PokerOutcomeRecorder
from core.poker_stats_manager import PokerStatsManager
from core.population_tracker import PopulationTracker
from core.reproduction_stats_manager import ReproductionStatsManager
from core.services.energy_tracker import EnergyTracker

if TYPE_CHECKING:
    from core.entities import Fish
    from core.events import EventBus
    from core.genetics import Genome
    from core.telemetry.events import BirthEvent, FoodEatenEvent, ReproductionEvent


class EcosystemManager:
    """Facade for ecosystem subsystems.

    Composes specialized trackers for different concerns:
    - PopulationTracker: births, deaths, generations, algorithm stats
    - LineageTracker: phylogenetic tree data
    - PokerStatsManager: poker game statistics
    - ReproductionStatsManager: reproduction statistics
    - EnergyTracker: energy flow tracking
    - EnhancedStatisticsTracker: time series and correlations
    - GeneticDiversityTracker: genetic diversity statistics
    - EcosystemTelemetryRouter: event/energy-delta ingestion
    - PokerOutcomeRecorder: poker outcome recording

    Attributes:
        max_population: Maximum number of fish allowed (carrying capacity)
    """

    def __init__(
        self,
        max_population: int = 75,
        event_bus: Optional["EventBus"] = None,
    ):
        """Initialize the ecosystem manager.

        Args:
            max_population: Maximum number of fish (carrying capacity)
            event_bus: Optional EventBus for domain event subscriptions
        """
        self.frame_count: int = 0

        # Event logging (simple, kept inline)
        self.events: list[EcosystemEvent] = []
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
        self.diversity = GeneticDiversityTracker()

        # Enhanced statistics tracker (time series, correlations, extinctions)
        from core.enhanced_statistics import EnhancedStatisticsTracker

        self.enhanced_stats: EnhancedStatisticsTracker = EnhancedStatisticsTracker(
            max_history_length=1000
        )

        # Energy tracking
        self.energy_tracker = EnergyTracker()

        # Telemetry routing (EventBus handlers, energy delta ingestion)
        self.telemetry = EcosystemTelemetryRouter(self)

        # Poker outcome recording (stats + energy ledger updates)
        self.poker_recorder = PokerOutcomeRecorder(self)

        # Subscribe to domain events if EventBus is provided
        self.event_bus = event_bus
        if event_bus is not None:
            self._subscribe_to_events(event_bus)

    def _subscribe_to_events(self, event_bus: "EventBus") -> None:
        """Subscribe handlers to domain events on the EventBus."""
        self.telemetry.subscribe(event_bus)

    def _on_food_eaten_event(self, event: "FoodEatenEvent") -> None:
        """Handle food consumption events."""
        self.telemetry.on_food_eaten(event)

    def _on_birth_event(self, event: "BirthEvent") -> None:
        """Handle entity birth events."""
        self.telemetry.on_birth(event)

    def _on_reproduction_event(self, event: "ReproductionEvent") -> None:
        """Handle reproduction events."""
        self.telemetry.on_reproduction(event)

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
    def generation_stats(self) -> dict:
        return self.population.generation_stats

    @property
    def death_causes(self) -> dict[str, int]:
        return self.population.death_causes

    @property
    def algorithm_stats(self) -> dict:
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
    def lineage_log(self) -> list[dict[str, Any]]:
        return self.lineage.lineage_log

    @property
    def poker_stats(self) -> dict[int, PokerStats]:
        return self.poker_manager.poker_stats

    @property
    def reproduction_stats(self):
        return self.reproduction_manager.reproduction_stats

    @property
    def genetic_diversity_stats(self) -> GeneticDiversityStats:
        return self.diversity.stats

    @genetic_diversity_stats.setter
    def genetic_diversity_stats(self, value: GeneticDiversityStats) -> None:
        self.diversity.stats = value

    @property
    def energy_sources(self) -> dict[str, float]:
        return self.energy_tracker.energy_sources

    @property
    def energy_burn(self) -> dict[str, float]:
        return self.energy_tracker.energy_burn

    @property
    def plant_energy_sources(self) -> dict[str, float]:
        return self.energy_tracker.plant_energy_sources

    @property
    def plant_energy_burn(self) -> dict[str, float]:
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

    def cleanup_dead_fish(self, alive_fish_ids: set[int]) -> int:
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

    def get_recent_events(self, count: int = 10) -> list[EcosystemEvent]:
        """Get the most recent events."""
        return self.events[-count:]

    # =========================================================================
    # Telemetry Event Recording (delegate to EcosystemTelemetryRouter)
    # =========================================================================

    def record_event(self, event: Any) -> None:
        """Record a telemetry event emitted by domain entities."""
        self.telemetry.record_event(event)

    def ingest_energy_deltas(self, deltas: list[Any]) -> None:
        """Process a batch of energy deltas from the engine recorder."""
        self.telemetry.ingest_energy_deltas(deltas)

    # =========================================================================
    # Population Recording (delegate to PopulationTracker)
    # =========================================================================

    def record_birth(
        self,
        fish_id: int,
        generation: int,
        parent_ids: list[int] | None = None,
        algorithm_id: int | None = None,
        color: str | None = None,
        algorithm_name: str | None = None,
        tank_name: str | None = None,
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
        algorithm_id: int | None = None,
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

    def update_population_stats(self, fish_list: list["Fish"]) -> None:
        """Update population statistics from current fish list."""
        self.population.update_population_stats(
            fish_list=fish_list,
            enhanced_stats=self.enhanced_stats,
        )
        self._update_genetic_diversity_stats(fish_list)
        self.update_pregnant_count(0)  # No pregnancy in current system

    def _update_genetic_diversity_stats(self, fish_list: list["Fish"]) -> None:
        """Update genetic diversity statistics."""
        self.diversity.update(fish_list)

    # =========================================================================
    # Query Methods (delegate to trackers)
    # =========================================================================

    def get_population_by_generation(self) -> dict[int, int]:
        """Get current population counts by generation."""
        return self.population.get_population_by_generation()

    def get_total_population(self) -> int:
        """Get total population across all generations."""
        return self.population.get_total_population()

    def get_lineage_data(self, alive_fish_ids: set[int] | None = None) -> list[dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization."""
        return self.lineage.get_lineage_data(alive_fish_ids)

    def get_summary_stats(self, entities: list | None = None) -> dict[str, Any]:
        """Get comprehensive ecosystem summary statistics."""
        return ecosystem_reporting.build_summary_stats(self, entities)

    def get_poker_stats_summary(self) -> dict[str, Any]:
        """Get poker statistics summary."""
        return self.poker_manager.get_poker_stats_summary()

    def get_poker_leaderboard(
        self,
        fish_list: list["Fish"] | None = None,
        limit: int = 10,
        sort_by: str = "net_energy",
    ) -> list[dict[str, Any]]:
        """Get poker leaderboard."""
        return self.poker_manager.get_poker_leaderboard(fish_list, sort_by=sort_by, limit=limit)

    def get_reproduction_summary(self) -> dict[str, Any]:
        """Get reproduction statistics summary."""
        return self.reproduction_manager.get_summary()

    def get_diversity_summary(self) -> dict[str, Any]:
        """Get summary genetic diversity statistics."""
        return self.diversity.get_summary()

    def get_enhanced_stats_summary(self) -> dict[str, Any]:
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
    # Food Recording (delegate to EcosystemTelemetryRouter)
    # =========================================================================

    def record_nectar_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record nectar consumption."""
        self.telemetry.record_nectar_eaten(algorithm_id, energy_gained)

    def record_live_food_eaten(
        self,
        algorithm_id: int,
        energy_gained: float = 10.0,
        genome: Optional["Genome"] = None,
        generation: int | None = None,
    ) -> None:
        """Record live food consumption."""
        self.telemetry.record_live_food_eaten(
            algorithm_id, energy_gained, genome=genome, generation=generation
        )

    def record_falling_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record falling food consumption."""
        self.telemetry.record_falling_food_eaten(algorithm_id, energy_gained)

    def record_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record generic food consumption."""
        self.telemetry.record_food_eaten(algorithm_id, energy_gained)

    # =========================================================================
    # Poker Recording (delegate to PokerOutcomeRecorder)
    # =========================================================================

    def record_poker_outcome_record(self, record: PokerOutcomeRecord) -> None:
        """Record a poker game outcome from a value object."""
        self.poker_recorder.record_poker_outcome_record(record)

    def record_plant_poker_game_record(self, record: PlantPokerOutcomeRecord) -> None:
        """Record a plant poker outcome from a value object."""
        self.poker_recorder.record_plant_poker_game_record(record)

    def record_mixed_poker_energy_transfer(
        self,
        energy_to_fish: float,
        is_plant_game: bool = True,
        winner_type: str = "",
    ) -> None:
        """Record energy transfer from a mixed poker game."""
        self.poker_recorder.record_mixed_poker_energy_transfer(
            energy_to_fish, is_plant_game=is_plant_game, winner_type=winner_type
        )

    def record_mixed_poker_outcome_record(self, record: MixedPokerOutcomeRecord) -> None:
        """Record mixed poker outcome with correct per-economy house cut attribution."""
        self.poker_recorder.record_mixed_poker_outcome_record(record)

    def record_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-fish poker."""
        self.poker_recorder.record_poker_energy_gain(amount)

    def record_plant_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-plant poker."""
        self.poker_recorder.record_plant_poker_energy_gain(amount)

    def record_auto_eval_energy_gain(self, amount: float) -> None:
        """Track energy awarded through auto-evaluation benchmarks."""
        self.poker_recorder.record_auto_eval_energy_gain(amount)

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
        self, source: str, delta: float, *, negative_source: str | None = None
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
        self, source: str, delta: float, *, negative_source: str | None = None
    ) -> None:
        """Record a signed plant energy delta."""
        self.energy_tracker.record_plant_energy_delta(
            source, delta, negative_source=negative_source
        )

    def record_plant_energy_transfer(self, source: str, amount: float) -> None:
        """Record a plant internal transfer."""
        self.energy_tracker.record_plant_energy_transfer(source, amount)

    def get_energy_source_summary(self) -> dict[str, float]:
        """Return a snapshot of accumulated energy gains."""
        return self.energy_tracker.get_energy_source_summary()

    def get_plant_energy_source_summary(self) -> dict[str, float]:
        """Return a snapshot of accumulated plant energy gains."""
        return self.energy_tracker.get_plant_energy_source_summary()

    def get_recent_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> dict[str, float]:
        """Get energy source breakdown over recent frames."""
        return self.energy_tracker.get_recent_energy_breakdown(window_frames=window_frames)

    def get_recent_plant_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> dict[str, float]:
        """Get plant energy source breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_breakdown(window_frames=window_frames)

    def get_recent_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> dict[str, float]:
        """Get energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_energy_burn(window_frames=window_frames)

    def get_recent_plant_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> dict[str, float]:
        """Get plant energy consumption breakdown over recent frames."""
        return self.energy_tracker.get_recent_plant_energy_burn(window_frames=window_frames)

    def record_energy_snapshot(self, total_fish_energy: float, fish_count: int) -> None:
        """Record a snapshot of total fish energy."""
        self.energy_tracker.record_energy_snapshot(total_fish_energy, fish_count)

    def get_energy_delta(self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES) -> dict[str, Any]:
        """Calculate the true change in fish population energy over a time window."""
        return self.energy_tracker.get_energy_delta(window_frames=window_frames)

    # =========================================================================
    # Algorithm Performance
    # =========================================================================

    def get_algorithm_performance_report(self, min_sample_size: int = 5) -> str:
        """Get algorithm performance report."""
        from core import algorithm_reporter

        return algorithm_reporter.get_algorithm_performance_report(self, min_sample_size)

    def get_poker_strategy_distribution(self, fish_list: list["Fish"]) -> dict[str, Any]:
        """Get distribution of poker strategies in the population."""
        return ecosystem_reporting.get_poker_strategy_distribution(fish_list)

    def log_poker_evolution_status(self, fish_list: list["Fish"]) -> None:
        """Log current poker evolution status to console."""
        ecosystem_reporting.log_poker_evolution_status(self, fish_list)
