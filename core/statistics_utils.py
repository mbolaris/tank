"""Reusable statistics calculation utilities.

This module provides safe, well-documented statistical helpers that
handle edge cases (empty lists, single values) consistently across
the codebase.

Design Principles:
- All functions handle empty lists gracefully (return zeros)
- Single-value lists return 0.0 for standard deviation
- Types are explicit and well-documented
- Functions are pure and side-effect free
"""

from dataclasses import dataclass, field
from statistics import mean, median, stdev
from typing import Any
from collections.abc import Sequence


@dataclass(frozen=True)
class DescriptiveStats:
    """Basic descriptive statistics for a dataset.

    Attributes:
        mean: Arithmetic mean of values
        std: Sample standard deviation (0.0 if n <= 1)
        min: Minimum value
        max: Maximum value
        median: Median value
        count: Number of values
    """

    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    median: float = 0.0
    count: int = 0


@dataclass
class MetaStats:
    """Meta-genetic statistics for a trait population.

    Tracks the mutation parameters of traits across the population,
    which is essential for observing meta-evolution (evolution of evolvability).

    Attributes:
        mut_rate_mean: Average mutation rate across population
        mut_rate_std: Standard deviation of mutation rate
        mut_strength_mean: Average mutation strength
        mut_strength_std: Standard deviation of mutation strength
        hgt_prob_mean: Average horizontal gene transfer probability
        hgt_prob_std: Standard deviation of HGT probability
    """

    mut_rate_mean: float = 0.0
    mut_rate_std: float = 0.0
    mut_strength_mean: float = 0.0
    mut_strength_std: float = 0.0
    hgt_prob_mean: float = 0.0
    hgt_prob_std: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mut_rate_mean": self.mut_rate_mean,
            "mut_rate_std": self.mut_rate_std,
            "mut_strength_mean": self.mut_strength_mean,
            "mut_strength_std": self.mut_strength_std,
            "hgt_prob_mean": self.hgt_prob_mean,
            "hgt_prob_std": self.hgt_prob_std,
        }


@dataclass
class GeneDistribution:
    """Distribution data for a single gene.

    Contains everything needed to render a gene distribution histogram
    in the frontend, including statistical summaries and meta-genetic info.

    Attributes:
        key: Internal identifier for the gene (e.g., 'adult_size')
        label: Human-readable label (e.g., 'Adult Size')
        category: 'physical' or 'behavioral'
        discrete: Whether the gene is discrete (enum) or continuous
        allowed_min: Minimum allowed value from trait spec
        allowed_max: Maximum allowed value from trait spec
        min: Observed minimum in population
        max: Observed maximum in population
        median: Observed median in population
        bins: Histogram bin counts
        bin_edges: Histogram bin edges
        meta: Meta-genetic statistics for this trait
    """

    key: str
    label: str
    category: str
    discrete: bool
    allowed_min: float
    allowed_max: float
    min: float = 0.0
    max: float = 0.0
    median: float = 0.0
    bins: list[int] = field(default_factory=list)
    bin_edges: list[float] = field(default_factory=list)
    meta: MetaStats = field(default_factory=MetaStats)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "label": self.label,
            "category": self.category,
            "discrete": self.discrete,
            "allowed_min": self.allowed_min,
            "allowed_max": self.allowed_max,
            "min": self.min,
            "max": self.max,
            "median": self.median,
            "bins": self.bins,
            "bin_edges": self.bin_edges,
            "meta": self.meta.to_dict(),
        }


def safe_mean_std(values: list[float]) -> tuple[float, float]:
    """Calculate mean and standard deviation safely.

    Handles edge cases consistently:
    - Empty list: returns (0.0, 0.0)
    - Single value: returns (value, 0.0) - no std with n=1
    - Multiple values: returns (mean, sample_stdev)

    Args:
        values: List of numeric values

    Returns:
        Tuple of (mean, standard_deviation)

    Example:
        >>> safe_mean_std([1.0, 2.0, 3.0])
        (2.0, 1.0)
        >>> safe_mean_std([])
        (0.0, 0.0)
        >>> safe_mean_std([5.0])
        (5.0, 0.0)
    """
    if not values:
        return 0.0, 0.0
    m = mean(values)
    s = stdev(values) if len(values) > 1 else 0.0
    return float(m), float(s)


def descriptive_stats(values: list[float]) -> DescriptiveStats:
    """Calculate comprehensive descriptive statistics.

    Args:
        values: List of numeric values

    Returns:
        DescriptiveStats dataclass with all statistics

    Example:
        >>> stats = descriptive_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> stats.mean
        3.0
        >>> stats.min
        1.0
    """
    if not values:
        return DescriptiveStats()
    m, s = safe_mean_std(values)
    return DescriptiveStats(
        mean=m,
        std=s,
        min=min(values),
        max=max(values),
        median=median(values),
        count=len(values),
    )


def compute_meta_stats(traits: list[Any]) -> MetaStats:
    """Calculate meta-genetic statistics from a list of traits.

    Each trait is expected to have mutation_rate, mutation_strength,
    and hgt_probability attributes.

    Args:
        traits: List of GeneticTrait objects

    Returns:
        MetaStats with population-level mutation statistics
    """
    if not traits:
        return MetaStats()

    rates = [float(getattr(t, "mutation_rate", 1.0)) for t in traits]
    strengths = [float(getattr(t, "mutation_strength", 1.0)) for t in traits]
    hgts = [float(getattr(t, "hgt_probability", 0.1)) for t in traits]

    r_mean, r_std = safe_mean_std(rates)
    s_mean, s_std = safe_mean_std(strengths)
    h_mean, h_std = safe_mean_std(hgts)

    return MetaStats(
        mut_rate_mean=r_mean,
        mut_rate_std=r_std,
        mut_strength_mean=s_mean,
        mut_strength_std=s_std,
        hgt_prob_mean=h_mean,
        hgt_prob_std=h_std,
    )


def create_histogram(
    values: Sequence[float],
    range_min: float,
    range_max: float,
    num_bins: int = 12,
) -> tuple[list[int], list[float]]:
    """Create a histogram from a list of values.

    Args:
        values: Data values to bin
        range_min: Minimum value for histogram range
        range_max: Maximum value for histogram range
        num_bins: Number of bins (default 12)

    Returns:
        Tuple of (bin_counts, bin_edges)

    Example:
        >>> bins, edges = create_histogram([1, 2, 3, 4, 5], 0, 10, num_bins=5)
        >>> len(bins)
        5
        >>> len(edges)
        6
    """
    if not values or num_bins <= 0:
        return [], []

    # Ensure range is valid
    if range_max <= range_min:
        range_max = range_min + 1.0

    bin_width = (range_max - range_min) / num_bins
    bins = [0] * num_bins
    edges = [range_min + i * bin_width for i in range(num_bins + 1)]

    for value in values:
        # Clamp value to range
        clamped = max(range_min, min(value, range_max - 0.0001))
        bin_index = int((clamped - range_min) / bin_width)
        bin_index = min(bin_index, num_bins - 1)  # Handle edge case
        bins[bin_index] += 1

    return bins, edges
