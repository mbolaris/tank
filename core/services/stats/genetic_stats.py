"""Genetic statistics calculation.

This module provides functions to calculate genetic distribution statistics
for the simulation, extracting this logic from the main StatsCalculator.
"""

import logging
import statistics
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from core.config.fish import (
    BODY_ASPECT_MAX,
    BODY_ASPECT_MIN,
    EYE_SIZE_MAX,
    EYE_SIZE_MIN,
    FISH_ADULT_SIZE,
    FISH_PATTERN_COUNT,
    FISH_SIZE_MODIFIER_MAX,
    FISH_SIZE_MODIFIER_MIN,
    FISH_TEMPLATE_COUNT,
    LIFESPAN_MODIFIER_MAX,
    LIFESPAN_MODIFIER_MIN,
)
from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait import GeneticTrait, TraitSpec
from core.services.stats.utils import humanize_gene_label
from core.statistics_utils import GeneDistribution, compute_meta_stats, create_histogram

if TYPE_CHECKING:
    from core.entities import Fish

# Values that flow into the flat (dynamically-keyed) stats dict, e.g.
# "adult_size_min", "adult_size_bins", ...
StatValue = float | list[int] | list[float]
GeneStatsValue = StatValue | dict[str, list[dict[str, Any]]]


def get_genetic_distribution_stats(fish_list: list["Fish"]) -> dict[str, GeneStatsValue]:
    """Get genetic trait distribution statistics with histograms.

    Args:
        fish_list: List of fish entities to analyze

    Returns:
        Dictionary with genetic stats (adult size, eye size, fin size, etc.)
    """
    stats: dict[str, GeneStatsValue] = {}

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
    built_dists["behavioral"].extend(_get_composable_behavior_distributions(fish_list))

    # Merge composable poker strategy traits into behavioral list
    built_dists["behavioral"].extend(_get_poker_strategy_distributions(fish_list))

    stats["gene_distributions"] = {
        category: [dist.to_dict() for dist in dists] for category, dists in built_dists.items()
    }

    return stats


def _get_trait_values(
    fish_list: list["Fish"], trait_name: str, category: str = "physical"
) -> list[float]:
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
    values: list[float], min_val: float, max_val: float, key_prefix: str
) -> dict[str, StatValue]:
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


def _get_adult_size_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    # Calculate actual size (base * modifier)
    values = []
    for f in fish_list:
        if hasattr(f, "genome") and hasattr(f.genome.physical, "size_modifier"):
            mod = f.genome.physical.size_modifier.value
            values.append(FISH_ADULT_SIZE * mod)

    min_size = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN
    max_size = FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX

    return _compute_numeric_stats(values, min_size, max_size, "adult_size")


def _get_eye_size_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "eye_size", "physical")
    return _compute_numeric_stats(values, EYE_SIZE_MIN, EYE_SIZE_MAX, "eye_size")


def _get_fin_size_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    # Hardcoded bounds from trait specs if not in config
    values = _get_trait_values(fish_list, "fin_size", "physical")
    return _compute_numeric_stats(values, 0.5, 2.0, "fin_size")


def _get_tail_size_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "tail_size", "physical")
    return _compute_numeric_stats(values, 0.5, 2.0, "tail_size")


def _get_body_aspect_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "body_aspect", "physical")
    return _compute_numeric_stats(values, BODY_ASPECT_MIN, BODY_ASPECT_MAX, "body_aspect")


def _get_template_id_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "template_id", "physical")
    # For discrete values, use min/max of possible range for histogram
    return _compute_numeric_stats(values, 0, FISH_TEMPLATE_COUNT - 1, "template_id")


def _get_pattern_type_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "pattern_type", "physical")
    return _compute_numeric_stats(values, 0, FISH_PATTERN_COUNT - 1, "pattern_type")


def _get_pattern_intensity_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "pattern_intensity", "physical")
    return _compute_numeric_stats(values, 0.0, 1.0, "pattern_intensity")


def _get_lifespan_modifier_stats(fish_list: list["Fish"]) -> dict[str, StatValue]:
    values = _get_trait_values(fish_list, "lifespan_modifier", "physical")
    return _compute_numeric_stats(
        values, LIFESPAN_MODIFIER_MIN, LIFESPAN_MODIFIER_MAX, "lifespan_modifier"
    )


