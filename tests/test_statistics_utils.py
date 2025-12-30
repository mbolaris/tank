"""Unit tests for statistics_utils module.

Tests the core statistical functions to ensure they handle
edge cases correctly and provide consistent results.
"""

from core.statistics_utils import (
    GeneDistribution,
    MetaStats,
    compute_meta_stats,
    create_histogram,
    descriptive_stats,
    safe_mean_std,
)


class TestSafeMeanStd:
    """Tests for safe_mean_std function."""

    def test_empty_list_returns_zeros(self):
        """Empty list should return (0.0, 0.0)."""
        mean, std = safe_mean_std([])
        assert mean == 0.0
        assert std == 0.0

    def test_single_value_has_zero_std(self):
        """Single value should have mean=value, std=0."""
        mean, std = safe_mean_std([5.0])
        assert mean == 5.0
        assert std == 0.0

    def test_two_values(self):
        """Two values should calculate correct mean and std."""
        mean, std = safe_mean_std([0.0, 10.0])
        assert mean == 5.0
        assert std > 0  # Should be ~7.07

    def test_multiple_values(self):
        """Multiple values should calculate correct statistics."""
        mean, std = safe_mean_std([1.0, 2.0, 3.0, 4.0, 5.0])
        assert mean == 3.0
        assert 1.5 < std < 1.6  # Should be ~1.58

    def test_returns_floats(self):
        """Return values should always be floats."""
        mean, std = safe_mean_std([1, 2, 3])  # integers
        assert isinstance(mean, float)
        assert isinstance(std, float)


class TestDescriptiveStats:
    """Tests for descriptive_stats function."""

    def test_empty_list(self):
        """Empty list should return zeroed stats with count=0."""
        stats = descriptive_stats([])
        assert stats.count == 0
        assert stats.mean == 0.0
        assert stats.std == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0
        assert stats.median == 0.0

    def test_single_value(self):
        """Single value should set min=max=median=mean=value."""
        stats = descriptive_stats([42.0])
        assert stats.count == 1
        assert stats.mean == 42.0
        assert stats.min == 42.0
        assert stats.max == 42.0
        assert stats.median == 42.0
        assert stats.std == 0.0

    def test_multiple_values(self):
        """Multiple values should calculate all statistics."""
        stats = descriptive_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert stats.count == 5
        assert stats.mean == 3.0
        assert stats.min == 1.0
        assert stats.max == 5.0
        assert stats.median == 3.0
        assert stats.std > 0


class TestMetaStats:
    """Tests for MetaStats dataclass."""

    def test_default_values(self):
        """Default MetaStats should have all zeros."""
        meta = MetaStats()
        assert meta.mut_rate_mean == 0.0
        assert meta.mut_strength_mean == 0.0
        assert meta.hgt_prob_mean == 0.0

    def test_to_dict(self):
        """to_dict should return all fields."""
        meta = MetaStats(
            mut_rate_mean=0.1,
            mut_rate_std=0.02,
            mut_strength_mean=0.3,
            mut_strength_std=0.04,
            hgt_prob_mean=0.05,
            hgt_prob_std=0.01,
        )
        d = meta.to_dict()
        assert d["mut_rate_mean"] == 0.1
        assert d["mut_strength_mean"] == 0.3
        assert d["hgt_prob_mean"] == 0.05
        assert len(d) == 6


class TestComputeMetaStats:
    """Tests for compute_meta_stats function."""

    def test_empty_list(self):
        """Empty trait list should return default MetaStats."""
        meta = compute_meta_stats([])
        assert meta.mut_rate_mean == 0.0

    def test_with_mock_traits(self):
        """Should extract meta values from trait-like objects."""

        class MockTrait:
            def __init__(self, rate, strength, hgt):
                self.mutation_rate = rate
                self.mutation_strength = strength
                self.hgt_probability = hgt

        traits = [
            MockTrait(0.1, 0.2, 0.05),
            MockTrait(0.1, 0.2, 0.05),
        ]
        meta = compute_meta_stats(traits)
        assert meta.mut_rate_mean == 0.1
        assert meta.mut_strength_mean == 0.2
        assert meta.hgt_prob_mean == 0.05


class TestGeneDistribution:
    """Tests for GeneDistribution dataclass."""

    def test_default_values(self):
        """Required fields should be set, optional should default."""
        dist = GeneDistribution(
            key="test_gene",
            label="Test Gene",
            category="physical",
            discrete=False,
            allowed_min=0.0,
            allowed_max=1.0,
        )
        assert dist.key == "test_gene"
        assert dist.min == 0.0
        assert dist.bins == []
        assert isinstance(dist.meta, MetaStats)

    def test_to_dict(self):
        """to_dict should include all fields and nested meta."""
        dist = GeneDistribution(
            key="size",
            label="Size",
            category="physical",
            discrete=False,
            allowed_min=0.5,
            allowed_max=2.0,
            min=0.7,
            max=1.8,
            median=1.2,
            bins=[1, 2, 3],
            bin_edges=[0.5, 1.0, 1.5, 2.0],
        )
        d = dist.to_dict()
        assert d["key"] == "size"
        assert d["bins"] == [1, 2, 3]
        assert "meta" in d
        assert isinstance(d["meta"], dict)


class TestCreateHistogram:
    """Tests for create_histogram function."""

    def test_empty_values(self):
        """Empty values should return empty bins and edges."""
        bins, edges = create_histogram([], 0, 10)
        assert bins == []
        assert edges == []

    def test_basic_histogram(self):
        """Should create correct number of bins and edges."""
        values = [1, 2, 3, 4, 5]
        bins, edges = create_histogram(values, 0, 10, num_bins=5)
        assert len(bins) == 5
        assert len(edges) == 6  # n+1 edges for n bins
        assert sum(bins) == 5  # All values counted

    def test_values_at_boundaries(self):
        """Values at boundaries should be counted correctly."""
        values = [0.0, 5.0, 9.99]
        bins, edges = create_histogram(values, 0, 10, num_bins=2)
        assert sum(bins) == 3

    def test_single_bin(self):
        """Single bin should count all values."""
        values = [1, 2, 3, 4, 5]
        bins, edges = create_histogram(values, 0, 10, num_bins=1)
        assert bins == [5]
        assert len(edges) == 2
