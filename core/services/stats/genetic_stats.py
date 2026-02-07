"""Genetic statistics calculation.

This module provides functions to calculate genetic distribution statistics
for the simulation, extracting this logic from the main StatsCalculator.
"""

import logging
import statistics
from typing import TYPE_CHECKING, Any, Dict, List

logger = logging.getLogger(__name__)

from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.services.stats.utils import humanize_gene_label
from core.statistics_utils import compute_meta_stats, create_histogram

if TYPE_CHECKING:
    from core.entities import Fish


def get_genetic_distribution_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    """Get genetic trait distribution statistics with histograms.

    Args:
        fish_list: List of fish entities to analyze

    Returns:
        Dictionary with genetic stats (adult size, eye size, fin size, etc.)
    """
    stats: Dict[str, Any] = {}

    # Calculate individual physical trait stats
    # We use specific helpers for the main dashboard widgets that expect specific formats
    stats.update(_get_adult_size_stats(fish_list))
    stats.update(_get_eye_size_stats(fish_list))
    stats.update(_get_fin_size_stats(fish_list))
    stats.update(_get_tail_size_stats(fish_list))
    stats.update(_get_body_aspect_stats(fish_list))
    stats.update(_get_template_id_stats(fish_list))
    stats.update(_get_pattern_type_stats(fish_list))
    stats.update(_get_pattern_intensity_stats(fish_list))
    stats.update(_get_lifespan_modifier_stats(fish_list))

    # Dynamic gene distributions for the UI (physical + behavioral)
    built_dists = _build_gene_distributions(fish_list)

    # Merge composable behavior traits into behavioral list
    composable_dists = _get_composable_behavior_distributions(fish_list)
    built_dists["behavioral"].extend(composable_dists)

    # Merge composable poker strategy traits into behavioral list
    poker_dists = _get_poker_strategy_distributions(fish_list)
    built_dists["behavioral"].extend(poker_dists)

    stats["gene_distributions"] = built_dists

    return stats


def _get_trait_values(
    fish_list: List["Fish"], trait_name: str, category: str = "physical"
) -> List[float]:
    """Extract numeric values for a specific genetic trait from a list of fish.

    Handles GeneticTrait wrappers by accessing .value property.
    """
    values = []
    for f in fish_list:
        if not hasattr(f, "genome"):
            continue

        container = getattr(f.genome, category, None)
        if not container:
            continue

        trait = getattr(container, trait_name, None)
        if trait is not None and hasattr(trait, "value"):
            values.append(float(trait.value))
        elif isinstance(trait, (int, float)):
            values.append(float(trait))

    return values


def _compute_numeric_stats(
    values: List[float], min_val: float, max_val: float, key_prefix: str
) -> Dict[str, Any]:
    """Compute standard stats and histogram for a list of values."""
    if not values:
        return {
            f"{key_prefix}_min": 0.0,
            f"{key_prefix}_max": 0.0,
            f"{key_prefix}_avg": 0.0,
            f"{key_prefix}_median": 0.0,
            f"{key_prefix}_bins": [],
            f"{key_prefix}_bin_edges": [],
        }

    bins, edges = create_histogram(values, min_val, max_val, num_bins=10)

    return {
        f"{key_prefix}_min": min(values),
        f"{key_prefix}_max": max(values),
        f"{key_prefix}_avg": sum(values) / len(values),
        f"{key_prefix}_median": statistics.median(values),
        f"{key_prefix}_bins": bins,
        f"{key_prefix}_bin_edges": edges,
    }


def _get_adult_size_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import FISH_ADULT_SIZE, FISH_SIZE_MODIFIER_MAX, FISH_SIZE_MODIFIER_MIN

    # Calculate actual size (base * modifier)
    values = []
    for f in fish_list:
        if hasattr(f, "genome") and hasattr(f.genome.physical, "size_modifier"):
            mod = f.genome.physical.size_modifier.value
            values.append(FISH_ADULT_SIZE * mod)

    min_size = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN
    max_size = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX

    return _compute_numeric_stats(values, min_size, max_size, "adult_size")


def _get_eye_size_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import EYE_SIZE_MAX, EYE_SIZE_MIN

    values = _get_trait_values(fish_list, "eye_size", "physical")
    return _compute_numeric_stats(values, EYE_SIZE_MIN, EYE_SIZE_MAX, "eye_size")


def _get_fin_size_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    # Hardcoded bounds from trait specs if not in config
    values = _get_trait_values(fish_list, "fin_size", "physical")
    return _compute_numeric_stats(values, 0.5, 2.0, "fin_size")


def _get_tail_size_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    values = _get_trait_values(fish_list, "tail_size", "physical")
    return _compute_numeric_stats(values, 0.5, 2.0, "tail_size")


def _get_body_aspect_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import BODY_ASPECT_MAX, BODY_ASPECT_MIN

    values = _get_trait_values(fish_list, "body_aspect", "physical")
    return _compute_numeric_stats(values, BODY_ASPECT_MIN, BODY_ASPECT_MAX, "body_aspect")


