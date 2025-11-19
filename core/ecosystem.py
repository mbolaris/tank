"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.constants import MAX_ECOSYSTEM_EVENTS, TOTAL_ALGORITHM_COUNT, TOTAL_SPECIES_COUNT

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome


@dataclass
class AlgorithmStats:
    """Performance statistics for a behavior algorithm.

    Attributes:
        algorithm_id: Unique identifier for the algorithm (0-47)
        algorithm_name: Human-readable name
        total_births: Total fish born with this algorithm
        total_deaths: Total fish died with this algorithm
        deaths_starvation: Deaths due to starvation
        deaths_old_age: Deaths due to old age
        deaths_predation: Deaths due to predation
        total_reproductions: Number of times fish with this algorithm reproduced
        current_population: Current living fish with this algorithm
        total_lifespan: Sum of lifespans for averaging
        total_food_eaten: Total food items consumed by fish with this algorithm
    """

    algorithm_id: int
    algorithm_name: str = ""
    total_births: int = 0
    total_deaths: int = 0
    deaths_starvation: int = 0
    deaths_old_age: int = 0
    deaths_predation: int = 0
    total_reproductions: int = 0
    current_population: int = 0
    total_lifespan: int = 0
    total_food_eaten: int = 0

    def get_avg_lifespan(self) -> float:
        return self.total_lifespan / self.total_deaths if self.total_deaths > 0 else 0.0

    def get_survival_rate(self) -> float:
        return self.current_population / self.total_births if self.total_births > 0 else 0.0

    def get_reproduction_rate(self) -> float:
        return self.total_reproductions / self.total_births if self.total_births > 0 else 0.0


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
class PokerStats:
    """Poker game statistics for an algorithm.

    Attributes:
        algorithm_id: Unique identifier for the algorithm
        total_games: Total poker games played
        total_wins: Total games won
        total_losses: Total games lost
        total_ties: Total games tied
        total_energy_won: Total energy gained from poker
        total_energy_lost: Total energy lost from poker
        total_house_cuts: Total energy taken by house
        best_hand_rank: Best hand rank achieved (0-9)
        avg_hand_rank: Average hand rank
        folds: Number of times folded
        won_at_showdown: Number of wins at showdown (vs fold)
        won_by_fold: Number of wins because opponent folded
        showdown_count: Number of times reached showdown
        button_wins: Wins when on the button
        button_games: Games played on the button
        off_button_wins: Wins when not on the button
        off_button_games: Games played off the button
        preflop_folds: Folds during pre-flop
        postflop_folds: Folds after seeing flop
        avg_pot_size: Average pot size
        total_raises: Total number of raises made
        total_calls: Total number of calls made
    """

    algorithm_id: int
    total_games: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_ties: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    total_house_cuts: float = 0.0
    best_hand_rank: int = 0
    avg_hand_rank: float = 0.0
    _total_hand_rank: float = field(default=0.0, repr=False)  # For averaging

    # New detailed stats
    folds: int = 0
    won_at_showdown: int = 0
    won_by_fold: int = 0
    showdown_count: int = 0
    button_wins: int = 0
    button_games: int = 0
    off_button_wins: int = 0
    off_button_games: int = 0
    preflop_folds: int = 0
    postflop_folds: int = 0
    avg_pot_size: float = 0.0
    _total_pot_size: float = field(default=0.0, repr=False)
    total_raises: int = 0
    total_calls: int = 0

    def get_win_rate(self) -> float:
        return self.total_wins / self.total_games if self.total_games > 0 else 0.0

    def get_net_energy(self) -> float:
        return self.total_energy_won - self.total_energy_lost - self.total_house_cuts

    def get_showdown_win_rate(self) -> float:
        return self.won_at_showdown / self.showdown_count if self.showdown_count > 0 else 0.0

    def get_fold_rate(self) -> float:
        return self.folds / self.total_games if self.total_games > 0 else 0.0

    def get_button_win_rate(self) -> float:
        return self.button_wins / self.button_games if self.button_games > 0 else 0.0

    def get_off_button_win_rate(self) -> float:
        return self.off_button_wins / self.off_button_games if self.off_button_games > 0 else 0.0

    def get_aggression_factor(self) -> float:
        return self.total_raises / self.total_calls if self.total_calls > 0 else 0.0

    def get_roi(self) -> float:
        return self.get_net_energy() / self.total_games if self.total_games > 0 else 0.0

    def get_vpip(self) -> float:
        """Calculate VPIP (Voluntarily Put money In Pot) percentage.

        VPIP measures how often a player plays a hand (doesn't fold pre-flop).
        Higher VPIP = looser play, Lower VPIP = tighter play.
        """
        return (
            (self.total_games - self.preflop_folds) / self.total_games
            if self.total_games > 0
            else 0.0
        )

    def get_bluff_success_rate(self) -> float:
        """Calculate bluff success rate (wins by fold / total folds by opponent).

        This estimates how often the player successfully bluffs opponents into folding.
        """
        total_fold_opportunities = self.won_by_fold + self.folds
        return self.won_by_fold / total_fold_opportunities if total_fold_opportunities > 0 else 0.0

    def get_positional_advantage(self) -> float:
        """Calculate positional advantage (button win rate - off-button win rate).

        Positive values indicate better performance on the button (as expected).
        Larger positive values suggest good exploitation of position.
        """
        return self.get_button_win_rate() - self.get_off_button_win_rate()

    def get_showdown_percentage(self) -> float:
        """Calculate percentage of games that went to showdown."""
        return self.showdown_count / self.total_games if self.total_games > 0 else 0.0

    def get_postflop_fold_rate(self) -> float:
        """Calculate percentage of folds that occurred post-flop.

        Higher values suggest better pre-flop selection but weaker post-flop play.
        """
        return self.postflop_folds / self.folds if self.folds > 0 else 0.0


