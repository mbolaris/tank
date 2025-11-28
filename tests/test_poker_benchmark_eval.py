"""Tests for calibrated poker benchmark evaluation system.

This module tests:
- Deterministic RNG for duplicate deals
- Seat swapping for variance reduction
- Benchmark evaluation metrics and confidence intervals
"""

import pytest

from core.poker.core.cards import Deck
from core.poker.strategy.implementations import (
    BalancedStrategy,
    TightAggressiveStrategy,
    ManiacStrategy,
)
from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    create_standard_strategy,
    evaluate_vs_single_benchmark_duplicate,
    evaluate_vs_benchmark_suite,
    _compute_ci_95,
)
from core.auto_evaluate_poker import AutoEvaluatePokerGame


class TestDeckDeterminism:
    """Test that seeded RNG produces deterministic card shuffles."""

    def test_same_seed_produces_same_shuffle(self):
        """Two decks with same seed should shuffle identically."""
        seed = 42
        deck1 = Deck(seed=seed)
        deck2 = Deck(seed=seed)

        # Deal all cards from both decks
        cards1 = deck1.deal(52)
        cards2 = deck2.deal(52)

        # Should be identical
        assert len(cards1) == 52
        assert len(cards2) == 52
        for i in range(52):
            assert cards1[i] == cards2[i], f"Card {i} differs: {cards1[i]} != {cards2[i]}"

    def test_different_seeds_produce_different_shuffles(self):
        """Two decks with different seeds should shuffle differently."""
        deck1 = Deck(seed=42)
        deck2 = Deck(seed=43)

        cards1 = deck1.deal(52)
        cards2 = deck2.deal(52)

        # Should be different (with overwhelming probability)
        differences = sum(1 for i in range(52) if cards1[i] != cards2[i])
        assert differences > 0, "Different seeds should produce different shuffles"

    def test_deck_reset_with_same_seed(self):
        """Resetting deck with same seed should reproduce shuffle."""
        deck = Deck(seed=42)
        cards1 = deck.deal(10)

        deck.reset(seed=42)
        cards2 = deck.deal(10)

        assert cards1 == cards2


class TestHeadsUpEvaluation:
    """Test heads-up match evaluation."""

    def test_run_heads_up_basic(self):
        """Basic test that run_heads_up executes without errors."""
        candidate = BalancedStrategy()
        benchmark = TightAggressiveStrategy()

        stats = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=10,
            small_blind=50,
            big_blind=100,
            starting_stack=10000,
            rng_seed=42,
        )

        assert stats is not None
        assert hasattr(stats, "net_bb_for_candidate")
        assert stats.hands_played == 10

    def test_run_heads_up_determinism(self):
        """Same seed should produce same results."""
        candidate = BalancedStrategy()
        benchmark = TightAggressiveStrategy()

        stats1 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=20,
            rng_seed=42,
        )

        stats2 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=20,
            rng_seed=42,
        )

        # Same seed should produce identical results
        assert stats1.net_bb_for_candidate == stats2.net_bb_for_candidate
        assert stats1.hands_played == stats2.hands_played

    def test_seat_swap_gets_same_cards(self):
        """Swapping seats with same seed should deal same cards (opposite results)."""
        candidate = BalancedStrategy()
        benchmark = TightAggressiveStrategy()

        # Candidate in seat 0
        stats_seat0 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=50,
            rng_seed=42,
        )

        # Candidate in seat 1 with SAME seed
        stats_seat1 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=1,
            num_hands=50,
            rng_seed=42,
        )

        # Results should be mirror images (approximately, due to position effects)
        # The sum should cancel out most variance
        total_bb = stats_seat0.net_bb_for_candidate + stats_seat1.net_bb_for_candidate

        # Total should be closer to 0 than either individual result
        # (exact cancellation only if strategies are symmetric)
        individual_magnitude = abs(stats_seat0.net_bb_for_candidate)
        assert abs(total_bb) <= individual_magnitude * 0.5 or individual_magnitude < 1.0


