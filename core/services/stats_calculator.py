"""Statistics calculation service for the simulation.

This module provides a centralized service for calculating simulation
statistics. It extracts stat calculation logic from SimulationEngine
to improve separation of concerns.

Architecture Notes:
- Receives engine reference for accessing simulation state
- Provides modular stat calculation methods
- Can be extended with caching for expensive calculations
"""

import time
from statistics import mean, median, stdev
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine



class StatsCalculator:
    """Calculates simulation statistics on demand.

    This service extracts stat calculation from SimulationEngine,
    providing a cleaner separation of concerns and easier testing.

    Attributes:
        _engine: Reference to the simulation engine
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the stats calculator.

        Args:
            engine: The simulation engine to calculate stats for
        """
        self._engine = engine

    def _calculate_meta_stats(self, traits: List[Any], prefix: str) -> Dict[str, Any]:
        """Calculate meta-statistics (mutation rate, strength, HGT) for a list of traits.

        Args:
            traits: List of GeneticTrait objects
            prefix: Prefix for the output keys (e.g., 'adult_size')

        Returns:
            Dictionary with mean and std dev for mutation rate, strength, and HGT
        """
        stats: Dict[str, Any] = {}
        
        if not traits:
            # Return defaults if no traits
            for metric in ["mut_rate", "mut_strength", "hgt_prob"]:
                stats[f"{prefix}_{metric}_mean"] = 0.0
                stats[f"{prefix}_{metric}_std"] = 0.0
            return stats

        # Helper to safely calc mean/std
        def calc_safe(values: List[float]) -> Tuple[float, float]:
            if not values:
                return 0.0, 0.0
            m = mean(values)
            s = stdev(values) if len(values) > 1 else 0.0
            return m, s

        # Mutation Rate
        rates = [t.mutation_rate for t in traits]
        r_mean, r_std = calc_safe(rates)
        stats[f"{prefix}_mut_rate_mean"] = r_mean
        stats[f"{prefix}_mut_rate_std"] = r_std

        # Mutation Strength
        strengths = [t.mutation_strength for t in traits]
        s_mean, s_std = calc_safe(strengths)
        stats[f"{prefix}_mut_strength_mean"] = s_mean
        stats[f"{prefix}_mut_strength_std"] = s_std

        # HGT Probability
        hgts = [t.hgt_probability for t in traits]
        h_mean, h_std = calc_safe(hgts)
        stats[f"{prefix}_hgt_prob_mean"] = h_mean
        stats[f"{prefix}_hgt_prob_std"] = h_std

        return stats


    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive simulation statistics.

        This is the main entry point that aggregates all stat categories.

        Returns:
            Dictionary with all simulation statistics
        """
        if self._engine.ecosystem is None:
            return {}

        # Start with ecosystem summary stats
        stats = self._engine.ecosystem.get_summary_stats(
            self._engine.get_all_entities()
        )

        # Add cumulative energy sources
        stats["energy_sources"] = self._engine.ecosystem.get_energy_source_summary()

        # Add simulation state
        stats.update(self._get_simulation_state())

        # Add entity counts and energy
        stats.update(self._get_entity_stats())

        # Add fish health distribution
        stats.update(self._get_fish_health_stats())

        # Add genetic distribution stats
        stats.update(self._get_genetic_distribution_stats())

        return stats

    def _get_simulation_state(self) -> Dict[str, Any]:
        """Get simulation state statistics.

        Returns:
            Dictionary with frame count, time, and speed stats
        """
        from core.constants import FRAME_RATE

        elapsed = time.time() - self._engine.start_time
        return {
            "frame_count": self._engine.frame_count,
            "time_string": self._engine.time_system.get_time_string(),
            "elapsed_real_time": elapsed,
            "simulation_speed": (
                self._engine.frame_count / (FRAME_RATE * elapsed)
                if elapsed > 0
                else 0
            ),
        }

    def _get_entity_stats(self) -> Dict[str, Any]:
        """Get entity count and energy statistics.

        Returns:
            Dictionary with entity counts and energy totals
        """
        from core import entities
        from core.entities.fractal_plant import FractalPlant

        fish_list = self._engine.get_fish_list()
        all_food_list = self._engine.get_food_list()

        # Separate food types
        live_food_list = [
            e for e in all_food_list if isinstance(e, entities.LiveFood)
        ]
        regular_food_list = [
            e for e in all_food_list if not isinstance(e, entities.LiveFood)
        ]

        # Plant lists
        regular_plants = [
            e for e in self._engine.entities_list if isinstance(e, entities.Plant)
        ]
        fractal_plants = [
            e for e in self._engine.entities_list if isinstance(e, FractalPlant)
        ]

        return {
            "fish_count": len(fish_list),
            "fish_energy": sum(fish.energy for fish in fish_list),
            "food_count": len(regular_food_list),
            "food_energy": sum(food.energy for food in regular_food_list),
            "live_food_count": len(live_food_list),
            "live_food_energy": sum(food.energy for food in live_food_list),
            "plant_count": len(regular_plants) + len(fractal_plants),
            "plant_energy": sum(plant.energy for plant in fractal_plants),
        }

    def _get_fish_health_stats(self) -> Dict[str, Any]:
        """Get fish health and energy distribution statistics.

        Returns:
            Dictionary with fish health stats (critical, low, healthy, full)
        """
        fish_list = self._engine.get_fish_list()

        if not fish_list:
            return {
                "avg_fish_energy": 0.0,
                "min_fish_energy": 0.0,
                "max_fish_energy": 0.0,
                "min_max_energy_capacity": 0.0,
                "max_max_energy_capacity": 0.0,
                "median_max_energy_capacity": 0.0,
                "fish_health_critical": 0,
                "fish_health_low": 0,
                "fish_health_healthy": 0,
                "fish_health_full": 0,
            }

        fish_energies = [fish.energy for fish in fish_list]
        max_energies = [fish.max_energy for fish in fish_list]

        # Count fish in different energy health states
        critical_count = 0
        low_count = 0
        healthy_count = 0
        full_count = 0

        for fish in fish_list:
            ratio = fish.energy / fish.max_energy if fish.max_energy > 0 else 0
            if ratio < 0.15:
                critical_count += 1
            elif ratio < 0.30:
                low_count += 1
            elif ratio < 0.80:
                healthy_count += 1
            else:
                full_count += 1

        return {
            "avg_fish_energy": sum(fish_energies) / len(fish_list),
            "min_fish_energy": min(fish_energies),
            "max_fish_energy": max(fish_energies),
            "min_max_energy_capacity": min(max_energies),
            "max_max_energy_capacity": max(max_energies),
            "median_max_energy_capacity": median(max_energies),
            "fish_health_critical": critical_count,
            "fish_health_low": low_count,
            "fish_health_healthy": healthy_count,
            "fish_health_full": full_count,
        }

    def _get_genetic_distribution_stats(self) -> Dict[str, Any]:
        """Get genetic trait distribution statistics with histograms.

        Returns:
            Dictionary with genetic stats (adult size, eye size, fin size)
        """
        stats: Dict[str, Any] = {}

        # Adult size stats
        stats.update(self._get_adult_size_stats())

        # Eye size stats
        stats.update(self._get_eye_size_stats())

        # Fin size stats
        stats.update(self._get_fin_size_stats())

        # New physical traits
        stats.update(self._get_tail_size_stats())
        stats.update(self._get_body_aspect_stats())
        stats.update(self._get_template_id_stats())
        stats.update(self._get_pattern_type_stats())
        stats.update(self._get_pattern_intensity_stats())
        stats.update(self._get_lifespan_modifier_stats())

        return stats

    def _get_adult_size_stats(self) -> Dict[str, Any]:
        """Calculate adult size distribution statistics.

        Returns:
            Dictionary with adult size stats and histogram
        """
        from core.constants import (
            FISH_ADULT_SIZE,
            FISH_SIZE_MODIFIER_MAX,
            FISH_SIZE_MODIFIER_MIN,
        )

        fish_list = self._engine.get_fish_list()

        # Allowed size bounds
        allowed_min = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN
        allowed_max = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX

        stats = {
            "allowed_adult_size_min": allowed_min,
            "allowed_adult_size_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "adult_size_min": 0.0,
                "adult_size_max": 0.0,
                "adult_size_median": 0.0,
                "adult_size_range": "0.00-0.00",
                "adult_size_bins": [],
                "adult_size_bin_edges": [],
            })
            return stats

        adult_size_traits = [
            f.genome.physical.size_modifier for f in fish_list if hasattr(f, "genome")
        ]
        
        adult_sizes = [
            FISH_ADULT_SIZE * t.value
            for t in adult_size_traits
        ]

        # Calculate meta stats
        stats.update(self._calculate_meta_stats(adult_size_traits, "adult_size"))

        stats["adult_size_min"] = min(adult_sizes)
        stats["adult_size_max"] = max(adult_sizes)
        stats["adult_size_range"] = (
            f"{stats['adult_size_min']:.2f}-{stats['adult_size_max']:.2f}"
        )

        try:
            stats["adult_size_median"] = median(adult_sizes)
        except Exception:
            stats["adult_size_median"] = 0.0

        # Create histogram
        bins, edges = self._create_histogram(
            adult_sizes, allowed_min, allowed_max, num_bins=16
        )
        stats["adult_size_bins"] = bins
        stats["adult_size_bin_edges"] = edges

        return stats

    def _get_eye_size_stats(self) -> Dict[str, Any]:
        """Calculate eye size distribution statistics.

        Returns:
            Dictionary with eye size stats and histogram
        """
        fish_list = self._engine.get_fish_list()

        # Try to get allowed bounds from config
        try:
            from core.config.fish import EYE_SIZE_MAX, EYE_SIZE_MIN
            allowed_min = EYE_SIZE_MIN
            allowed_max = EYE_SIZE_MAX
        except Exception:
            allowed_min = 0.5
            allowed_max = 2.0

        stats = {
            "allowed_eye_size_min": allowed_min,
            "allowed_eye_size_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "eye_size_min": 0.0,
                "eye_size_max": 0.0,
                "eye_size_median": 0.0,
                "eye_size_bins": [],
                "eye_size_bin_edges": [],
            })
            return stats

        try:
            eye_traits = [f.genome.physical.eye_size for f in fish_list]
            eye_sizes = [t.value for t in eye_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(eye_traits, "eye_size"))

            if eye_sizes:
                stats["eye_size_min"] = min(eye_sizes)
                stats["eye_size_max"] = max(eye_sizes)

                try:
                    stats["eye_size_median"] = median(eye_sizes)
                except Exception:
                    stats["eye_size_median"] = 0.0

                # Create histogram using observed range
                es_min = min(eye_sizes)
                es_max = max(eye_sizes)
                bins, edges = self._create_histogram(
                    eye_sizes, es_min, es_max, num_bins=12
                )
                stats["eye_size_bins"] = bins
                stats["eye_size_bin_edges"] = edges
            else:
                stats.update({
                    "eye_size_min": 0.0,
                    "eye_size_max": 0.0,
                    "eye_size_median": 0.0,
                    "eye_size_bins": [],
                    "eye_size_bin_edges": [],
                })
        except Exception:
            stats.update({
                "eye_size_min": 0.0,
                "eye_size_max": 0.0,
                "eye_size_median": 0.0,
                "eye_size_bins": [],
                "eye_size_bin_edges": [],
            })

        return stats

    def _get_fin_size_stats(self) -> Dict[str, Any]:
        """Calculate fin size distribution statistics.

        Returns:
            Dictionary with fin size stats and histogram
        """
        fish_list = self._engine.get_fish_list()

        # Fixed allowed bounds for fin size
        allowed_min = 0.5
        allowed_max = 2.0

        stats = {
            "allowed_fin_size_min": allowed_min,
            "allowed_fin_size_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "fin_size_min": 0.0,
                "fin_size_max": 0.0,
                "fin_size_median": 0.0,
                "fin_size_bins": [],
                "fin_size_bin_edges": [],
            })
            return stats

        try:
            fin_traits = [f.genome.physical.fin_size for f in fish_list]
            fin_sizes = [t.value for t in fin_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(fin_traits, "fin_size"))

            if fin_sizes:
                stats["fin_size_min"] = min(fin_sizes)
                stats["fin_size_max"] = max(fin_sizes)

                try:
                    stats["fin_size_median"] = median(fin_sizes)
                except Exception:
                    stats["fin_size_median"] = 0.0

                # Create histogram using allowed range
                bins, edges = self._create_histogram(
                    fin_sizes, allowed_min, allowed_max, num_bins=12
                )
                stats["fin_size_bins"] = bins
                stats["fin_size_bin_edges"] = edges
            else:
                stats.update({
                    "fin_size_min": 0.0,
                    "fin_size_max": 0.0,
                    "fin_size_median": 0.0,
                    "fin_size_bins": [],
                    "fin_size_bin_edges": [],
                })
        except Exception:
            stats.update({
                "fin_size_min": 0.0,
                "fin_size_max": 0.0,
                "fin_size_median": 0.0,
                "fin_size_bins": [],
                "fin_size_bin_edges": [],
            })

        return stats

    def _get_tail_size_stats(self) -> Dict[str, Any]:
        """Calculate tail size distribution statistics."""
        fish_list = self._engine.get_fish_list()
        from core.constants import BODY_ASPECT_MIN, BODY_ASPECT_MAX

        fish_list = self._engine.get_fish_list()
        allowed_min = BODY_ASPECT_MIN
        allowed_max = BODY_ASPECT_MAX

        stats = {
            "allowed_tail_size_min": allowed_min,
            "allowed_tail_size_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "tail_size_min": 0.0,
                "tail_size_max": 0.0,
                "tail_size_median": 0.0,
                "tail_size_bins": [],
                "tail_size_bin_edges": [],
            })
            return stats

        try:
            tail_traits = [f.genome.physical.tail_size for f in fish_list]
            values = [t.value for t in tail_traits]
            
            # Calculate meta stats
            stats.update(self._calculate_meta_stats(tail_traits, "tail_size"))
            if values:
                stats["tail_size_min"] = min(values)
                stats["tail_size_max"] = max(values)
                try:
                    stats["tail_size_median"] = median(values)
                except Exception:
                    stats["tail_size_median"] = 0.0
                bins, edges = self._create_histogram(values, allowed_min, allowed_max, num_bins=12)
                stats["tail_size_bins"] = bins
                stats["tail_size_bin_edges"] = edges
            else:
                stats.update({
                    "tail_size_min": 0.0,
                    "tail_size_max": 0.0,
                    "tail_size_median": 0.0,
                    "tail_size_bins": [],
                    "tail_size_bin_edges": [],
                })
        except Exception:
             stats.update({
                "tail_size_min": 0.0,
                "tail_size_max": 0.0,
                "tail_size_median": 0.0,
                "tail_size_bins": [],
                "tail_size_bin_edges": [],
            })
        return stats

    def _get_body_aspect_stats(self) -> Dict[str, Any]:
        """Calculate body aspect distribution statistics."""
        fish_list = self._engine.get_fish_list()
        allowed_min = 0.5
        allowed_max = 2.0

        stats = {
            "allowed_body_aspect_min": allowed_min,
            "allowed_body_aspect_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "body_aspect_min": 0.0,
                "body_aspect_max": 0.0,
                "body_aspect_median": 0.0,
                "body_aspect_bins": [],
                "body_aspect_bin_edges": [],
            })
            return stats

        try:
            aspect_traits = [f.genome.physical.body_aspect for f in fish_list]
            values = [t.value for t in aspect_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(aspect_traits, "body_aspect"))
            if values:
                stats["body_aspect_min"] = min(values)
                stats["body_aspect_max"] = max(values)
                try:
                    stats["body_aspect_median"] = median(values)
                except Exception:
                    stats["body_aspect_median"] = 0.0
                bins, edges = self._create_histogram(values, allowed_min, allowed_max, num_bins=12)
                stats["body_aspect_bins"] = bins
                stats["body_aspect_bin_edges"] = edges
            else:
                stats.update({
                    "body_aspect_min": 0.0,
                    "body_aspect_max": 0.0,
                    "body_aspect_median": 0.0,
                    "body_aspect_bins": [],
                    "body_aspect_bin_edges": [],
                })
        except Exception:
             stats.update({
                "body_aspect_min": 0.0,
                "body_aspect_max": 0.0,
                "body_aspect_median": 0.0,
                "body_aspect_bins": [],
                "body_aspect_bin_edges": [],
            })
        return stats

    def _get_template_id_stats(self) -> Dict[str, Any]:
        """Calculate template_id distribution statistics (discrete)."""
        from core.constants import FISH_TEMPLATE_COUNT
        fish_list = self._engine.get_fish_list()
        allowed_min = 0.0
        allowed_max = float(FISH_TEMPLATE_COUNT - 1)

        stats = {
            "allowed_template_id_min": allowed_min,
            "allowed_template_id_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "template_id_min": 0.0,
                "template_id_max": 0.0,
                "template_id_median": 0.0,
                "template_id_bins": [],
                "template_id_bin_edges": [],
            })
            return stats

        try:
            template_traits = [f.genome.physical.template_id for f in fish_list]
            values = [float(t.value) for t in template_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(template_traits, "template_id"))
            if values:
                stats["template_id_min"] = min(values)
                stats["template_id_max"] = max(values)
                try:
                    stats["template_id_median"] = median(values)
                except Exception:
                    stats["template_id_median"] = 0.0

                # For discrete variables like template_id, clear bins are nice
                # Using FISH_TEMPLATE_COUNT bins guarantees one bin per ID
                bins, edges = self._create_histogram(values, -0.5, allowed_max + 0.5, num_bins=FISH_TEMPLATE_COUNT)
                stats["template_id_bins"] = bins
                stats["template_id_bin_edges"] = edges
            else:
                 stats.update({
                    "template_id_min": 0.0,
                    "template_id_max": 0.0,
                    "template_id_median": 0.0,
                    "template_id_bins": [],
                    "template_id_bin_edges": [],
                })
        except Exception:
             stats.update({
                "template_id_min": 0.0,
                "template_id_max": 0.0,
                "template_id_median": 0.0,
                "template_id_bins": [],
                "template_id_bin_edges": [],
            })
        return stats

    def _get_pattern_type_stats(self) -> Dict[str, Any]:
        """Calculate pattern_type distribution statistics (discrete)."""
        from core.constants import FISH_PATTERN_COUNT
        fish_list = self._engine.get_fish_list()
        allowed_min = 0.0
        allowed_max = float(FISH_PATTERN_COUNT - 1)

        stats = {
            "allowed_pattern_type_min": allowed_min,
            "allowed_pattern_type_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "pattern_type_min": 0.0,
                "pattern_type_max": 0.0,
                "pattern_type_median": 0.0,
                "pattern_type_bins": [],
                "pattern_type_bin_edges": [],
            })
            return stats

        try:
            pattern_traits = [f.genome.physical.pattern_type for f in fish_list]
            values = [float(t.value) for t in pattern_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(pattern_traits, "pattern_type"))
            if values:
                stats["pattern_type_min"] = min(values)
                stats["pattern_type_max"] = max(values)
                try:
                    stats["pattern_type_median"] = median(values)
                except Exception:
                    stats["pattern_type_median"] = 0.0

                # Discrete bins
                bins, edges = self._create_histogram(values, -0.5, allowed_max + 0.5, num_bins=FISH_PATTERN_COUNT)
                stats["pattern_type_bins"] = bins
                stats["pattern_type_bin_edges"] = edges
            else:
                stats.update({
                    "pattern_type_min": 0.0,
                    "pattern_type_max": 0.0,
                    "pattern_type_median": 0.0,
                    "pattern_type_bins": [],
                    "pattern_type_bin_edges": [],
                })
        except Exception:
            stats.update({
                "pattern_type_min": 0.0,
                "pattern_type_max": 0.0,
                "pattern_type_median": 0.0,
                "pattern_type_bins": [],
                "pattern_type_bin_edges": [],
            })
        return stats

    def _get_pattern_intensity_stats(self) -> Dict[str, Any]:
        """Calculate pattern intensity distribution statistics."""
        fish_list = self._engine.get_fish_list()
        allowed_min = 0.0
        allowed_max = 1.0

        stats = {
            "allowed_pattern_intensity_min": allowed_min,
            "allowed_pattern_intensity_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "pattern_intensity_min": 0.0,
                "pattern_intensity_max": 0.0,
                "pattern_intensity_median": 0.0,
                "pattern_intensity_bins": [],
                "pattern_intensity_bin_edges": [],
            })
            return stats

        try:
            intensity_traits = [f.genome.physical.pattern_intensity for f in fish_list]
            values = [t.value for t in intensity_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(intensity_traits, "pattern_intensity"))
            if values:
                stats["pattern_intensity_min"] = min(values)
                stats["pattern_intensity_max"] = max(values)
                try:
                    stats["pattern_intensity_median"] = median(values)
                except Exception:
                    stats["pattern_intensity_median"] = 0.0
                bins, edges = self._create_histogram(values, allowed_min, allowed_max, num_bins=10)
                stats["pattern_intensity_bins"] = bins
                stats["pattern_intensity_bin_edges"] = edges
            else:
                stats.update({
                    "pattern_intensity_min": 0.0,
                    "pattern_intensity_max": 0.0,
                    "pattern_intensity_median": 0.0,
                    "pattern_intensity_bins": [],
                    "pattern_intensity_bin_edges": [],
                })
        except Exception:
             stats.update({
                "pattern_intensity_min": 0.0,
                "pattern_intensity_max": 0.0,
                "pattern_intensity_median": 0.0,
                "pattern_intensity_bins": [],
                "pattern_intensity_bin_edges": [],
            })
        return stats

    def _get_lifespan_modifier_stats(self) -> Dict[str, Any]:
        """Calculate lifespan modifier distribution statistics."""
        fish_list = self._engine.get_fish_list()
        from core.constants import LIFESPAN_MODIFIER_MIN, LIFESPAN_MODIFIER_MAX

        # Allowed range matches core/genetics/physical.py
        allowed_min = LIFESPAN_MODIFIER_MIN
        allowed_max = LIFESPAN_MODIFIER_MAX

        stats = {
            "allowed_lifespan_modifier_min": allowed_min,
            "allowed_lifespan_modifier_max": allowed_max,
        }

        if not fish_list:
            stats.update({
                "lifespan_modifier_min": 0.0,
                "lifespan_modifier_max": 0.0,
                "lifespan_modifier_median": 0.0,
                "lifespan_modifier_bins": [],
                "lifespan_modifier_bin_edges": [],
            })
            return stats

        try:
            lifespan_traits = [f.genome.physical.lifespan_modifier for f in fish_list]
            values = [t.value for t in lifespan_traits]

            # Calculate meta stats
            stats.update(self._calculate_meta_stats(lifespan_traits, "lifespan_modifier"))
            if values:
                stats["lifespan_modifier_min"] = min(values)
                stats["lifespan_modifier_max"] = max(values)
                try:
                    stats["lifespan_modifier_median"] = median(values)
                except Exception:
                    stats["lifespan_modifier_median"] = 0.0
                bins, edges = self._create_histogram(values, allowed_min, allowed_max, num_bins=12)
                stats["lifespan_modifier_bins"] = bins
                stats["lifespan_modifier_bin_edges"] = edges
            else:
                stats.update({
                    "lifespan_modifier_min": 0.0,
                    "lifespan_modifier_max": 0.0,
                    "lifespan_modifier_median": 0.0,
                    "lifespan_modifier_bins": [],
                    "lifespan_modifier_bin_edges": [],
                })
        except Exception:
             stats.update({
                "lifespan_modifier_min": 0.0,
                "lifespan_modifier_max": 0.0,
                "lifespan_modifier_median": 0.0,
                "lifespan_modifier_bins": [],
                "lifespan_modifier_bin_edges": [],
            })
        return stats

    def _create_histogram(
        self,
        values: List[float],
        range_min: float,
        range_max: float,
        num_bins: int = 12,
    ) -> tuple:
        """Create a histogram from values.

        Args:
            values: List of values to bin
            range_min: Minimum edge of histogram
            range_max: Maximum edge of histogram
            num_bins: Number of bins

        Returns:
            Tuple of (bin_counts, bin_edges)
        """
        if not values:
            return [], []

        span = max(1e-6, range_max - range_min)
        edges = [range_min + (span * i) / num_bins for i in range(num_bins + 1)]
        counts = [0] * num_bins

        for v in values:
            idx = int((v - range_min) / span * num_bins)
            if idx < 0:
                idx = 0
            elif idx >= num_bins:
                idx = num_bins - 1
            counts[idx] += 1

        return counts, edges
