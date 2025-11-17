"""Ecosystem management and statistics tracking.

This module manages population dynamics, statistics, and ecosystem health.
"""

from typing import Dict, List, Optional, TYPE_CHECKING, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json

if TYPE_CHECKING:
    from agents import Fish


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
        """Calculate average lifespan."""
        return self.total_lifespan / self.total_deaths if self.total_deaths > 0 else 0.0

    def get_survival_rate(self) -> float:
        """Calculate survival rate (still alive / total born)."""
        return self.current_population / self.total_births if self.total_births > 0 else 0.0

    def get_reproduction_rate(self) -> float:
        """Calculate reproduction success rate."""
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

    def get_win_rate(self) -> float:
        """Calculate win rate."""
        return self.total_wins / self.total_games if self.total_games > 0 else 0.0

    def get_net_energy(self) -> float:
        """Calculate net energy from poker."""
        return self.total_energy_won - self.total_energy_lost


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

        # Algorithm performance tracking (48 algorithms, indexed 0-47)
        self.algorithm_stats: Dict[int, AlgorithmStats] = {}
        self._init_algorithm_stats()

        # Poker statistics tracking
        self.poker_stats: Dict[int, PokerStats] = {}
        self._init_poker_stats()

        # Next available fish ID
        self.next_fish_id: int = 0

    def _init_algorithm_stats(self) -> None:
        """Initialize algorithm stats for all 48 algorithms."""
        # Import here to avoid circular dependency
        try:
            from core.behavior_algorithms import ALL_ALGORITHMS
            for i, algo_class in enumerate(ALL_ALGORITHMS):
                # Get algorithm name from class
                algo_name = algo_class.__name__
                self.algorithm_stats[i] = AlgorithmStats(
                    algorithm_id=i,
                    algorithm_name=algo_name
                )
        except ImportError:
            # If behavior_algorithms not available, just initialize empty
            for i in range(48):
                self.algorithm_stats[i] = AlgorithmStats(
                    algorithm_id=i,
                    algorithm_name=f"Algorithm_{i}"
                )

    def _init_poker_stats(self) -> None:
        """Initialize poker stats for all 53 algorithms (48 original + 5 poker)."""
        for i in range(53):
            self.poker_stats[i] = PokerStats(algorithm_id=i)

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

    def record_birth(self, fish_id: int, generation: int, parent_ids: Optional[List[int]] = None,
                     algorithm_id: Optional[int] = None) -> None:
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

        # Log event
        details = f"Parents: {parent_ids}" if parent_ids else "Initial spawn"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(EcosystemEvent(
            frame=self.frame_count,
            event_type='birth',
            fish_id=fish_id,
            details=details
        ))

    def record_death(self, fish_id: int, generation: int, age: int,
                     cause: str = 'unknown', genome: Optional['genetics.Genome'] = None,
                     algorithm_id: Optional[int] = None) -> None:
        """Record a death event.

        Args:
            fish_id: ID of the fish that died
            generation: Generation of the fish
            age: Age of the fish at death
            cause: Cause of death ('starvation', 'old_age', 'predation', 'unknown')
            genome: Optional genome for statistics
            algorithm_id: Optional algorithm ID (0-47)
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
            if cause == 'starvation':
                algo_stats.deaths_starvation += 1
            elif cause == 'old_age':
                algo_stats.deaths_old_age += 1
            elif cause == 'predation':
                algo_stats.deaths_predation += 1

        # Log event
        details = f"Age: {age}, Generation: {generation}"
        if algorithm_id is not None:
            details += f", Algorithm: {algorithm_id}"
        self._add_event(EcosystemEvent(
            frame=self.frame_count,
            event_type=cause,
            fish_id=fish_id,
            details=details
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
                fishes_with_genome = [f for f in fishes if hasattr(f, 'genome')]
                if fishes_with_genome:
                    stats.avg_speed = (
                        sum(f.genome.speed_modifier for f in fishes_with_genome) / len(fishes)
                    )
                    stats.avg_size = (
                        sum(f.genome.size_modifier for f in fishes_with_genome) / len(fishes)
                    )
                    stats.avg_energy = (
                        sum(f.genome.max_energy for f in fishes_with_genome) / len(fishes)
                    )

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
        poker_summary = self.get_poker_stats_summary()

        return {
            'total_population': total_pop,
            'current_generation': self.current_generation,
            'total_births': self.total_births,
            'total_deaths': self.total_deaths,
            'carrying_capacity': self.max_population,
            'capacity_usage': (
                f"{int(100 * total_pop / self.max_population)}%"
                if self.max_population > 0 else "0%"
            ),
            'death_causes': dict(self.death_causes),
            'generations_alive': len([g for g, s in self.generation_stats.items() if s.population > 0]),
            'poker_stats': poker_summary,
        }

    def get_poker_stats_summary(self) -> Dict[str, any]:
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

        # Find best hand rank across all algorithms
        best_hand_rank = max((s.best_hand_rank for s in self.poker_stats.values()), default=0)

        # Get hand rank name
        hand_rank_names = [
            "High Card", "Pair", "Two Pair", "Three of a Kind",
            "Straight", "Flush", "Full House", "Four of a Kind",
            "Straight Flush", "Royal Flush"
        ]
        if 0 <= best_hand_rank < len(hand_rank_names):
            best_hand_name = hand_rank_names[best_hand_rank]
        else:
            best_hand_name = "Unknown"

        return {
            'total_games': total_games,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_ties': total_ties,
            'total_energy_won': total_energy_won,
            'total_energy_lost': total_energy_lost,
            'total_house_cuts': total_house_cuts,
            'net_energy': total_energy_won - total_energy_lost,
            'best_hand_rank': best_hand_rank,
            'best_hand_name': best_hand_name,
        }

    def record_reproduction(self, algorithm_id: int) -> None:
        """Record a successful reproduction by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the reproducing fish
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_reproductions += 1

    def record_food_eaten(self, algorithm_id: int) -> None:
        """Record food consumption by a fish with the given algorithm.

        Args:
            algorithm_id: Algorithm ID (0-47) of the fish that ate
        """
        if algorithm_id in self.algorithm_stats:
            self.algorithm_stats[algorithm_id].total_food_eaten += 1

    def record_poker_outcome(self, winner_id: int, loser_id: int,
                            winner_algo_id: Optional[int], loser_algo_id: Optional[int],
                            amount: float, winner_hand: 'PokerHand', loser_hand: 'PokerHand',
                            house_cut: float = 0.0) -> None:
        """Record a poker game outcome.

        Args:
            winner_id: Fish ID of winner (-1 for tie)
            loser_id: Fish ID of loser (-1 for tie)
            winner_algo_id: Algorithm ID of winner (None if no algorithm)
            loser_algo_id: Algorithm ID of loser (None if no algorithm)
            amount: Amount of energy transferred (after house cut)
            winner_hand: The winning poker hand
            loser_hand: The losing poker hand
            house_cut: Amount taken by house (default 0.0)
        """
        from core.poker_interaction import PokerHand

        # Handle tie case
        if winner_id == -1:
            if winner_algo_id is not None and winner_algo_id in self.poker_stats:
                self.poker_stats[winner_algo_id].total_games += 1
                self.poker_stats[winner_algo_id].total_ties += 1
                self.poker_stats[winner_algo_id]._total_hand_rank += winner_hand.rank_value
                self.poker_stats[winner_algo_id].avg_hand_rank = (
                    self.poker_stats[winner_algo_id]._total_hand_rank /
                    self.poker_stats[winner_algo_id].total_games
                )
            if loser_algo_id is not None and loser_algo_id in self.poker_stats:
                self.poker_stats[loser_algo_id].total_games += 1
                self.poker_stats[loser_algo_id].total_ties += 1
                self.poker_stats[loser_algo_id]._total_hand_rank += loser_hand.rank_value
                self.poker_stats[loser_algo_id].avg_hand_rank = (
                    self.poker_stats[loser_algo_id]._total_hand_rank /
                    self.poker_stats[loser_algo_id].total_games
                )
            return

        # Record winner stats
        if winner_algo_id is not None and winner_algo_id in self.poker_stats:
            stats = self.poker_stats[winner_algo_id]
            stats.total_games += 1
            stats.total_wins += 1
            stats.total_energy_won += amount
            stats.total_house_cuts += house_cut / 2  # Split house cut evenly between both players
            stats.best_hand_rank = max(stats.best_hand_rank, winner_hand.rank_value)
            stats._total_hand_rank += winner_hand.rank_value
            stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

        # Record loser stats
        if loser_algo_id is not None and loser_algo_id in self.poker_stats:
            stats = self.poker_stats[loser_algo_id]
            stats.total_games += 1
            stats.total_losses += 1
            stats.total_energy_lost += amount
            stats.total_house_cuts += house_cut / 2  # Split house cut evenly between both players
            stats._total_hand_rank += loser_hand.rank_value
            stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

        # Log event
        self.events.append(EcosystemEvent(
            frame=self.frame_count,
            event_type='poker',
            fish_id=winner_id,
            details=(
                f"Won {amount:.1f} energy from fish {loser_id} "
                f"({winner_hand.description} vs {loser_hand.description})"
            )
        ))

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
            ""
        ]

    def _get_top_performers_section(
        self, algorithms_with_data: List[Tuple[int, 'AlgorithmStats']]
    ) -> List[str]:
        """Generate top performing algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data,
            key=lambda x: x[1].get_reproduction_rate(),
            reverse=True
        )

        lines = [
            "-" * 80,
            "TOP PERFORMING ALGORITHMS (by reproduction rate)",
            "-" * 80,
            ""
        ]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            lines.extend([
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
                ""
            ])

        return lines

    def _get_survival_section(
        self, algorithms_with_data: List[Tuple[int, 'AlgorithmStats']]
    ) -> List[str]:
        """Generate top surviving algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data,
            key=lambda x: x[1].get_survival_rate(),
            reverse=True
        )

        lines = [
            "-" * 80,
            "TOP SURVIVING ALGORITHMS (by current survival rate)",
            "-" * 80,
            ""
        ]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            lines.extend([
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Survival Rate: {stats.get_survival_rate():.2%}",
                f"  Current Population: {stats.current_population}",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                ""
            ])

        return lines

    def _get_longevity_section(
        self, algorithms_with_data: List[Tuple[int, 'AlgorithmStats']]
    ) -> List[str]:
        """Generate longest-lived algorithms section."""
        algorithms_sorted = sorted(
            algorithms_with_data,
            key=lambda x: x[1].get_avg_lifespan(),
            reverse=True
        )

        lines = [
            "-" * 80,
            "LONGEST-LIVED ALGORITHMS (by average lifespan)",
            "-" * 80,
            ""
        ]

        for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
            starvation_pct = (
                stats.deaths_starvation / stats.total_deaths * 100
                if stats.total_deaths > 0 else 0
            )
            lines.extend([
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                f"  Deaths: {stats.total_deaths}",
                f"  Starvation Deaths: {stats.deaths_starvation} ({starvation_pct:.1f}%)",
                ""
            ])

        return lines

    def _get_worst_performers_section(self, min_sample_size: int) -> List[str]:
        """Generate worst performing algorithms section."""
        algorithms_with_deaths = [
            (algo_id, stats) for algo_id, stats in self.algorithm_stats.items()
            if stats.total_deaths >= min_sample_size
        ]
        algorithms_with_deaths.sort(
            key=lambda x: (
                x[1].deaths_starvation / x[1].total_deaths
                if x[1].total_deaths > 0 else 0
            ),
            reverse=True
        )

        lines = [
            "-" * 80,
            "WORST PERFORMERS (highest starvation rate)",
            "-" * 80,
            ""
        ]

        for i, (algo_id, stats) in enumerate(algorithms_with_deaths[:10], 1):
            starvation_rate = (
                stats.deaths_starvation / stats.total_deaths
                if stats.total_deaths > 0 else 0
            )
            lines.extend([
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Starvation Rate: {starvation_rate:.2%}",
                f"  Deaths: {stats.total_deaths}",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                f"  Reproduction Rate: {stats.get_reproduction_rate():.2%}",
                ""
            ])

        return lines

    def _get_recommendations_section(
        self, algorithms_with_data: List[Tuple[int, 'AlgorithmStats']]
    ) -> List[str]:
        """Generate recommendations section based on performance data."""
        lines = [
            "-" * 80,
            "RECOMMENDATIONS FOR NEXT GENERATION",
            "-" * 80,
            ""
        ]

        # Best performer recommendation
        if algorithms_with_data:
            best_algo_id, best_stats = algorithms_with_data[0]
            lines.extend([
                f"1. The most successful algorithm is '{best_stats.algorithm_name}'",
                f"   with a reproduction rate of {best_stats.get_reproduction_rate():.2%}.",
                ""
            ])

        # Worst performer warning
        algorithms_by_starvation = sorted(
            [(aid, s) for aid, s in self.algorithm_stats.items() if s.total_deaths > 0],
            key=lambda x: (
                x[1].deaths_starvation / x[1].total_deaths
                if x[1].total_deaths > 0 else 0
            ),
            reverse=True
        )

        if algorithms_by_starvation:
            worst_algo_id, worst_stats = algorithms_by_starvation[0]
            starvation_rate = (
                worst_stats.deaths_starvation / worst_stats.total_deaths
                if worst_stats.total_deaths > 0 else 0
            )
            lines.extend([
                f"2. The algorithm '{worst_stats.algorithm_name}' has the highest starvation rate",
                f"   at {starvation_rate:.2%}, indicating poor food-seeking behavior.",
                ""
            ])

        # Overall metrics
        total_starvation = sum(s.deaths_starvation for s in self.algorithm_stats.values())
        total_deaths_all = sum(s.total_deaths for s in self.algorithm_stats.values())
        if total_deaths_all > 0:
            overall_starvation_rate = total_starvation / total_deaths_all
            lines.append(f"3. Overall starvation rate: {overall_starvation_rate:.2%}")
            if overall_starvation_rate > 0.5:
                lines.extend([
                    "   RECOMMENDATION: High starvation indicates resource scarcity.",
                    "   Focus on food-seeking and energy conservation algorithms."
                ])
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
            (algo_id, stats) for algo_id, stats in self.algorithm_stats.items()
            if stats.total_births >= min_sample_size
        ]

        # Sort by reproduction rate for recommendations
        algorithms_with_data.sort(
            key=lambda x: x[1].get_reproduction_rate(),
            reverse=True
        )

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