def _get_template_id_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import FISH_TEMPLATE_COUNT

    values = _get_trait_values(fish_list, "template_id", "physical")
    # For discrete values, use min/max of possible range for histogram
    return _compute_numeric_stats(values, 0, FISH_TEMPLATE_COUNT - 1, "template_id")


def _get_pattern_type_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import FISH_PATTERN_COUNT

    values = _get_trait_values(fish_list, "pattern_type", "physical")
    return _compute_numeric_stats(values, 0, FISH_PATTERN_COUNT - 1, "pattern_type")


def _get_pattern_intensity_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    values = _get_trait_values(fish_list, "pattern_intensity", "physical")
    return _compute_numeric_stats(values, 0.0, 1.0, "pattern_intensity")


def _get_lifespan_modifier_stats(fish_list: List["Fish"]) -> Dict[str, Any]:
    from core.config.fish import LIFESPAN_MODIFIER_MAX, LIFESPAN_MODIFIER_MIN

    values = _get_trait_values(fish_list, "lifespan_modifier", "physical")
    return _compute_numeric_stats(
        values, LIFESPAN_MODIFIER_MIN, LIFESPAN_MODIFIER_MAX, "lifespan_modifier"
    )


def _build_gene_distributions(fish_list: List["Fish"]) -> Dict[str, Any]:
    """Build dynamic gene distributions for frontend."""

    def meta_for_traits(traits: List[Any]) -> Dict[str, float]:
        return compute_meta_stats(traits).to_dict()

    def build_from_specs(
        *, category: str, traits_attr: str, specs: List[Any]
    ) -> List[Dict[str, Any]]:
        out = []

        # If no fish, emit empty structures
        if not fish_list:
            for spec in specs:
                out.append(
                    {
                        "key": spec.name,
                        "label": humanize_gene_label(spec.name),
                        "category": category,
                        "discrete": bool(getattr(spec, "discrete", False)),
                        "allowed_min": float(spec.min_val),
                        "allowed_max": float(spec.max_val),
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
            # Collect traits
            traits = []
            for f in fish_list:
                if not hasattr(f, "genome"):
                    continue
                container = getattr(f.genome, traits_attr, None)
                if not container:
                    continue
                trait = getattr(container, spec.name, None)
                if trait:
                    traits.append(trait)

            # Collect numeric values
            values = [float(t.value) for t in traits if hasattr(t, "value")]

            if not values:
                bins: List[int] = []
                edges: List[float] = []
                median_val = min_val = max_val = 0.0
            else:
                bins, edges = create_histogram(values, spec.min_val, spec.max_val, num_bins=20)
                median_val = statistics.median(values)
                min_val = min(values)
                max_val = max(values)

            # Evolvability meta-stats
            meta = meta_for_traits(traits)

            out.append(
                {
                    "key": spec.name,
                    "label": humanize_gene_label(spec.name),
                    "category": category,
                    "discrete": bool(getattr(spec, "discrete", False)),
                    "allowed_min": float(spec.min_val),
                    "allowed_max": float(spec.max_val),
                    "min": min_val,
                    "max": max_val,
                    "median": median_val,
                    "bins": bins,
                    "bin_edges": edges,
                    "meta": meta,
                }
            )
        return out

    physical = build_from_specs(
        category="physical", traits_attr="physical", specs=PHYSICAL_TRAIT_SPECS
    )
    behavioral = build_from_specs(
        category="behavioral", traits_attr="behavioral", specs=BEHAVIORAL_TRAIT_SPECS
    )

    # Derived Adult Size Distribution
    try:
        from core.config.fish import FISH_ADULT_SIZE, FISH_SIZE_MODIFIER_MAX, FISH_SIZE_MODIFIER_MIN

        allowed_min = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN)
        allowed_max = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX)

        size_traits = []
        adult_sizes = []
        for f in fish_list:
            if (
                hasattr(f, "genome")
                and hasattr(f.genome, "physical")
                and hasattr(f.genome.physical, "size_modifier")
            ):
                t = f.genome.physical.size_modifier
                size_traits.append(t)
                adult_sizes.append(FISH_ADULT_SIZE * float(t.value))

        if adult_sizes:
            bins, edges = create_histogram(adult_sizes, allowed_min, allowed_max, num_bins=16)
            median_val = statistics.median(adult_sizes)
            min_val, max_val = min(adult_sizes), max(adult_sizes)
        else:
            bins, edges = [], []
            median_val = min_val = max_val = 0.0

        physical.insert(
            0,
            {
                "key": "adult_size",
                "label": humanize_gene_label("adult_size"),
                "category": "physical",
                "discrete": False,
                "allowed_min": allowed_min,
                "allowed_max": allowed_max,
                "min": min_val,
                "max": max_val,
                "median": median_val,
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_for_traits(size_traits),
            },
        )
    except Exception:
        logger.debug("Failed to compute size distribution stats", exc_info=True)

    return {
        "physical": physical,
        "behavioral": behavioral,
    }