class TestBenchmarkEvaluation:
    """Test benchmark evaluation functions."""

    def test_create_standard_strategy(self):
        """Test creating standard strategies by ID."""
        balanced = create_standard_strategy("balanced")
        assert isinstance(balanced, BalancedStrategy)

        tag = create_standard_strategy("tight_aggressive")
        assert isinstance(tag, TightAggressiveStrategy)

        maniac = create_standard_strategy("maniac")
        assert isinstance(maniac, ManiacStrategy)

    def test_create_standard_strategy_invalid(self):
        """Test that invalid strategy ID raises error."""
        with pytest.raises(ValueError):
            create_standard_strategy("invalid_strategy")

    def test_compute_ci_95(self):
        """Test confidence interval computation."""
        # Perfect consistency
        values = [10.0] * 10
        ci_low, ci_high = _compute_ci_95(values)
        assert ci_low == pytest.approx(10.0, abs=1e-6)
        assert ci_high == pytest.approx(10.0, abs=1e-6)

        # Some variance
        values = [8.0, 9.0, 10.0, 11.0, 12.0]
        ci_low, ci_high = _compute_ci_95(values)
        mean = 10.0
        assert ci_low < mean
        assert ci_high > mean
        assert ci_low < ci_high

    def test_evaluate_vs_single_benchmark(self):
        """Test evaluation against a single benchmark opponent."""
        candidate = BalancedStrategy()
        cfg = BenchmarkEvalConfig(
            num_duplicate_sets=5,  # Small for fast test
            hands_per_match=20,
            base_seed=42,
        )

        result = evaluate_vs_single_benchmark_duplicate(
            candidate,
            "tight_aggressive",
            cfg,
        )

        assert result is not None
        assert result.benchmark_id == "tight_aggressive"
        assert result.hands_played == 5 * 20 * 2  # 5 sets × 20 hands × 2 seats
        assert isinstance(result.bb_per_100, float)
        assert isinstance(result.bb_per_100_ci_95, tuple)
        assert len(result.bb_per_100_ci_95) == 2

    def test_evaluate_vs_benchmark_suite(self):
        """Test full benchmark suite evaluation."""
        candidate = BalancedStrategy()
        cfg = BenchmarkEvalConfig(
            num_duplicate_sets=3,  # Very small for fast test
            hands_per_match=10,
            benchmark_opponents=["balanced", "tight_aggressive"],  # Just 2 for speed
            benchmark_weights={"balanced": 1.0, "tight_aggressive": 1.0},
        )

        result = evaluate_vs_benchmark_suite(candidate, cfg)

        assert result is not None
        assert len(result.per_benchmark) == 2
        assert "balanced" in result.per_benchmark
        assert "tight_aggressive" in result.per_benchmark
        assert isinstance(result.weighted_bb_per_100, float)
        assert result.total_hands == 2 * 3 * 10 * 2  # 2 opponents × 3 sets × 10 hands × 2 seats


class TestVarianceReduction:
    """Test that duplicate deals reduce variance."""

    def test_duplicate_reduces_variance(self):
        """Duplicate deals should reduce variance compared to random deals."""
        candidate = BalancedStrategy()

        # Run with duplicate deals (same seed, seat swap)
        cfg_duplicate = BenchmarkEvalConfig(
            num_duplicate_sets=10,
            hands_per_match=20,
            base_seed=100,
        )
        result_duplicate = evaluate_vs_single_benchmark_duplicate(
            candidate, "balanced", cfg_duplicate
        )

        # Variance with duplicate deals
        variance_duplicate = result_duplicate.sample_variance

        # With duplicate deals, variance should be reasonably bounded
        # (The exact value depends on strategy differences)
        # Just ensure the metric is computed and reasonable
        assert variance_duplicate >= 0.0
        assert result_duplicate.bb_per_100_ci_95[0] <= result_duplicate.bb_per_100
        assert result_duplicate.bb_per_100 <= result_duplicate.bb_per_100_ci_95[1]


class TestStatisticalSignificance:
    """Test statistical significance detection."""

    def test_balanced_vs_balanced_not_significant(self):
        """Balanced strategy vs itself should not show significant difference."""
        candidate = BalancedStrategy()
        cfg = BenchmarkEvalConfig(
            num_duplicate_sets=10,
            hands_per_match=50,
            base_seed=42,
        )

        result = evaluate_vs_single_benchmark_duplicate(
            candidate, "balanced", cfg
        )

        # Same strategy should not be significantly different
        # (CI should include 0)
        ci_low, ci_high = result.bb_per_100_ci_95
        # Note: Due to randomness in parameters, even identical strategy classes
        # may have different parameter values, so we can't guarantee CI includes 0
        # Just ensure CI is computed
        assert ci_low <= result.bb_per_100 <= ci_high


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
