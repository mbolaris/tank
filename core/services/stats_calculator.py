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
from statistics import median
from typing import TYPE_CHECKING, Any, Dict, List

from core.statistics_utils import compute_meta_stats, create_histogram, safe_mean_std

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine
    from core.entities import Fish




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
        meta = compute_meta_stats(traits)
        return {
            f"{prefix}_mut_rate_mean": meta.mut_rate_mean,
            f"{prefix}_mut_rate_std": meta.mut_rate_std,
            f"{prefix}_mut_strength_mean": meta.mut_strength_mean,
            f"{prefix}_mut_strength_std": meta.mut_strength_std,
            f"{prefix}_hgt_prob_mean": meta.hgt_prob_mean,
            f"{prefix}_hgt_prob_std": meta.hgt_prob_std,
        }

    def _humanize_gene_label(self, key: str) -> str:
        special = {
            "size_modifier": "Size Modifier",
            "adult_size": "Adult Size",
            "template_id": "Template",
            "pattern_type": "Pattern",
            "pattern_intensity": "Pattern Intensity",
            "lifespan_modifier": "Lifespan Mod",
        }
        if key in special:
            return special[key]
        return " ".join(part.capitalize() for part in key.split("_"))

    def _build_gene_distributions(self) -> Dict[str, Any]:
        """Build a dynamic gene distribution payload.

        This is intended for the frontend dashboards so new genes can appear
        automatically when added to the trait spec lists.
        """
        fish_list = self._engine.get_fish_list()

        def meta_for_traits(traits: List[Any]) -> Dict[str, float]:
            # Use centralized meta computation from statistics_utils
            return compute_meta_stats(traits).to_dict()

        def build_from_specs(*, category: str, traits_attr: str, specs: List[Any]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            if not fish_list:
                # Still emit entries with bounds so UI can render empty graphs.
                for spec in specs:
                    allowed_min = float(spec.min_val)
                    allowed_max = float(spec.max_val)
                    out.append(
                        {
                            "key": spec.name,
                            "label": self._humanize_gene_label(spec.name),
                            "category": category,
                            "discrete": bool(getattr(spec, "discrete", False)),
                            "allowed_min": allowed_min,
                            "allowed_max": allowed_max,
                            "min": 0.0,
                            "max": 0.0,
                            "median": 0.0,
                            "bins": [],
                            "bin_edges": [],
                            "meta": meta_for_traits([]),
                        }
                    )
                return out

            for spec in specs:
                try:
                    traits = [
                        getattr(getattr(f.genome, traits_attr), spec.name)
                        for f in fish_list
                        if hasattr(f, "genome")
                        and hasattr(f.genome, traits_attr)
                        and hasattr(getattr(f.genome, traits_attr), spec.name)
                    ]
                    values = [float(t.value) for t in traits]
                    allowed_min = float(spec.min_val)
                    allowed_max = float(spec.max_val)
                    if not values:
                        out.append(
                            {
                                "key": spec.name,
                                "label": self._humanize_gene_label(spec.name),
                                "category": category,
                                "discrete": bool(getattr(spec, "discrete", False)),
                                "allowed_min": allowed_min,
                                "allowed_max": allowed_max,
                                "min": 0.0,
                                "max": 0.0,
                                "median": 0.0,
                                "bins": [],
                                "bin_edges": [],
                                "meta": meta_for_traits([]),
                            }
                        )
                        continue

                    v_min = min(values)
                    v_max = max(values)
                    try:
                        v_median = median(values)
                    except Exception:
                        v_median = 0.0

                    discrete = bool(getattr(spec, "discrete", False))
                    if discrete:
                        # One bin per discrete value.
                        bin_count = int(round(allowed_max - allowed_min + 1))
                        bins, edges = create_histogram(
                            values,
                            allowed_min - 0.5,
                            allowed_max + 0.5,
                            num_bins=max(1, bin_count),
                        )
                    else:
                        bins, edges = create_histogram(values, allowed_min, allowed_max, num_bins=12)

                    out.append(
                        {
                            "key": spec.name,
                            "label": self._humanize_gene_label(spec.name),
                            "category": category,
                            "discrete": discrete,
                            "allowed_min": allowed_min,
                            "allowed_max": allowed_max,
                            "min": float(v_min),
                            "max": float(v_max),
                            "median": float(v_median),
                            "bins": bins,
                            "bin_edges": edges,
                            "meta": meta_for_traits(traits),
                        }
                    )
                except Exception:
                    # Skip individual trait failures; keep the rest.
                    continue
            return out

        physical_specs: List[Any] = []
        behavioral_specs: List[Any] = []
        try:
            from core.genetics.physical import PHYSICAL_TRAIT_SPECS

            physical_specs = list(PHYSICAL_TRAIT_SPECS)
        except Exception:
            physical_specs = []

        try:
            from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS

            behavioral_specs = list(BEHAVIORAL_TRAIT_SPECS)
        except Exception:
            behavioral_specs = []

        physical = build_from_specs(category="physical", traits_attr="physical", specs=physical_specs)
        behavioral = build_from_specs(category="behavioral", traits_attr="behavioral", specs=behavioral_specs)

        # Add derived adult size (based on size_modifier) as a first-class metric.
        try:
            from core.constants import FISH_ADULT_SIZE, FISH_SIZE_MODIFIER_MAX, FISH_SIZE_MODIFIER_MIN

            allowed_min = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN)
            allowed_max = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX)

            size_traits = [
                f.genome.physical.size_modifier
                for f in fish_list
                if hasattr(f, "genome") and hasattr(f.genome, "physical")
            ]
            adult_sizes = [float(FISH_ADULT_SIZE * t.value) for t in size_traits]

            if adult_sizes:
                a_min = float(min(adult_sizes))
                a_max = float(max(adult_sizes))
                try:
                    a_median = float(median(adult_sizes))
                except Exception:
                    a_median = 0.0
                bins, edges = create_histogram(adult_sizes, allowed_min, allowed_max, num_bins=16)
            else:
                a_min = 0.0
                a_max = 0.0
                a_median = 0.0
                bins, edges = [], []

            physical.insert(
                0,
                {
                    "key": "adult_size",
                    "label": self._humanize_gene_label("adult_size"),
                    "category": "physical",
                    "discrete": False,
                    "allowed_min": allowed_min,
                    "allowed_max": allowed_max,
                    "min": a_min,
                    "max": a_max,
                    "median": a_median,
                    "bins": bins,
                    "bin_edges": edges,
                    "meta": meta_for_traits(size_traits),
                },
            )
        except Exception:
            pass

        return {"physical": physical, "behavioral": behavioral}

    def _get_composable_behavior_distributions(self, fish_list: List["Fish"]) -> List[Dict[str, Any]]:
        """Build gene distributions for composable behavior traits."""
        try:
            from core.algorithms.composable import (
                SUB_BEHAVIOR_PARAMS,
                ThreatResponse,
                FoodApproach,
                EnergyStyle,
                SocialMode,
                PokerEngagement,
            )
        except ImportError:
            return []

        out: List[Dict[str, Any]] = []

        # 1. Discrete Traits (Enums)
        # We manually map these because they are special enum selections in the ComposableBehavior
        discrete_traits = [
            ("threat_response", ThreatResponse, "Threat Response"),
            ("food_approach", FoodApproach, "Food Approach"),
            ("energy_style", EnergyStyle, "Energy Style"),
            ("social_mode", SocialMode, "Social Mode"),
            ("poker_engagement", PokerEngagement, "Poker Engagement"),
        ]
        # Shared metadata for all composable traits (since they are all packed in one GeneticTrait wrapper)
        # We calculate it once effectively.
        composable_traits = [
            f.genome.behavioral.behavior
            for f in fish_list
            if f.genome.behavioral.behavior is not None
        ]
        # Use centralized meta computation from statistics_utils
        meta_dict = compute_meta_stats(composable_traits).to_dict()

        for key, enum_cls, label in discrete_traits:
            allowed_min = 0.0
            allowed_max = float(len(enum_cls) - 1)
            
            values = []
            for f in fish_list:
                cb = f.genome.behavioral.behavior.value
                if cb:
                    val = getattr(cb, key, 0)
                    values.append(float(val))
            
            if not values:
                out.append({
                    "key": key,
                    "label": label,
                    "category": "behavioral",
                    "discrete": True,
                    "allowed_min": allowed_min,
                    "allowed_max": allowed_max,
                    "min": 0.0, "max": 0.0, "median": 0.0,
                    "bins": [], "bin_edges": [],
                    "meta": meta_dict
                })
                continue

            v_min = min(values)
            v_max = max(values)
            v_median = median(values)
            
            # Histogram for discrete: one bin per option
            bin_count = int(allowed_max - allowed_min + 1)
            bins, edges = create_histogram(values, allowed_min - 0.5, allowed_max + 0.5, num_bins=bin_count)
            
            out.append({
                "key": key,
                "label": label,
                "category": "behavioral",
                "discrete": True,
                "allowed_min": allowed_min,
                "allowed_max": allowed_max,
                "min": float(v_min),
                "max": float(v_max),
                "median": float(v_median),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_dict
            })

        # 2. Continuous Parameters
        for param_key, (p_min, p_max) in SUB_BEHAVIOR_PARAMS.items():
            human_label = self._humanize_gene_label(param_key)
            values = []
            for f in fish_list:
                cb = f.genome.behavioral.behavior.value
                if cb and param_key in cb.parameters:
                    values.append(cb.parameters[param_key])

            if not values:
                out.append({
                    "key": param_key,
                    "label": human_label,
                    "category": "behavioral",
                    "discrete": False,
                    "allowed_min": p_min,
                    "allowed_max": p_max,
                    "min": 0.0, "max": 0.0, "median": 0.0,
                    "bins": [], "bin_edges": [],
                    "meta": meta_dict  # Share same meta since they are part of same gene complex
                })
                continue
                
            v_min = min(values)
            v_max = max(values)
            v_median = median(values)
            bins, edges = create_histogram(values, p_min, p_max, num_bins=12)

            out.append({
                "key": param_key,
                "label": human_label,
                "category": "behavioral",
                "discrete": False,
                "allowed_min": p_min,
                "allowed_max": p_max,
                "min": float(v_min),
                "max": float(v_max),
                "median": float(v_median),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_dict
            })

        return out

    def _get_poker_strategy_distributions(self, fish_list: List["Fish"]) -> List[Dict[str, Any]]:
        """Build gene distributions for composable poker strategy traits.
        
        Similar to _get_composable_behavior_distributions but for poker strategy
        sub-behaviors (HandSelection, BettingStyle, BluffingApproach, etc.).
        """
        try:
            from core.poker.strategy.composable_poker import (
                ComposablePokerStrategy,
                POKER_SUB_BEHAVIOR_PARAMS,
                HandSelection,
                BettingStyle,
                BluffingApproach,
                PositionAwareness,
                ShowdownTendency,
            )
        except ImportError:
            return []

        out: List[Dict[str, Any]] = []

        # 1. Discrete Traits (Enums) - The poker sub-behaviors
        discrete_traits = [
            ("hand_selection", HandSelection, "Hand Selection"),
            ("betting_style", BettingStyle, "Betting Style"),
            ("bluffing_approach", BluffingApproach, "Bluffing Approach"),
            ("position_awareness", PositionAwareness, "Position Awareness"),
            ("showdown_tendency", ShowdownTendency, "Showdown Tendency"),
        ]

        # Get poker strategy traits for meta-stats
        poker_traits = [
            f.genome.behavioral.poker_strategy
            for f in fish_list
            if hasattr(f, "genome") 
            and hasattr(f.genome, "behavioral")
            and f.genome.behavioral.poker_strategy is not None
        ]
        meta_dict = compute_meta_stats(poker_traits).to_dict()

        for key, enum_cls, label in discrete_traits:
            allowed_min = 0.0
            allowed_max = float(len(enum_cls) - 1)

            values = []
            for f in fish_list:
                if not hasattr(f, "genome") or not hasattr(f.genome, "behavioral"):
                    continue
                ps = f.genome.behavioral.poker_strategy
                if ps is None:
                    continue
                strat = ps.value
                if strat is None or not isinstance(strat, ComposablePokerStrategy):
                    continue
                val = getattr(strat, key, 0)
                values.append(float(val))

            if not values:
                out.append({
                    "key": f"poker_{key}",
                    "label": label,
                    "category": "behavioral",
                    "discrete": True,
                    "allowed_min": allowed_min,
                    "allowed_max": allowed_max,
                    "min": 0.0, "max": 0.0, "median": 0.0,
                    "bins": [], "bin_edges": [],
                    "meta": meta_dict
                })
                continue

            v_min = min(values)
            v_max = max(values)
            v_median = median(values)

            # Histogram for discrete: one bin per option
            bin_count = int(allowed_max - allowed_min + 1)
            bins, edges = create_histogram(values, allowed_min - 0.5, allowed_max + 0.5, num_bins=bin_count)

            out.append({
                "key": f"poker_{key}",
                "label": label,
                "category": "behavioral",
                "discrete": True,
                "allowed_min": allowed_min,
                "allowed_max": allowed_max,
                "min": float(v_min),
                "max": float(v_max),
                "median": float(v_median),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_dict
            })

        # 2. Continuous Parameters from ComposablePokerStrategy
        for param_key, (p_min, p_max) in POKER_SUB_BEHAVIOR_PARAMS.items():
            human_label = self._humanize_gene_label(param_key)
            values = []
            for f in fish_list:
                if not hasattr(f, "genome") or not hasattr(f.genome, "behavioral"):
                    continue
                ps = f.genome.behavioral.poker_strategy
                if ps is None:
                    continue
                strat = ps.value
                if strat is None or not isinstance(strat, ComposablePokerStrategy):
                    continue
                if param_key in strat.parameters:
                    values.append(strat.parameters[param_key])

            if not values:
                out.append({
                    "key": f"poker_{param_key}",
                    "label": f"Poker {human_label}",
                    "category": "behavioral",
                    "discrete": False,
                    "allowed_min": p_min,
                    "allowed_max": p_max,
                    "min": 0.0, "max": 0.0, "median": 0.0,
                    "bins": [], "bin_edges": [],
                    "meta": meta_dict
                })
                continue

            v_min = min(values)
            v_max = max(values)
            v_median = median(values)
            bins, edges = create_histogram(values, p_min, p_max, num_bins=12)

            out.append({
                "key": f"poker_{param_key}",
                "label": f"Poker {human_label}",
                "category": "behavioral",
                "discrete": False,
                "allowed_min": p_min,
                "allowed_max": p_max,
                "min": float(v_min),
                "max": float(v_max),
                "median": float(v_median),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_dict
            })

        return out

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
        from core.entities.plant import Plant

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
        plants = [
            e for e in self._engine.entities_list if isinstance(e, Plant)
        ]

        return {
            "fish_count": len(fish_list),
            "fish_energy": sum(fish.energy for fish in fish_list),
            "food_count": len(regular_food_list),
            "food_energy": sum(food.energy for food in regular_food_list),
            "live_food_count": len(live_food_list),
            "live_food_energy": sum(food.energy for food in live_food_list),
            "plant_count": len(plants),
            "plant_energy": sum(plant.energy for plant in plants),
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

        # Dynamic gene distributions for the UI (physical + behavioral)
        built_dists = self._build_gene_distributions()
        
        # Merge composable behavior traits into behavioral list
        composable_dists = self._get_composable_behavior_distributions(self._engine.get_fish_list())
        built_dists["behavioral"].extend(composable_dists)
        
        # Merge composable poker strategy traits into behavioral list
        poker_dists = self._get_poker_strategy_distributions(self._engine.get_fish_list())
        built_dists["behavioral"].extend(poker_dists)

        stats["gene_distributions"] = built_dists

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
        bins, edges = create_histogram(
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
                bins, edges = create_histogram(
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
                bins, edges = create_histogram(
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
                bins, edges = create_histogram(values, allowed_min, allowed_max, num_bins=12)
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
                bins, edges = create_histogram(values, allowed_min, allowed_max, num_bins=12)
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
                bins, edges = create_histogram(values, -0.5, allowed_max + 0.5, num_bins=FISH_TEMPLATE_COUNT)
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
                bins, edges = create_histogram(values, -0.5, allowed_max + 0.5, num_bins=FISH_PATTERN_COUNT)
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
                bins, edges = create_histogram(values, allowed_min, allowed_max, num_bins=10)
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
                bins, edges = create_histogram(values, allowed_min, allowed_max, num_bins=12)
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