@dataclass
class EcosystemEvent:
    """Represents an event in the ecosystem.

    Attributes:
        frame: Frame number when event occurred
        event_type: Type of event ('birth', 'death', 'starvation', 'old_age', 'predation', 'poker')
        fish_id: ID of the fish involved
        details: Additional details about the event
    """

    frame: int
    event_type: str
    fish_id: int
    details: str = ""


@dataclass
class ReproductionStats:
    """Statistics for reproduction dynamics.

    Attributes:
        total_reproductions: Total successful reproductions
        total_mating_attempts: Total mating attempts (successful + failed)
        total_failed_attempts: Total failed mating attempts
        current_pregnant_fish: Current number of pregnant fish
        total_offspring: Total offspring produced
    """

    total_reproductions: int = 0
    total_mating_attempts: int = 0
    total_failed_attempts: int = 0
    current_pregnant_fish: int = 0
    total_offspring: int = 0

    def get_success_rate(self) -> float:
        """Calculate mating success rate."""
        return (
            self.total_reproductions / self.total_mating_attempts
            if self.total_mating_attempts > 0
            else 0.0
        )

    def get_offspring_per_reproduction(self) -> float:
        """Calculate average offspring per reproduction."""
        return (
            self.total_offspring / self.total_reproductions if self.total_reproductions > 0 else 0.0
        )


@dataclass
class GeneticDiversityStats:
    """Statistics for genetic diversity in the population.

    Attributes:
        unique_algorithms: Number of unique behavior algorithms present
        unique_species: Number of unique species present
        color_variance: Variance in color hue (0-1)
        trait_variances: Dict of trait name to variance
        avg_genome_similarity: Average genetic similarity (0-1, optional)
    """

    unique_algorithms: int = 0
    unique_species: int = 0
    color_variance: float = 0.0
    trait_variances: Dict[str, float] = field(default_factory=dict)
    avg_genome_similarity: float = 0.0

    def get_diversity_score(self) -> float:
        """Calculate overall diversity score (0-1, higher is more diverse)."""
        # Combine multiple diversity metrics
        # More algorithms and species = better, higher variance = better
        algo_score = min(self.unique_algorithms / float(TOTAL_ALGORITHM_COUNT), 1.0)
        species_score = min(self.unique_species / float(TOTAL_SPECIES_COUNT), 1.0)
        color_score = min(self.color_variance * 3.0, 1.0)  # Normalize variance

        # Average the scores
        return (algo_score + species_score + color_score) / 3.0


