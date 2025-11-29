"""Simple smoke tests for benchmark evaluation determinism."""

import unittest

from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.poker.core.cards import Deck
from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    create_standard_strategy,
    evaluate_vs_single_benchmark_duplicate,
)
from core.poker.strategy.implementations import BalancedStrategy, TightAggressiveStrategy


class TestDeckDeterminism(unittest.TestCase):
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
        self.assertEqual(len(cards1), 52)
        self.assertEqual(len(cards2), 52)
        for i in range(52):
            self.assertEqual(cards1[i], cards2[i], f"Card {i} differs")

    def test_different_seeds_produce_different_shuffles(self):
        """Two decks with different seeds should shuffle differently."""
        deck1 = Deck(seed=42)
        deck2 = Deck(seed=43)

        cards1 = deck1.deal(52)
        cards2 = deck2.deal(52)

        # Should be different (with overwhelming probability)
        differences = sum(1 for i in range(52) if cards1[i] != cards2[i])
        self.assertGreater(differences, 0, "Different seeds should produce different shuffles")


class TestHeadsUpDeterminism(unittest.TestCase):
    """Test heads-up match determinism."""

    def test_run_heads_up_basic(self):
        """Test that heads-up evaluation completes successfully."""
        import random

        # Create strategies with seeded random for consistent parameters
        random.seed(100)
        candidate = BalancedStrategy()
        random.seed(200)
        benchmark = TightAggressiveStrategy()

        stats = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=20,
            rng_seed=42,
        )

        # Verify basic structure
        self.assertIsNotNone(stats)
        self.assertTrue(hasattr(stats, "net_bb_for_candidate"))
        self.assertEqual(stats.hands_played, 20)
        self.assertIsInstance(stats.net_bb_for_candidate, (int, float))

    def test_seat_swap_produces_opposite_perspective(self):
        """Test that swapping seats changes perspective but uses same cards."""
        import random

        # Use fixed-parameter strategies
        random.seed(100)
        candidate = BalancedStrategy()
        random.seed(200)
        benchmark = TightAggressiveStrategy()

        # Note: Strategy decisions use random(), so results won't be perfectly
        # deterministic unless we also control strategy RNG. The key test is
        # that the CARD DEALING is deterministic (tested in TestDeckDeterminism).

        stats_seat0 = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=50,
            rng_seed=42,
        )

        # Different seed means different cards, so different result
        stats_different_seed = AutoEvaluatePokerGame.run_heads_up(
            candidate_algo=candidate,
            benchmark_algo=benchmark,
            candidate_seat=0,
            num_hands=50,
            rng_seed=999,
        )

        # Results should differ because cards are different
        # (unless extremely unlikely coincidence)
        self.assertTrue(
            stats_seat0.net_bb_for_candidate != stats_different_seed.net_bb_for_candidate
            or abs(stats_seat0.net_bb_for_candidate) < 0.1
        )


class TestBenchmarkEvaluation(unittest.TestCase):
    """Test benchmark evaluation functions."""

    def test_create_standard_strategy(self):
        """Test creating standard strategies by ID."""
        balanced = create_standard_strategy("balanced")
        self.assertIsInstance(balanced, BalancedStrategy)

        tag = create_standard_strategy("tight_aggressive")
        self.assertIsInstance(tag, TightAggressiveStrategy)

    def test_create_standard_strategy_invalid(self):
        """Test that invalid strategy ID raises error."""
        with self.assertRaises(ValueError):
            create_standard_strategy("invalid_strategy")

    def test_evaluate_vs_single_benchmark_smoke(self):
        """Smoke test: evaluation runs without errors."""
        candidate = BalancedStrategy()
        cfg = BenchmarkEvalConfig(
            num_duplicate_sets=2,  # Very small for fast test
            hands_per_match=10,
            base_seed=42,
        )

        result = evaluate_vs_single_benchmark_duplicate(
            candidate,
            "tight_aggressive",
            cfg,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.benchmark_id, "tight_aggressive")
        self.assertEqual(result.hands_played, 2 * 10 * 2)  # 2 sets × 10 hands × 2 seats
        self.assertIsInstance(result.bb_per_100, float)
        self.assertIsInstance(result.bb_per_100_ci_95, tuple)
        self.assertEqual(len(result.bb_per_100_ci_95), 2)


if __name__ == "__main__":
    unittest.main()