def _get_composable_behavior_distributions(fish_list: List["Fish"]) -> List[Dict[str, Any]]:
    """Get distributions for composable behavior system."""
    if not fish_list:
        return []

    try:
        from core.algorithms.composable import ComposableBehavior
        from core.algorithms.registry import SUB_BEHAVIOR_COUNTS
    except ImportError:
        return []

    def meta_for_traits(traits: List[Any]) -> Dict[str, float]:
        return compute_meta_stats(traits).to_dict()

    distributions = []

    # 1. Threat Response
    threat_vals = []
    threat_traits = []

    for f in fish_list:
        if not hasattr(f, "genome"):
            continue
        trait = getattr(f.genome.behavioral, "behavior", None)
        if trait is None:
            continue
        behavior = trait.value

        if isinstance(behavior, ComposableBehavior) and behavior.threat_response:
            threat_vals.append(behavior.threat_response.value)
            threat_traits.append(trait)

    if threat_vals:
        min_val, max_val = 0, SUB_BEHAVIOR_COUNTS["threat_response"] - 1
        bins, edges = create_histogram(threat_vals, min_val, max_val, num_bins=max_val + 1)

        distributions.append(
            {
                "key": "threat_response",
                "label": "Threat Response",
                "category": "behavioral",
                "discrete": True,
                "allowed_min": min_val,
                "allowed_max": max_val,
                "min": min(threat_vals),
                "max": max(threat_vals),
                "median": statistics.median(threat_vals),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_for_traits(threat_traits),
            }
        )

    # 2. Food Approach
    food_vals = []
    food_traits = []

    for f in fish_list:
        if not hasattr(f, "genome"):
            continue
        trait = getattr(f.genome.behavioral, "behavior", None)
        if trait is None:
            continue
        behavior = trait.value

        if isinstance(behavior, ComposableBehavior) and behavior.food_approach:
            food_vals.append(behavior.food_approach.value)
            food_traits.append(trait)

    if food_vals:
        min_val, max_val = 0, SUB_BEHAVIOR_COUNTS["food_approach"] - 1
        bins, edges = create_histogram(food_vals, min_val, max_val, num_bins=max_val + 1)

        distributions.append(
            {
                "key": "food_approach",
                "label": "Food Approach",
                "category": "behavioral",
                "discrete": True,
                "allowed_min": min_val,
                "allowed_max": max_val,
                "min": min(food_vals),
                "max": max(food_vals),
                "median": statistics.median(food_vals),
                "bins": bins,
                "bin_edges": edges,
                "meta": meta_for_traits(food_traits),
            }
        )

    return distributions


def _get_poker_strategy_distributions(fish_list: List["Fish"]) -> List[Dict[str, Any]]:
    """Get distributions for poker strategy traits."""
    if not fish_list:
        return []

    try:
        from core.poker.strategy.composable import ComposablePokerStrategy
    except ImportError:
        return []

    def meta_for_traits(traits: List[Any]) -> Dict[str, float]:
        return compute_meta_stats(traits).to_dict()

    betting_vals: List[int] = []
    hand_vals: List[int] = []
    bluff_vals: List[int] = []
    traits: List[Any] = []

    for f in fish_list:
        if not hasattr(f, "genome"):
            continue
        if not hasattr(f.genome.behavioral, "poker_strategy"):
            continue

        trait = getattr(f.genome.behavioral, "poker_strategy", None)
        if trait is None:
            continue
        strategy = trait.value

        if isinstance(strategy, ComposablePokerStrategy):
            betting_vals.append(strategy.betting_style.value)
            hand_vals.append(strategy.hand_selection.value)
            bluff_vals.append(strategy.bluffing_approach.value)
            traits.append(trait)

    if not traits:
        return []

    def build_dist(key: str, label: str, values: List[int]) -> Dict[str, Any]:
        if not values:
            return {}
        min_val, max_val = 0, 3
        bins, edges = create_histogram(values, min_val, max_val, num_bins=4)
        return {
            "key": key,
            "label": label,
            "category": "behavioral",
            "discrete": True,
            "allowed_min": min_val,
            "allowed_max": max_val,
            "min": min(values),
            "max": max(values),
            "median": statistics.median(values),
            "bins": bins,
            "bin_edges": edges,
            "meta": meta_for_traits(traits),
        }

    dists = []
    if hand_vals:
        dists.append(build_dist("poker_hand_selection", "Poker Hand Selection", hand_vals))
    if betting_vals:
        dists.append(build_dist("poker_betting_style", "Poker Betting Style", betting_vals))
    if bluff_vals:
        dists.append(build_dist("poker_bluffing_approach", "Poker Bluffing Approach", bluff_vals))

    return dists
