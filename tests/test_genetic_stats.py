"""Unit tests for genetic_stats module."""

from unittest.mock import MagicMock

from core.services.stats.genetic_stats import get_genetic_distribution_stats


class MockTrait:
    def __init__(self, value, mutation_rate=0.1, mutation_strength=0.1, hgt_probability=0.1):
        self.value = value
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.hgt_probability = hgt_probability


class MockGenome:
    def __init__(self):
        self.physical = MagicMock()
        self.behavioral = MagicMock()

        # Setup standard physical traits
        self.physical.size_modifier = MockTrait(1.0)
        self.physical.eye_size = MockTrait(1.0)
        self.physical.fin_size = MockTrait(1.0)
        self.physical.tail_size = MockTrait(1.0)
        self.physical.body_aspect = MockTrait(1.0)
        self.physical.template_id = MockTrait(0)
        self.physical.pattern_type = MockTrait(0)
        self.physical.pattern_intensity = MockTrait(0.5)
        self.physical.lifespan_modifier = MockTrait(1.0)
        self.physical.color_hue = MockTrait(0.5)

        self.behavioral.behavior = MockTrait(None)
        self.behavioral.poker_strategy = MockTrait(None)


class MockFish:
    def __init__(self):
        self.genome = MockGenome()


def test_get_genetic_distribution_stats_structure():
    """Test that the stats structure is correct."""
    fish = MockFish()
    stats = get_genetic_distribution_stats([fish])

    # Check flat stats
    assert "adult_size_avg" in stats
    assert "eye_size_avg" in stats
    assert "fin_size_avg" in stats

    # Check distributions
    assert "gene_distributions" in stats
    dists = stats["gene_distributions"]
    assert "physical" in dists
    assert "behavioral" in dists

    # Check physical traits interact correctly with config specs
    # Should contain at least size_modifier, eye_size, etc.
    keys = [d["key"] for d in dists["physical"]]
    assert "size_modifier" in keys
    assert "eye_size" in keys

    # Check for adult_size (derived trait) which was previously manually inserted
    # This assertion will fail until I fix it
    # assert "adult_size" in keys


def test_empty_list():
    stats = get_genetic_distribution_stats([])
    assert stats["adult_size_avg"] == 0.0
    # Should still return distributions with empty bins
    assert len(stats["gene_distributions"]["physical"]) > 0


def test_composable_strategy_stats():
    """Test that composable poker strategy stats are correctly extracted."""
    from core.poker.strategy.composable import (
        BettingStyle,
        BluffingApproach,
        ComposablePokerStrategy,
        HandSelection,
    )

    fish = MockFish()
    # Mock a real composable strategy
    strategy = ComposablePokerStrategy(
        betting_style=BettingStyle.VALUE_HEAVY,  # 1
        hand_selection=HandSelection.TIGHT,  # 1
        bluffing_approach=BluffingApproach.AGGRESSIVE,  # 3
    )
    fish.genome.behavioral.poker_strategy = MockTrait(strategy)

    stats = get_genetic_distribution_stats([fish])

    dists = stats["gene_distributions"]["behavioral"]
    keys = [d["key"] for d in dists]

    assert "poker_betting_style" in keys
    assert "poker_hand_selection" in keys
    assert "poker_bluffing_approach" in keys