def _build_gene_distributions(fish_list: list["Fish"]) -> dict[str, list[GeneDistribution]]:
    """Build dynamic gene distributions for frontend."""

    def build_from_specs(
        *, category: str, traits_attr: str, specs: list[TraitSpec]
    ) -> list[GeneDistribution]:
        out = []

        # If no fish, emit empty structures
        if not fish_list:
            for spec in specs:
                out.append(
                    GeneDistribution(
                        key=spec.name,
                        label=humanize_gene_label(spec.name),
                        category=category,
                        discrete=spec.discrete,
                        allowed_min=float(spec.min_val),
                        allowed_max=float(spec.max_val),
                        meta=compute_meta_stats([]),
                    )
                )
            return out

        for spec in specs:
            # Collect traits
            traits: list[GeneticTrait[Any]] = []
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
                bins: list[int] = []
                edges: list[float] = []
                median_val = min_val = max_val = 0.0
            else:
                bins, edges = create_histogram(values, spec.min_val, spec.max_val, num_bins=20)
                median_val = statistics.median(values)
                min_val = min(values)
                max_val = max(values)

            out.append(
                GeneDistribution(
                    key=spec.name,
                    label=humanize_gene_label(spec.name),
                    category=category,
                    discrete=spec.discrete,
                    allowed_min=float(spec.min_val),
                    allowed_max=float(spec.max_val),
                    min=min_val,
                    max=max_val,
                    median=median_val,
                    bins=bins,
                    bin_edges=edges,
                    meta=compute_meta_stats(traits),
                )
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
        allowed_min = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MIN)
        allowed_max = float(FISH_ADULT_SIZE * FISH_SIZE_MODIFIER_MAX)

        size_traits: list[GeneticTrait[Any]] = []
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
            GeneDistribution(
                key="adult_size",
                label=humanize_gene_label("adult_size"),
                category="physical",
                discrete=False,
                allowed_min=allowed_min,
                allowed_max=allowed_max,
                min=min_val,
                max=max_val,
                median=median_val,
                bins=bins,
                bin_edges=edges,
                meta=compute_meta_stats(size_traits),
            ),
        )
    except Exception:
        logger.debug("Failed to compute size distribution stats", exc_info=True)

    return {
        "physical": physical,
        "behavioral": behavioral,
    }


def _get_composable_behavior_distributions(fish_list: list["Fish"]) -> list[GeneDistribution]:
    """Get distributions for composable behavior system."""
    if not fish_list:
        return []

    try:
        from core.algorithms.composable import ComposableBehavior
        from core.algorithms.registry import SUB_BEHAVIOR_COUNTS
    except ImportError:
        return []

    distributions = []

    # 1. Threat Response
    threat_vals = []
    threat_traits: list[GeneticTrait[Any]] = []

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
            GeneDistribution(
                key="threat_response",
                label="Threat Response",
                category="behavioral",
                discrete=True,
                allowed_min=min_val,
                allowed_max=max_val,
                min=min(threat_vals),
                max=max(threat_vals),
                median=statistics.median(threat_vals),
                bins=bins,
                bin_edges=edges,
                meta=compute_meta_stats(threat_traits),
            )
        )

    # 2. Food Approach
    food_vals = []
    food_traits: list[GeneticTrait[Any]] = []

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
            GeneDistribution(
                key="food_approach",
                label="Food Approach",
                category="behavioral",
                discrete=True,
                allowed_min=min_val,
                allowed_max=max_val,
                min=min(food_vals),
                max=max(food_vals),
                median=statistics.median(food_vals),
                bins=bins,
                bin_edges=edges,
                meta=compute_meta_stats(food_traits),
            )
        )

    return distributions


def _get_poker_strategy_distributions(fish_list: list["Fish"]) -> list[GeneDistribution]:
    """Get distributions for poker strategy traits."""
    if not fish_list:
        return []

    try:
        from core.poker.strategy.composable import ComposablePokerStrategy
    except ImportError:
        return []

    betting_vals: list[int] = []
    hand_vals: list[int] = []
    bluff_vals: list[int] = []
    traits: list[GeneticTrait[Any]] = []

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

    def build_dist(key: str, label: str, values: list[int]) -> GeneDistribution:
        min_val, max_val = 0, 3
        bins, edges = create_histogram(values, min_val, max_val, num_bins=4)
        return GeneDistribution(
            key=key,
            label=label,
            category="behavioral",
            discrete=True,
            allowed_min=min_val,
            allowed_max=max_val,
            min=min(values),
            max=max(values),
            median=statistics.median(values),
            bins=bins,
            bin_edges=edges,
            meta=compute_meta_stats(traits),
        )

    dists = []
    if hand_vals:
        dists.append(build_dist("poker_hand_selection", "Poker Hand Selection", hand_vals))
    if betting_vals:
        dists.append(build_dist("poker_betting_style", "Poker Betting Style", betting_vals))
    if bluff_vals:
        dists.append(build_dist("poker_bluffing_approach", "Poker Bluffing Approach", bluff_vals))

    return dists
