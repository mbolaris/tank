"""Enhanced statistics tracking for evolutionary dynamics.

This module provides advanced population analytics including:
- Time series tracking (historical trends)
- Trait correlation analysis (which traits lead to success)
- Extinction tracking (which algorithms died out)
- Evolutionary rate calculations (how fast traits are changing)
- Energy efficiency metrics (energy-to-offspring ratios)
- Fitness landscape mapping (trait combinations vs fitness)
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import math

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome
    from core.ecosystem import EcosystemManager


@dataclass
class TimeSeriesSnapshot:
    """A snapshot of ecosystem state at a specific frame."""

    frame: int
    population: int
    avg_fitness: float
    avg_speed: float
    avg_size: float
    avg_metabolism: float
    avg_energy: float
    unique_algorithms: int
    diversity_score: float
    total_energy: float
    birth_rate: float  # Births per frame
    death_rate: float  # Deaths per frame


@dataclass
class TraitCorrelation:
    """Correlation between a trait and fitness."""

    trait_name: str
    correlation: float  # -1.0 to +1.0
    sample_size: int
    p_value: float  # Statistical significance (lower is better)


@dataclass
class ExtinctionEvent:
    """Records when an algorithm goes extinct."""

    algorithm_id: int
    algorithm_name: str
    extinction_frame: int
    total_births: int
    total_deaths: int
    avg_lifespan: float
    extinction_cause: str  # 'outcompeted', 'starvation', 'predation'


@dataclass
class EvolutionaryRate:
    """Measures how fast traits are evolving."""

    trait_name: str
    rate_of_change: float  # Units per generation
    variance_change: float  # Change in population variance
    directional_selection: float  # Direction of selection pressure (-1 to +1)


@dataclass
class EnergyEfficiencyMetrics:
    """Metrics for energy usage efficiency."""

    total_energy_consumed: float
    total_energy_from_food: float
    total_offspring_produced: int
    energy_per_offspring: float
    food_to_offspring_ratio: float
    avg_energy_waste: float  # Energy lost to death without reproduction


class EnhancedStatisticsTracker:
    """Advanced statistics tracking for evolutionary analysis.

    This class extends the basic EcosystemManager statistics with:
    - Historical time series data
    - Correlation analysis between traits and fitness
    - Extinction event tracking
    - Evolutionary rate measurements
    - Energy efficiency metrics
    """

    def __init__(self, max_history_length: int = 1000):
        """Initialize the enhanced statistics tracker.

        Args:
            max_history_length: Maximum number of frames to keep in history
        """
        self.max_history_length = max_history_length

        # Time series data
        self.time_series: deque = deque(maxlen=max_history_length)

        # Trait correlation data (trait_name -> list of (trait_value, fitness) pairs)
        self.trait_fitness_data: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

        # Extinction tracking
        self.extinct_algorithms: List[ExtinctionEvent] = []
        self.algorithm_last_seen: Dict[int, int] = {}  # algorithm_id -> last frame seen
        self.algorithm_extinction_check: Dict[int, bool] = {}  # algorithm_id -> is_extinct

        # Evolutionary rates (trait_name -> historical values)
        self.trait_history: Dict[str, deque] = {
            "speed": deque(maxlen=100),
            "size": deque(maxlen=100),
            "metabolism": deque(maxlen=100),
            "vision": deque(maxlen=100),
            "aggression": deque(maxlen=100),
            "social_tendency": deque(maxlen=100),
        }

        # Energy efficiency tracking
        self.energy_efficiency = EnergyEfficiencyMetrics(
            total_energy_consumed=0.0,
            total_energy_from_food=0.0,
            total_offspring_produced=0,
            energy_per_offspring=0.0,
            food_to_offspring_ratio=0.0,
            avg_energy_waste=0.0,
        )

        # Death energy tracking (for waste calculation)
        self.total_death_energy_loss: float = 0.0
        self.total_deaths_tracked: int = 0

    def record_frame_snapshot(
        self,
        frame: int,
        fish_list: List["Fish"],
        births_this_frame: int = 0,
        deaths_this_frame: int = 0,
    ) -> None:
        """Record a snapshot of the current state for time series analysis.

        Args:
            frame: Current frame number
            fish_list: List of all living fish
            births_this_frame: Number of births this frame
            deaths_this_frame: Number of deaths this frame
        """
        if not fish_list:
            return

        # Calculate aggregates
        population = len(fish_list)
        avg_fitness = sum(f.genome.fitness_score for f in fish_list) / population
        avg_speed = sum(f.genome.speed_modifier for f in fish_list) / population
        avg_size = sum(f.genome.size_modifier for f in fish_list) / population
        avg_metabolism = sum(f.genome.metabolism_rate for f in fish_list) / population
        avg_energy = sum(f.energy for f in fish_list) / population
        total_energy = sum(f.energy for f in fish_list)

        # Count unique algorithms
        from core.algorithms import get_algorithm_index

        algorithms = set()
        for f in fish_list:
            if f.genome.behavior_algorithm is not None:
                algo_id = get_algorithm_index(f.genome.behavior_algorithm)
                if algo_id >= 0:
                    algorithms.add(algo_id)
                    self.algorithm_last_seen[algo_id] = frame

        unique_algorithms = len(algorithms)

        # Calculate diversity (simple variance-based measure)
        speed_variance = (
            sum((f.genome.speed_modifier - avg_speed) ** 2 for f in fish_list) / population
        )
        size_variance = (
            sum((f.genome.size_modifier - avg_size) ** 2 for f in fish_list) / population
        )
        diversity_score = min(1.0, (speed_variance + size_variance) / 2.0 * 5.0)  # Normalize

        # Birth/death rates (per frame)
        birth_rate = births_this_frame
        death_rate = deaths_this_frame

        # Create snapshot
        snapshot = TimeSeriesSnapshot(
            frame=frame,
            population=population,
            avg_fitness=avg_fitness,
            avg_speed=avg_speed,
            avg_size=avg_size,
            avg_metabolism=avg_metabolism,
            avg_energy=avg_energy,
            unique_algorithms=unique_algorithms,
            diversity_score=diversity_score,
            total_energy=total_energy,
            birth_rate=birth_rate,
            death_rate=death_rate,
        )

        self.time_series.append(snapshot)

        # Update trait history for evolutionary rate calculation
        self.trait_history["speed"].append(avg_speed)
        self.trait_history["size"].append(avg_size)
        self.trait_history["metabolism"].append(avg_metabolism)

    def record_trait_fitness_sample(self, genome: "Genome") -> None:
        """Record a trait-fitness data point for correlation analysis.

        Args:
            genome: Genome to sample from
        """
        fitness = genome.fitness_score

        # Record various traits
        self.trait_fitness_data["speed"].append((genome.speed_modifier, fitness))
        self.trait_fitness_data["size"].append((genome.size_modifier, fitness))
        self.trait_fitness_data["metabolism"].append((genome.metabolism_rate, fitness))
        self.trait_fitness_data["vision"].append((genome.vision_range, fitness))
        self.trait_fitness_data["aggression"].append((genome.aggression, fitness))
        self.trait_fitness_data["social_tendency"].append((genome.social_tendency, fitness))
        self.trait_fitness_data["max_energy"].append((genome.max_energy, fitness))

        # Limit sample size to prevent memory bloat
        max_samples = 500
        for trait_name in self.trait_fitness_data:
            if len(self.trait_fitness_data[trait_name]) > max_samples:
                # Keep most recent samples
                self.trait_fitness_data[trait_name] = self.trait_fitness_data[trait_name][
                    -max_samples:
                ]

    def calculate_trait_correlations(self) -> List[TraitCorrelation]:
        """Calculate correlations between traits and fitness.

        Returns:
            List of TraitCorrelation objects showing which traits correlate with success
        """
        correlations = []

        for trait_name, samples in self.trait_fitness_data.items():
            if len(samples) < 10:
                # Need at least 10 samples for meaningful correlation
                continue

            # Calculate Pearson correlation coefficient
            n = len(samples)
            trait_values = [s[0] for s in samples]
            fitness_values = [s[1] for s in samples]

            mean_trait = sum(trait_values) / n
            mean_fitness = sum(fitness_values) / n

            numerator = sum(
                (t - mean_trait) * (f - mean_fitness) for t, f in zip(trait_values, fitness_values)
            )

            trait_variance = sum((t - mean_trait) ** 2 for t in trait_values)
            fitness_variance = sum((f - mean_fitness) ** 2 for f in fitness_values)

            denominator = math.sqrt(trait_variance * fitness_variance)

            if denominator == 0:
                correlation = 0.0
            else:
                correlation = numerator / denominator

            # Calculate p-value (simplified t-test)
            if abs(correlation) > 0.01:
                t_stat = correlation * math.sqrt((n - 2) / (1 - correlation**2))
                # Simplified p-value estimate
                p_value = max(0.001, 1.0 / (1.0 + abs(t_stat)))
            else:
                p_value = 1.0

            correlations.append(
                TraitCorrelation(
                    trait_name=trait_name, correlation=correlation, sample_size=n, p_value=p_value
                )
            )

        # Sort by absolute correlation strength
        correlations.sort(key=lambda x: abs(x.correlation), reverse=True)

        return correlations

    def check_for_extinctions(
        self, frame: int, ecosystem: "EcosystemManager"
    ) -> List[ExtinctionEvent]:
        """Check if any algorithms have gone extinct.

        An algorithm is considered extinct if:
        - No fish with this algorithm have been seen for 1000 frames
        - Total births > 0 (it existed at some point)
        - Current population = 0

        Args:
            frame: Current frame number
            ecosystem: Ecosystem manager with algorithm stats

        Returns:
            List of new extinction events
        """
        new_extinctions = []
        extinction_threshold = 1000  # Frames without seeing algorithm

        for algo_id, stats in ecosystem.algorithm_stats.items():
            # Skip if already tracked as extinct
            if self.algorithm_extinction_check.get(algo_id, False):
                continue

            # Check if algorithm has existed and is now gone
            if stats.total_births > 0 and stats.current_population == 0:
                last_seen = self.algorithm_last_seen.get(algo_id, 0)
                frames_since_seen = frame - last_seen

                if frames_since_seen > extinction_threshold:
                    # Algorithm is extinct!
                    # Determine cause
                    if stats.total_deaths > 0:
                        starvation_rate = stats.deaths_starvation / stats.total_deaths
                        predation_rate = stats.deaths_predation / stats.total_deaths

                        if starvation_rate > 0.6:
                            cause = "starvation"
                        elif predation_rate > 0.3:
                            cause = "predation"
                        else:
                            cause = "outcompeted"
                    else:
                        cause = "unknown"

                    extinction = ExtinctionEvent(
                        algorithm_id=algo_id,
                        algorithm_name=stats.algorithm_name,
                        extinction_frame=frame,
                        total_births=stats.total_births,
                        total_deaths=stats.total_deaths,
                        avg_lifespan=stats.get_avg_lifespan(),
                        extinction_cause=cause,
                    )

                    self.extinct_algorithms.append(extinction)
                    self.algorithm_extinction_check[algo_id] = True
                    new_extinctions.append(extinction)

        return new_extinctions

    def calculate_evolutionary_rates(self) -> List[EvolutionaryRate]:
        """Calculate how fast traits are evolving.

        Returns:
            List of EvolutionaryRate objects showing evolutionary dynamics
        """
        rates = []

        for trait_name, history in self.trait_history.items():
            if len(history) < 10:
                continue

            # Calculate rate of change (trend)
            values = list(history)
            n = len(values)

            # Linear regression to find trend
            x_values = list(range(n))
            mean_x = sum(x_values) / n
            mean_y = sum(values) / n

            numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, values))
            denominator = sum((x - mean_x) ** 2 for x in x_values)

            if denominator == 0:
                slope = 0.0
            else:
                slope = numerator / denominator

            # Calculate variance change
            first_half = values[: n // 2]
            second_half = values[n // 2 :]

            if len(first_half) > 1 and len(second_half) > 1:
                var1 = sum((v - sum(first_half) / len(first_half)) ** 2 for v in first_half) / len(
                    first_half
                )
                var2 = sum(
                    (v - sum(second_half) / len(second_half)) ** 2 for v in second_half
                ) / len(second_half)
                variance_change = var2 - var1
            else:
                variance_change = 0.0

            # Directional selection (normalized slope)
            max_slope = 0.01  # Typical maximum slope
            directional_selection = max(-1.0, min(1.0, slope / max_slope))

            rates.append(
                EvolutionaryRate(
                    trait_name=trait_name,
                    rate_of_change=slope,
                    variance_change=variance_change,
                    directional_selection=directional_selection,
                )
            )

        return rates

    def record_energy_consumption(self, amount: float) -> None:
        """Record energy consumed by fish.

        Args:
            amount: Energy amount consumed
        """
        self.energy_efficiency.total_energy_consumed += amount

    def record_energy_from_food(self, amount: float) -> None:
        """Record energy gained from food.

        Args:
            amount: Energy amount gained
        """
        self.energy_efficiency.total_energy_from_food += amount

    def record_offspring_birth(self, energy_cost: float) -> None:
        """Record a reproduction event.

        Args:
            energy_cost: Energy spent on reproduction
        """
        self.energy_efficiency.total_offspring_produced += 1

        # Update metrics
        if self.energy_efficiency.total_offspring_produced > 0:
            self.energy_efficiency.energy_per_offspring = (
                self.energy_efficiency.total_energy_consumed
                / self.energy_efficiency.total_offspring_produced
            )

        if self.energy_efficiency.total_energy_from_food > 0:
            self.energy_efficiency.food_to_offspring_ratio = (
                self.energy_efficiency.total_offspring_produced
                / (self.energy_efficiency.total_energy_from_food / 10.0)  # Normalize by food items
            )

    def record_death_energy_loss(self, remaining_energy: float) -> None:
        """Record energy lost when fish dies.

        Args:
            remaining_energy: Energy the fish had when it died
        """
        self.total_death_energy_loss += remaining_energy
        self.total_deaths_tracked += 1

        if self.total_deaths_tracked > 0:
            self.energy_efficiency.avg_energy_waste = (
                self.total_death_energy_loss / self.total_deaths_tracked
            )

    def get_time_series_summary(self, frames: int = 100) -> Dict[str, Any]:
        """Get summary of recent time series data.

        Args:
            frames: Number of recent frames to summarize

        Returns:
            Dictionary with time series statistics
        """
        if not self.time_series:
            return {}

        recent_data = list(self.time_series)[-frames:]

        if not recent_data:
            return {}

        # Calculate trends
        populations = [s.population for s in recent_data]
        fitness_values = [s.avg_fitness for s in recent_data]
        diversity_values = [s.diversity_score for s in recent_data]

        return {
            "avg_population": sum(populations) / len(populations),
            "population_trend": populations[-1] - populations[0] if len(populations) > 1 else 0,
            "avg_fitness": sum(fitness_values) / len(fitness_values),
            "fitness_trend": (
                fitness_values[-1] - fitness_values[0] if len(fitness_values) > 1 else 0
            ),
            "avg_diversity": sum(diversity_values) / len(diversity_values),
            "diversity_trend": (
                diversity_values[-1] - diversity_values[0] if len(diversity_values) > 1 else 0
            ),
            "total_births": sum(s.birth_rate for s in recent_data),
            "total_deaths": sum(s.death_rate for s in recent_data),
        }

    def get_full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive statistics report.

        Returns:
            Dictionary with all enhanced statistics
        """
        return {
            "time_series_summary": self.get_time_series_summary(),
            "trait_correlations": [
                {
                    "trait": tc.trait_name,
                    "correlation": tc.correlation,
                    "sample_size": tc.sample_size,
                    "p_value": tc.p_value,
                }
                for tc in self.calculate_trait_correlations()
            ],
            "extinctions": [
                {
                    "algorithm_name": e.algorithm_name,
                    "extinction_frame": e.extinction_frame,
                    "total_births": e.total_births,
                    "avg_lifespan": e.avg_lifespan,
                    "cause": e.extinction_cause,
                }
                for e in self.extinct_algorithms
            ],
            "evolutionary_rates": [
                {
                    "trait": er.trait_name,
                    "rate_of_change": er.rate_of_change,
                    "variance_change": er.variance_change,
                    "directional_selection": er.directional_selection,
                }
                for er in self.calculate_evolutionary_rates()
            ],
            "energy_efficiency": {
                "total_energy_consumed": self.energy_efficiency.total_energy_consumed,
                "total_energy_from_food": self.energy_efficiency.total_energy_from_food,
                "total_offspring": self.energy_efficiency.total_offspring_produced,
                "energy_per_offspring": self.energy_efficiency.energy_per_offspring,
                "food_to_offspring_ratio": self.energy_efficiency.food_to_offspring_ratio,
                "avg_energy_waste": self.energy_efficiency.avg_energy_waste,
            },
        }