@dataclass
class JellyfishPokerStats:
    """Statistics for a fish's performance against the jellyfish benchmark.

    This tracks how well each fish performs in poker games against the
    non-evolving jellyfish evaluator, providing a standardized benchmark
    for comparing fish poker skills.

    Attributes:
        fish_id: Unique identifier for the fish
        fish_name: Display name for the fish
        total_games: Total games played against jellyfish
        wins: Games won against jellyfish
        losses: Games lost against jellyfish
        total_energy_won: Total energy gained from jellyfish
        total_energy_lost: Total energy lost to jellyfish
        best_hand_rank: Best hand rank achieved (0-9)
        avg_hand_rank: Average hand rank
        wins_by_fold: Wins because jellyfish folded
        losses_by_fold: Losses because fish folded
    """
    fish_id: int
    fish_name: str = ""
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    best_hand_rank: int = 0
    avg_hand_rank: float = 0.0
    _total_hand_rank: float = field(default=0.0, repr=False)
    wins_by_fold: int = 0
    losses_by_fold: int = 0

    def get_win_rate(self) -> float:
        """Calculate win rate against jellyfish."""
        return self.wins / self.total_games if self.total_games > 0 else 0.0

    def get_net_energy(self) -> float:
        """Calculate net energy gained/lost against jellyfish."""
        return self.total_energy_won - self.total_energy_lost

    def get_avg_energy_per_game(self) -> float:
        """Calculate average energy per game."""
        return self.get_net_energy() / self.total_games if self.total_games > 0 else 0.0

    def get_fold_win_rate(self) -> float:
        """Calculate rate of wins by fold (bluffing success)."""
        return self.wins_by_fold / self.wins if self.wins > 0 else 0.0

    def get_score(self) -> float:
        """Calculate overall performance score for leaderboard ranking.

        Combines win rate (60%), net energy (30%), and games played (10%).
        """
        if self.total_games == 0:
            return 0.0

        # Win rate component (0-60 points)
        win_rate_score = self.get_win_rate() * 60.0

        # Net energy component (0-30 points, normalized)
        # Assume typical range is -500 to +500 energy
        net_energy_normalized = max(-1.0, min(1.0, self.get_net_energy() / 500.0))
        energy_score = (net_energy_normalized + 1.0) / 2.0 * 30.0

        # Games played component (0-10 points, more games = more reliable)
        # Cap at 50 games for full points
        games_score = min(self.total_games / 50.0, 1.0) * 10.0

        return win_rate_score + energy_score + games_score


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
        self.poker_stats: Dict[int, PokerStats] = {}
        self._init_poker_stats()

        # Reproduction statistics tracking
        self.reproduction_stats: ReproductionStats = ReproductionStats()

        # Genetic diversity statistics tracking
        self.genetic_diversity_stats: GeneticDiversityStats = GeneticDiversityStats()

        # Jellyfish poker leaderboard tracking
        self.jellyfish_poker_stats: Dict[int, JellyfishPokerStats] = {}

        # NEW: Enhanced statistics tracker (time series, correlations, extinctions, etc.)
        from core.enhanced_statistics import EnhancedStatisticsTracker

        self.enhanced_stats: EnhancedStatisticsTracker = EnhancedStatisticsTracker(
            max_history_length=1000
        )

        # Next available fish ID
        self.next_fish_id: int = 0

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

    def _init_poker_stats(self) -> None:
        """Initialize poker stats for all algorithms including poker variants."""
        # 48 base algorithms + 5 poker-specific = 53 total
        for i in range(TOTAL_ALGORITHM_COUNT + 5):
            self.poker_stats[i] = PokerStats(algorithm_id=i)

    def update(self, frame: int) -> None:
        """Update ecosystem state.

        Args:
            frame: Current frame number
        """
        self.frame_count = frame

        # NEW: Check for algorithm extinctions
        self.enhanced_stats.check_for_extinctions(frame, self)

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
    ) -> None:
        """Record a birth event.

        Args:
            fish_id: ID of the newborn fish
            generation: Generation number
            parent_ids: Optional list of parent IDs
            algorithm_id: Optional algorithm ID (0-47)
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

        # Update algorithm stats
        if algorithm_id is not None and algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_births += 1
            self.algorithm_stats[algorithm_id].current_population += 1

        # NEW: Record offspring birth for energy efficiency tracking
        self.enhanced_stats.record_offspring_birth(energy_cost=0.0)

        # Log event
        details = f"Parents: {parent_ids}" if parent_ids else "Initial spawn"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(
            EcosystemEvent(
                frame=self.frame_count, event_type="birth", fish_id=fish_id, details=details
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
    ) -> None:
        """Record a death event.

        Args:
            fish_id: ID of the fish that died
            generation: Generation of the fish
            age: Age of the fish at death
            cause: Cause of death ('starvation', 'old_age', 'predation', 'unknown')
            genome: Optional genome for statistics
            algorithm_id: Optional algorithm ID (0-47)
            remaining_energy: Energy the fish had when it died (for waste tracking)
        """
        self.total_deaths += 1

        # Update generation stats
        if generation in self.generation_stats:
            stats = self.generation_stats[generation]
            stats.deaths += 1
            stats.population = max(0, stats.population - 1)

            # Update average age at death
            total_fish = stats.deaths
            if total_fish > 0:
                stats.avg_age = (stats.avg_age * (total_fish - 1) + age) / total_fish
            else:
                stats.avg_age = age

        # Track death causes
        self.death_causes[cause] += 1

        # Update algorithm stats
        if algorithm_id is not None and algorithm_id in self.algorithm_stats:
            algo_stats = self.algorithm_stats[algorithm_id]
            algo_stats.total_deaths += 1
            algo_stats.current_population = max(0, algo_stats.current_population - 1)
            algo_stats.total_lifespan += age

            # Track death cause by algorithm
            if cause == "starvation":
                algo_stats.deaths_starvation += 1
            elif cause == "old_age":
                algo_stats.deaths_old_age += 1
            elif cause == "predation":
                algo_stats.deaths_predation += 1

        # NEW: Record trait-fitness correlation sample (before death)
        if genome is not None:
            self.enhanced_stats.record_trait_fitness_sample(genome)

        # NEW: Record energy waste from death
        self.enhanced_stats.record_death_energy_loss(remaining_energy)

        # Log event
        details = f"Age: {age}, Generation: {generation}"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(
            EcosystemEvent(
                frame=self.frame_count, event_type=cause, fish_id=fish_id, details=details
            )
        )

    def update_population_stats(self, fish_list: List["Fish"]) -> None:
        """Update population statistics from current fish.

        Args:
            fish_list: List of all living fish
        """
        if not fish_list:
            return

        # Group by generation
        gen_fish: Dict[int, List[Fish]] = defaultdict(list)
        for fish in fish_list:
            if hasattr(fish, "generation"):
                gen_fish[fish.generation].append(fish)

        # Update stats for each generation
        for generation, fishes in gen_fish.items():
            if generation not in self.generation_stats:
                self.generation_stats[generation] = GenerationStats(generation=generation)

            stats = self.generation_stats[generation]
            stats.population = len(fishes)

            # Calculate averages
            if fishes:
                fishes_with_genome = [f for f in fishes if hasattr(f, "genome")]
                if fishes_with_genome:
                    stats.avg_speed = sum(
                        f.genome.speed_modifier for f in fishes_with_genome
                    ) / len(fishes)
                    stats.avg_size = sum(f.genome.size_modifier for f in fishes_with_genome) / len(
                        fishes
                    )
                    stats.avg_energy = sum(f.genome.max_energy for f in fishes_with_genome) / len(
                        fishes
                    )

        # Update genetic diversity stats
        self.update_genetic_diversity_stats(fish_list)

        # Update pregnant fish count
        pregnant_count = sum(
            1
            for fish in fish_list
            if hasattr(fish, "reproduction") and fish.reproduction.is_pregnant
        )
        self.update_pregnant_count(pregnant_count)

        # NEW: Record time series snapshot for enhanced statistics
        # (Record every 10 frames to reduce overhead)
        if self.frame_count % 10 == 0:
            self.enhanced_stats.record_frame_snapshot(
                frame=self.frame_count,
                fish_list=fish_list,
                births_this_frame=0,  # Will be updated separately
                deaths_this_frame=0,
            )

    def update_genetic_diversity_stats(self, fish_list: List["Fish"]) -> None:
        """Calculate and update genetic diversity statistics.

        Args:
            fish_list: List of all living fish
        """
        if not fish_list:
            self.genetic_diversity_stats = GeneticDiversityStats()
            return

        # Import here to avoid circular dependency
        try:
            from core.algorithms import get_algorithm_index
        except ImportError:
            get_algorithm_index = None

        # Count unique algorithms
        algorithms = set()
        species = set()
        color_hues = []
        speed_modifiers = []
        size_modifiers = []
        vision_ranges = []

        for fish in fish_list:
            # Count algorithms (using get_algorithm_index to get the index)
            if (
                hasattr(fish, "genome")
                and hasattr(fish.genome, "behavior_algorithm")
                and get_algorithm_index is not None
            ):
                algo_idx = get_algorithm_index(fish.genome.behavior_algorithm)
                if algo_idx >= 0:
                    algorithms.add(algo_idx)

            # Count species
            if hasattr(fish, "species"):
                species.add(fish.species)

            # Collect trait values
            if hasattr(fish, "genome"):
                if hasattr(fish.genome, "color_hue"):
                    color_hues.append(fish.genome.color_hue)
                if hasattr(fish.genome, "speed_modifier"):
                    speed_modifiers.append(fish.genome.speed_modifier)
                if hasattr(fish.genome, "size_modifier"):
                    size_modifiers.append(fish.genome.size_modifier)
                if hasattr(fish.genome, "vision_range"):
                    vision_ranges.append(fish.genome.vision_range)

        # Calculate variance for color (0-1 scale)
        color_variance = 0.0
        if len(color_hues) > 1:
            mean_color = sum(color_hues) / len(color_hues)
            color_variance = sum((h - mean_color) ** 2 for h in color_hues) / len(color_hues)

        # Calculate trait variances
        trait_variances = {}
        if len(speed_modifiers) > 1:
            mean_speed = sum(speed_modifiers) / len(speed_modifiers)
            trait_variances["speed"] = sum((s - mean_speed) ** 2 for s in speed_modifiers) / len(
                speed_modifiers
            )

        if len(size_modifiers) > 1:
            mean_size = sum(size_modifiers) / len(size_modifiers)
            trait_variances["size"] = sum((s - mean_size) ** 2 for s in size_modifiers) / len(
                size_modifiers
            )

        if len(vision_ranges) > 1:
            mean_vision = sum(vision_ranges) / len(vision_ranges)
            trait_variances["vision"] = sum((v - mean_vision) ** 2 for v in vision_ranges) / len(
                vision_ranges
            )

        # Update diversity stats
        self.genetic_diversity_stats.unique_algorithms = len(algorithms)
        self.genetic_diversity_stats.unique_species = len(species)
        self.genetic_diversity_stats.color_variance = color_variance
        self.genetic_diversity_stats.trait_variances = trait_variances

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
        """Get current population count by generation.

        Returns:
            Dictionary mapping generation number to population count
        """
        return {
            gen: stats.population
            for gen, stats in self.generation_stats.items()
            if stats.population > 0
        }

    def get_total_population(self) -> int:
        """Get total current population across all generations.

        Returns:
            Total number of living fish
        """
        return sum(stats.population for stats in self.generation_stats.values())

    def get_summary_stats(self, entities: Optional[List] = None) -> Dict[str, Any]:
        """Get summary statistics for the ecosystem.

        Args:
            entities: Optional list of entities to calculate total energy from

        Returns:
            Dictionary with key ecosystem metrics
        """
        total_pop = self.get_total_population()
        poker_summary = self.get_poker_stats_summary()

        # Calculate total energy if entities provided
        total_energy = 0.0
        if entities is not None:
            from core.entities import Fish

            total_energy = sum(e.energy for e in entities if isinstance(e, Fish))

        return {
            "total_population": total_pop,
            "current_generation": self.current_generation,
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "carrying_capacity": self.max_population,
            "capacity_usage": (
                f"{int(100 * total_pop / self.max_population)}%"
                if self.max_population > 0
                else "0%"
            ),
            "death_causes": dict(self.death_causes),
            "generations_alive": len(
                [g for g, s in self.generation_stats.items() if s.population > 0]
            ),
            "poker_stats": poker_summary,
            "total_energy": total_energy,
            "reproduction_stats": self.get_reproduction_summary(),
            "diversity_stats": self.get_diversity_summary(),
        }

    def get_poker_stats_summary(self) -> Dict[str, Any]:
        """Get summary poker statistics across all algorithms.

        Returns:
            Dictionary with aggregated poker statistics
        """
        total_games = sum(s.total_games for s in self.poker_stats.values())
        total_wins = sum(s.total_wins for s in self.poker_stats.values())
        total_losses = sum(s.total_losses for s in self.poker_stats.values())
        total_ties = sum(s.total_ties for s in self.poker_stats.values())
        total_energy_won = sum(s.total_energy_won for s in self.poker_stats.values())
        total_energy_lost = sum(s.total_energy_lost for s in self.poker_stats.values())
        total_house_cuts = sum(s.total_house_cuts for s in self.poker_stats.values())
        total_folds = sum(s.folds for s in self.poker_stats.values())
        total_showdowns = sum(s.showdown_count for s in self.poker_stats.values())
        total_won_at_showdown = sum(s.won_at_showdown for s in self.poker_stats.values())
        total_won_by_fold = sum(s.won_by_fold for s in self.poker_stats.values())

        # Find best hand rank across all algorithms
        best_hand_rank = max((s.best_hand_rank for s in self.poker_stats.values()), default=0)

        # Get hand rank name
        hand_rank_names = [
            "High Card",
            "Pair",
            "Two Pair",
            "Three of a Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four of a Kind",
            "Straight Flush",
            "Royal Flush",
        ]
        if 0 <= best_hand_rank < len(hand_rank_names):
            best_hand_name = hand_rank_names[best_hand_rank]
        else:
            best_hand_name = "Unknown"

        # Calculate aggregate stats
        avg_fold_rate = (total_folds / total_games) if total_games > 0 else 0.0
        showdown_win_rate = (
            (total_won_at_showdown / total_showdowns) if total_showdowns > 0 else 0.0
        )
        net_energy = total_energy_won - total_energy_lost - total_house_cuts

        # Advanced metrics
        win_rate = (total_wins / total_games) if total_games > 0 else 0.0
        roi = (net_energy / total_games) if total_games > 0 else 0.0

        # VPIP calculation (aggregate across all algorithms)
        total_preflop_folds = sum(s.preflop_folds for s in self.poker_stats.values())
        vpip = ((total_games - total_preflop_folds) / total_games) if total_games > 0 else 0.0

        # Bluff success rate
        total_fold_opportunities = total_won_by_fold + total_folds
        bluff_success_rate = (
            (total_won_by_fold / total_fold_opportunities) if total_fold_opportunities > 0 else 0.0
        )

        # Positional stats
        total_button_wins = sum(s.button_wins for s in self.poker_stats.values())
        total_button_games = sum(s.button_games for s in self.poker_stats.values())
        total_off_button_wins = sum(s.off_button_wins for s in self.poker_stats.values())
        total_off_button_games = sum(s.off_button_games for s in self.poker_stats.values())
        button_win_rate = (
            (total_button_wins / total_button_games) if total_button_games > 0 else 0.0
        )
        off_button_win_rate = (
            (total_off_button_wins / total_off_button_games) if total_off_button_games > 0 else 0.0
        )
        positional_advantage = button_win_rate - off_button_win_rate

        # Aggression factor
        total_raises = sum(s.total_raises for s in self.poker_stats.values())
        total_calls = sum(s.total_calls for s in self.poker_stats.values())
        aggression_factor = (total_raises / total_calls) if total_calls > 0 else 0.0

        # Average hand rank
        avg_hand_rank = sum(s.avg_hand_rank for s in self.poker_stats.values() if s.total_games > 0)
        num_active_algorithms = len([s for s in self.poker_stats.values() if s.total_games > 0])
        avg_hand_rank = (
            (avg_hand_rank / num_active_algorithms) if num_active_algorithms > 0 else 0.0
        )

        return {
            "total_games": total_games,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_ties": total_ties,
            "total_energy_won": total_energy_won,
            "total_energy_lost": total_energy_lost,
            "total_house_cuts": total_house_cuts,
            "net_energy": net_energy,
            "best_hand_rank": best_hand_rank,
            "best_hand_name": best_hand_name,
            "total_folds": total_folds,
            "avg_fold_rate": f"{avg_fold_rate:.1%}",
            "total_showdowns": total_showdowns,
            "showdown_win_rate": f"{showdown_win_rate:.1%}",
            "won_by_fold": total_won_by_fold,
            "won_at_showdown": total_won_at_showdown,
            # Advanced metrics for evaluating poker skill improvement
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate:.1%}",
            "roi": roi,
            "vpip": vpip,
            "vpip_pct": f"{vpip:.1%}",
            "bluff_success_rate": bluff_success_rate,
            "bluff_success_pct": f"{bluff_success_rate:.1%}",
            "button_win_rate": button_win_rate,
            "button_win_rate_pct": f"{button_win_rate:.1%}",
            "off_button_win_rate": off_button_win_rate,
            "off_button_win_rate_pct": f"{off_button_win_rate:.1%}",
            "positional_advantage": positional_advantage,
            "positional_advantage_pct": f"{positional_advantage:.1%}",
            "aggression_factor": aggression_factor,
            "avg_hand_rank": avg_hand_rank,
            "preflop_folds": total_preflop_folds,
            "postflop_folds": total_folds - total_preflop_folds,
        }

    def get_poker_leaderboard(
        self, fish_list: Optional[List] = None, limit: int = 10, sort_by: str = "net_energy"
    ) -> List[Dict[str, Any]]:
        """Get poker leaderboard of top-performing fish.

        Args:
            fish_list: List of fish to include (if None, uses all tracked fish)
            limit: Maximum number of fish to return (default 10)
            sort_by: Metric to sort by (options: 'net_energy', 'wins', 'win_rate', 'roi')

        Returns:
            List of dictionaries with fish poker stats, sorted by the specified metric
        """
        from core.entities import Fish

        if fish_list is None:
            return []

        # Filter to only fish with poker games played
        poker_fish = [f for f in fish_list if isinstance(f, Fish) and f.poker_stats.total_games > 0]

        # Sort by the requested metric
        if sort_by == "net_energy":
            poker_fish.sort(key=lambda f: f.poker_stats.get_net_energy(), reverse=True)
        elif sort_by == "wins":
            poker_fish.sort(key=lambda f: f.poker_stats.wins, reverse=True)
        elif sort_by == "win_rate":
            poker_fish.sort(key=lambda f: f.poker_stats.get_win_rate(), reverse=True)
        elif sort_by == "roi":
            poker_fish.sort(key=lambda f: f.poker_stats.get_roi(), reverse=True)
        else:
            # Default to net energy
            poker_fish.sort(key=lambda f: f.poker_stats.get_net_energy(), reverse=True)

        # Get hand rank names for display
        hand_rank_names = [
            "High Card",
            "Pair",
            "Two Pair",
            "Three of a Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four of a Kind",
            "Straight Flush",
            "Royal Flush",
        ]

        # Build leaderboard data
        leaderboard = []
        for rank, fish in enumerate(poker_fish[:limit], start=1):
            stats = fish.poker_stats
            best_hand_name = (
                hand_rank_names[stats.best_hand_rank]
                if 0 <= stats.best_hand_rank < len(hand_rank_names)
                else "Unknown"
            )

            # Get algorithm name if available
            algo_name = "Unknown"
            if fish.genome.behavior_algorithm is not None:
                from core.algorithms import get_algorithm_name

                # Handle both int indices and algorithm objects
                if isinstance(fish.genome.behavior_algorithm, int):
                    algo_name = get_algorithm_name(fish.genome.behavior_algorithm)
                else:
                    # It's an algorithm object, get its class name
                    algo_name = fish.genome.behavior_algorithm.__class__.__name__

            leaderboard.append(
                {
                    "rank": rank,
                    "fish_id": fish.fish_id,
                    "generation": fish.generation,
                    "algorithm": algo_name,
                    "energy": round(fish.energy, 1),
                    "age": fish.age,
                    "total_games": stats.total_games,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "ties": stats.ties,
                    "win_rate": round(stats.get_win_rate() * 100, 1),
                    "net_energy": round(stats.get_net_energy(), 1),
                    "roi": round(stats.get_roi(), 2),
                    "current_streak": stats.current_streak,
                    "best_streak": stats.best_streak,
                    "best_hand": best_hand_name,
                    "best_hand_rank": stats.best_hand_rank,
                    "showdown_win_rate": round(stats.get_showdown_win_rate() * 100, 1),
                    "fold_rate": round(stats.get_fold_rate() * 100, 1),
                    "positional_advantage": round(stats.get_positional_advantage() * 100, 1),
                }
            )

        return leaderboard

    def get_reproduction_summary(self) -> Dict[str, Any]:
        """Get summary reproduction statistics.

        Returns:
            Dictionary with reproduction metrics
        """
        return {
            "total_reproductions": self.reproduction_stats.total_reproductions,
            "total_mating_attempts": self.reproduction_stats.total_mating_attempts,
            "total_failed_attempts": self.reproduction_stats.total_failed_attempts,
            "success_rate": self.reproduction_stats.get_success_rate(),
            "success_rate_pct": f"{self.reproduction_stats.get_success_rate():.1%}",
            "current_pregnant_fish": self.reproduction_stats.current_pregnant_fish,
            "total_offspring": self.reproduction_stats.total_offspring,
            "offspring_per_reproduction": self.reproduction_stats.get_offspring_per_reproduction(),
        }

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
        """Record a successful reproduction by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the reproducing fish
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_reproductions += 1

        # Track overall reproduction stats
        self.reproduction_stats.total_reproductions += 1
        self.reproduction_stats.total_offspring += 1  # Assume 1 offspring per reproduction

    def record_mating_attempt(self, success: bool) -> None:
        """Record a mating attempt (successful or failed).

        Args:
            success: Whether the mating attempt was successful
        """
        self.reproduction_stats.total_mating_attempts += 1
        if not success:
            self.reproduction_stats.total_failed_attempts += 1

    def update_pregnant_count(self, count: int) -> None:
        """Update the count of currently pregnant fish.

        Args:
            count: Current number of pregnant fish
        """
        self.reproduction_stats.current_pregnant_fish = count

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
        """Record a poker game outcome with detailed statistics.

        Args:
            winner_id: Fish ID of winner (-1 for tie)
            loser_id: Fish ID of loser (-1 for tie)
            winner_algo_id: Algorithm ID of winner (None if no algorithm)
            loser_algo_id: Algorithm ID of loser (None if no algorithm)
            amount: Amount of energy transferred (after house cut)
            winner_hand: The winning poker hand
            loser_hand: The losing poker hand
            house_cut: Amount taken by house (default 0.0)
            result: Optional PokerResult with detailed game information
            player1_algo_id: Algorithm ID of player 1
            player2_algo_id: Algorithm ID of player 2
        """
        from core.poker_interaction import BettingAction

        # Handle tie case
        if winner_id == -1:
            if winner_algo_id is not None and winner_algo_id in self.poker_stats:
                self.poker_stats[winner_algo_id].total_games += 1
                self.poker_stats[winner_algo_id].total_ties += 1
                if winner_hand is not None:
                    self.poker_stats[winner_algo_id]._total_hand_rank += winner_hand.rank_value
                    self.poker_stats[winner_algo_id].avg_hand_rank = (
                        self.poker_stats[winner_algo_id]._total_hand_rank
                        / self.poker_stats[winner_algo_id].total_games
                    )
            if loser_algo_id is not None and loser_algo_id in self.poker_stats:
                self.poker_stats[loser_algo_id].total_games += 1
                self.poker_stats[loser_algo_id].total_ties += 1
                if loser_hand is not None:
                    self.poker_stats[loser_algo_id]._total_hand_rank += loser_hand.rank_value
                    self.poker_stats[loser_algo_id].avg_hand_rank = (
                        self.poker_stats[loser_algo_id]._total_hand_rank
                        / self.poker_stats[loser_algo_id].total_games
                    )
            return

        # Record winner stats
        if winner_algo_id is not None and winner_algo_id in self.poker_stats:
            stats = self.poker_stats[winner_algo_id]
            stats.total_games += 1
            stats.total_wins += 1
            stats.total_energy_won += amount
            stats.total_house_cuts += house_cut / 2  # Split house cut evenly between both players
            if winner_hand is not None:
                stats.best_hand_rank = max(stats.best_hand_rank, winner_hand.rank_value)
                stats._total_hand_rank += winner_hand.rank_value
                stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

            # Track detailed stats if result available
            if result is not None:
                # Update pot size average
                stats._total_pot_size += result.final_pot
                stats.avg_pot_size = stats._total_pot_size / stats.total_games

                # Track win by fold vs showdown
                if result.won_by_fold:
                    stats.won_by_fold += 1
                else:
                    stats.won_at_showdown += 1
                    stats.showdown_count += 1

                # Track positional stats (winner perspective)
                winner_on_button = (
                    winner_id == result.winner_id and result.button_position == 1
                ) or (winner_id != result.winner_id and result.button_position == 2)
                if winner_algo_id == player1_algo_id:
                    winner_on_button = result.button_position == 1
                else:
                    winner_on_button = result.button_position == 2

                if winner_on_button:
                    stats.button_games += 1
                    stats.button_wins += 1
                else:
                    stats.off_button_games += 1
                    stats.off_button_wins += 1

                # Count betting actions for aggression factor
                for player, action, _ in result.betting_history:
                    # Determine if this action was by the winner
                    if (player == 1 and winner_algo_id == player1_algo_id) or (
                        player == 2 and winner_algo_id == player2_algo_id
                    ):
                        if action == BettingAction.RAISE:
                            stats.total_raises += 1
                        elif action == BettingAction.CALL:
                            stats.total_calls += 1

        # Record loser stats
        if loser_algo_id is not None and loser_algo_id in self.poker_stats:
            stats = self.poker_stats[loser_algo_id]
            stats.total_games += 1
            stats.total_losses += 1
            stats.total_energy_lost += amount
            stats.total_house_cuts += house_cut / 2  # Split house cut evenly between both players
            if loser_hand is not None:
                stats._total_hand_rank += loser_hand.rank_value
                stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

            # Track detailed stats if result available
            if result is not None:
                # Update pot size average
                stats._total_pot_size += result.final_pot
                stats.avg_pot_size = stats._total_pot_size / stats.total_games

                # Track fold stats
                loser_folded = (loser_algo_id == player1_algo_id and result.player1_folded) or (
                    loser_algo_id == player2_algo_id and result.player2_folded
                )
                if loser_folded:
                    stats.folds += 1
                    # Track pre-flop vs post-flop folds
                    if result.total_rounds == 0:
                        stats.preflop_folds += 1
                    else:
                        stats.postflop_folds += 1
                else:
                    # Lost at showdown
                    stats.showdown_count += 1

                # Track positional stats (loser perspective)
                loser_on_button = (
                    loser_algo_id == player1_algo_id and result.button_position == 1
                ) or (loser_algo_id == player2_algo_id and result.button_position == 2)
                if loser_on_button:
                    stats.button_games += 1
                else:
                    stats.off_button_games += 1

                # Count betting actions for aggression factor
                for player, action, _ in result.betting_history:
                    # Determine if this action was by the loser
                    if (player == 1 and loser_algo_id == player1_algo_id) or (
                        player == 2 and loser_algo_id == player2_algo_id
                    ):
                        if action == BettingAction.RAISE:
                            stats.total_raises += 1
                        elif action == BettingAction.CALL:
                            stats.total_calls += 1

        # Log event
        winner_desc = winner_hand.description if winner_hand is not None else "Unknown"
        loser_desc = loser_hand.description if loser_hand is not None else "Unknown"
        self.events.append(
            EcosystemEvent(
                frame=self.frame_count,
                event_type="poker",
                fish_id=winner_id,
                details=(
                    f"Won {amount:.1f} energy from fish {loser_id} "
                    f"({winner_desc} vs {loser_desc})"
                ),
            )
        )

    def _get_report_header(self) -> List[str]:
        """Generate the report header section."""
        return [
            "=" * 80,
            "ALGORITHM PERFORMANCE REPORT",
            "=" * 80,
            "",
            f"Total Simulation Time: {self.frame_count} frames",
            f"Total Population Births: {self.total_births}",
            f"Total Population Deaths: {self.total_deaths}",
            f"Current Generation: {self.current_generation}",
            "",
        ]

    def _get_top_performers_section(
        self, algorithms_with_data: List[Tuple[int, "AlgorithmStats"]]
    ) -> List[str]:
        """Generate top performing algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data, key=lambda x: x[1].get_reproduction_rate(), reverse=True
        )

        lines = ["-" * 80, "TOP PERFORMING ALGORITHMS (by reproduction rate)", "-" * 80, ""]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            lines.extend(
                [
                    f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                    f"  Births: {stats.total_births}",
                    f"  Deaths: {stats.total_deaths}",
                    f"  Current Population: {stats.current_population}",
                    f"  Reproductions: {stats.total_reproductions}",
                    f"  Reproduction Rate: {stats.get_reproduction_rate():.2%}",
                    f"  Survival Rate: {stats.get_survival_rate():.2%}",
                    f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                    f"  Food Eaten: {stats.total_food_eaten}",
                    f"  Deaths - Starvation: {stats.deaths_starvation}, "
                    f"Old Age: {stats.deaths_old_age}, Predation: {stats.deaths_predation}",
                    "",
                ]
            )

        return lines

    def _get_survival_section(
        self, algorithms_with_data: List[Tuple[int, "AlgorithmStats"]]
    ) -> List[str]:
        """Generate top surviving algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data, key=lambda x: x[1].get_survival_rate(), reverse=True
        )

        lines = ["-" * 80, "TOP SURVIVING ALGORITHMS (by current survival rate)", "-" * 80, ""]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            lines.extend(
                [
                    f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                    f"  Survival Rate: {stats.get_survival_rate():.2%}",
                    f"  Current Population: {stats.current_population}",
                    f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                    "",
                ]
            )

        return lines

    def _get_longevity_section(
        self, algorithms_with_data: List[Tuple[int, "AlgorithmStats"]]
    ) -> List[str]:
        """Generate longest-lived algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data, key=lambda x: x[1].get_avg_lifespan(), reverse=True
        )

        lines = ["-" * 80, "LONGEST-LIVED ALGORITHMS (by average lifespan)", "-" * 80, ""]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            starvation_pct = (
                stats.deaths_starvation / stats.total_deaths * 100 if stats.total_deaths > 0 else 0
            )
            lines.extend(
                [
                    f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                    f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                    f"  Deaths: {stats.total_deaths}",
                    f"  Starvation Deaths: {stats.deaths_starvation} ({starvation_pct:.1f}%)",
                    "",
                ]
            )

        return lines

    def _get_worst_performers_section(self, min_sample_size: int) -> List[str]:
        """Generate worst performing algorithms section."""
        algorithms_with_deaths = [
            (algo_id, stats)
            for algo_id, stats in self.algorithm_stats.items()
            if stats.total_deaths >= min_sample_size
        ]
        algorithms_with_deaths.sort(
            key=lambda x: (
                x[1].deaths_starvation / x[1].total_deaths if x[1].total_deaths > 0 else 0
            ),
            reverse=True,
        )

        lines = ["-" * 80, "WORST PERFORMERS (highest starvation rate)", "-" * 80, ""]

        for i, (algo_id, stats) in enumerate(algorithms_with_deaths[:10], 1):
            starvation_rate = (
                stats.deaths_starvation / stats.total_deaths if stats.total_deaths > 0 else 0
            )
            lines.extend(
                [
                    f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                    f"  Starvation Rate: {starvation_rate:.2%}",
                    f"  Deaths: {stats.total_deaths}",
                    f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                    f"  Reproduction Rate: {stats.get_reproduction_rate():.2%}",
                    "",
                ]
            )

        return lines

    def _get_recommendations_section(
        self, algorithms_with_data: List[Tuple[int, "AlgorithmStats"]]
    ) -> List[str]:
        """Generate recommendations section based on performance data."""
        lines = ["-" * 80, "RECOMMENDATIONS FOR NEXT GENERATION", "-" * 80, ""]

        # Best performer recommendation
        if algorithms_with_data:
            best_algo_id, best_stats = algorithms_with_data[0]
            lines.extend(
                [
                    f"1. The most successful algorithm is '{best_stats.algorithm_name}'",
                    f"   with a reproduction rate of {best_stats.get_reproduction_rate():.2%}.",
                    "",
                ]
            )

        # Worst performer warning
        algorithms_by_starvation = sorted(
            [(aid, s) for aid, s in self.algorithm_stats.items() if s.total_deaths > 0],
            key=lambda x: (
                x[1].deaths_starvation / x[1].total_deaths if x[1].total_deaths > 0 else 0
            ),
            reverse=True,
        )

        if algorithms_by_starvation:
            worst_algo_id, worst_stats = algorithms_by_starvation[0]
            starvation_rate = (
                worst_stats.deaths_starvation / worst_stats.total_deaths
                if worst_stats.total_deaths > 0
                else 0
            )
            lines.extend(
                [
                    f"2. The algorithm '{worst_stats.algorithm_name}' has the highest starvation rate",
                    f"   at {starvation_rate:.2%}, indicating poor food-seeking behavior.",
                    "",
                ]
            )

        # Overall metrics
        total_starvation = sum(s.deaths_starvation for s in self.algorithm_stats.values())
        total_deaths_all = sum(s.total_deaths for s in self.algorithm_stats.values())
        if total_deaths_all > 0:
            overall_starvation_rate = total_starvation / total_deaths_all
            lines.append(f"3. Overall starvation rate: {overall_starvation_rate:.2%}")
            if overall_starvation_rate > 0.5:
                lines.extend(
                    [
                        "   RECOMMENDATION: High starvation indicates resource scarcity.",
                        "   Focus on food-seeking and energy conservation algorithms.",
                    ]
                )
            lines.append("")

        return lines

    def get_algorithm_performance_report(self, min_sample_size: int = 5) -> str:
        """Generate a comprehensive performance report for all algorithms.

        This report is designed to be used as a prompt for AI to generate
        next-generation algorithms based on performance data.

        Args:
            min_sample_size: Minimum number of births to include algorithm in analysis

        Returns:
            Formatted text report with algorithm performance metrics
        """
        # Filter algorithms with sufficient data
        algorithms_with_data = [
            (algo_id, stats)
            for algo_id, stats in self.algorithm_stats.items()
            if stats.total_births >= min_sample_size
        ]

        # Sort by reproduction rate for recommendations
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate(), reverse=True)

        # Build report from sections
        report_lines = []
        report_lines.extend(self._get_report_header())
        report_lines.extend(self._get_top_performers_section(algorithms_with_data))
        report_lines.extend(self._get_survival_section(algorithms_with_data))
        report_lines.extend(self._get_longevity_section(algorithms_with_data))
        report_lines.extend(self._get_worst_performers_section(min_sample_size))
        report_lines.extend(self._get_recommendations_section(algorithms_with_data))
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def record_jellyfish_poker_game(self, fish_id: int, fish_won: bool,
                                   energy_transferred: float, fish_hand_rank: int,
                                   won_by_fold: bool) -> None:
        """Record a poker game between a fish and the jellyfish benchmark.

        Args:
            fish_id: ID of the fish that played
            fish_won: True if fish won, False if jellyfish won
            energy_transferred: Amount of energy won or lost
            fish_hand_rank: Rank of the fish's hand (0-9)
            won_by_fold: True if game ended by fold
        """
        # Initialize stats for this fish if not exists
        if fish_id not in self.jellyfish_poker_stats:
            self.jellyfish_poker_stats[fish_id] = JellyfishPokerStats(
                fish_id=fish_id,
                fish_name=f"Fish #{fish_id}"
            )

        stats = self.jellyfish_poker_stats[fish_id]
        stats.total_games += 1

        if fish_won:
            stats.wins += 1
            stats.total_energy_won += energy_transferred
            if won_by_fold:
                stats.wins_by_fold += 1
        else:
            stats.losses += 1
            stats.total_energy_lost += energy_transferred
            if won_by_fold:
                stats.losses_by_fold += 1

        # Update hand rank stats
        stats.best_hand_rank = max(stats.best_hand_rank, fish_hand_rank)
        stats._total_hand_rank += fish_hand_rank
        stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

    def get_jellyfish_leaderboard(self, limit: int = 10) -> List[JellyfishPokerStats]:
        """Get the jellyfish poker leaderboard sorted by performance score.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of JellyfishPokerStats sorted by score (highest first)
        """
        # Filter out fish with no games
        stats_with_games = [
            stats for stats in self.jellyfish_poker_stats.values()
            if stats.total_games > 0
        ]

        # Sort by score (highest first)
        stats_with_games.sort(key=lambda s: s.get_score(), reverse=True)

        # Return top N
        return stats_with_games[:limit]

    def get_jellyfish_poker_stats_for_fish(self, fish_id: int) -> Optional[JellyfishPokerStats]:
        """Get jellyfish poker stats for a specific fish.

        Args:
            fish_id: ID of the fish

        Returns:
            JellyfishPokerStats or None if fish hasn't played
        """
        return self.jellyfish_poker_stats.get(fish_id)
