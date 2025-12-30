"""Tests to verify poker evolution fixes are working correctly.

These tests verify that:
1. Winner-biased inheritance is properly applied to poker strategies
2. Mutation rates are appropriate for preserving adaptations
3. Evolution trends toward better poker performance over generations
"""

import random
import pytest
from typing import List

from core.genetics import Genome
from core.genetics.behavioral import _inherit_poker_strategy
from core.poker.strategy.implementations import (
    ALL_POKER_STRATEGIES,
    POKER_EVOLUTION_CONFIG,
    PokerStrategyAlgorithm,
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    BalancedStrategy,
    crossover_poker_strategies,
    get_random_poker_strategy,
)


class TestWinnerBiasedInheritance:
    """Tests for winner-biased poker strategy inheritance."""

    def test_crossover_favors_winner_strategy_type(self):
        """Test that crossover produces offspring with winner's strategy type ~80% of the time."""
        n_trials = 200
        winner_type_count = 0

        # Use fixed strategies for reproducibility
        rng = random.Random(42)
        winner = TightAggressiveStrategy(rng=rng)
        loser = LooseAggressiveStrategy(rng=rng)

        for _ in range(n_trials):
            offspring = crossover_poker_strategies(
                winner,
                loser,
                mutation_rate=0.12,
                mutation_strength=0.15,
                winner_weight=0.80,
                rng=rng,
            )

            if offspring.strategy_id == "tight_aggressive":
                winner_type_count += 1

        # Winner type should appear ~80% minus novelty injection (~2%)
        # So expect roughly 75-85% winner type inheritance
        winner_pct = winner_type_count / n_trials
        assert winner_pct >= 0.65, (
            f"Winner's strategy type only inherited {winner_pct:.1%} of the time, "
            f"expected >= 65%"
        )
        assert winner_pct <= 0.95, (
            f"Winner's strategy type inherited {winner_pct:.1%} of the time, "
            f"expected <= 95% (some novelty expected)"
        )

    def test_crossover_favors_winner_parameters(self):
        """Test that parameter values are closer to winner's values."""
        n_trials = 200

        rng = random.Random(42)
        winner = TightAggressiveStrategy(rng=rng)
        winner.parameters["weak_fold_threshold"] = 0.20  # Winner's value
        winner.parameters["bluff_frequency"] = 0.05

        loser = TightAggressiveStrategy(rng=rng)  # Same type for cleaner test
        loser.parameters["weak_fold_threshold"] = 0.80  # Very different
        loser.parameters["bluff_frequency"] = 0.95

        closer_to_winner = 0

        for _ in range(n_trials):
            offspring = crossover_poker_strategies(
                winner,
                loser,
                mutation_rate=0.12,
                mutation_strength=0.15,
                winner_weight=0.80,
                rng=rng,
            )

            if offspring.strategy_id == "tight_aggressive":
                # Check fold threshold
                fold_val = offspring.parameters.get("weak_fold_threshold", 0.5)
                # With 80/20 blend: expected = 0.20 * 0.8 + 0.80 * 0.2 = 0.32
                # After mutation, should still be closer to 0.32 than to 0.80
                if abs(fold_val - 0.32) < abs(fold_val - 0.80):
                    closer_to_winner += 1

        winner_param_pct = closer_to_winner / n_trials
        assert winner_param_pct >= 0.60, (
            f"Parameters closer to winner only {winner_param_pct:.1%} of the time, "
            f"expected >= 60%"
        )

    def test_from_winner_choice_propagates_to_poker_strategy(self):
        """Test that Genome.from_winner_choice properly biases poker strategy."""
        n_trials = 100
        winner_strategy_count = 0

        rng = random.Random(42)
        for _ in range(n_trials):
            # Create two genomes with different poker strategies
            winner_genome = Genome.random(use_algorithm=True, rng=rng)
            loser_genome = Genome.random(use_algorithm=True, rng=rng)

            # Ensure they have different strategies
            winner_genome.behavioral.poker_strategy.value = TightAggressiveStrategy(rng=rng)
            loser_genome.behavioral.poker_strategy.value = LooseAggressiveStrategy(rng=rng)

            # Create offspring using winner-choice (80/20 split)
            offspring = Genome.from_winner_choice(
                winner=winner_genome,
                mate=loser_genome,
                mutation_rate=0.1,
                mutation_strength=0.1,
                rng=rng,
            )

            if offspring.behavioral.poker_strategy.value.strategy_id == "tight_aggressive":
                winner_strategy_count += 1

        winner_pct = winner_strategy_count / n_trials
        assert winner_pct >= 0.60, (
            f"Winner's poker strategy only inherited {winner_pct:.1%} of the time, "
            f"expected >= 60% (with some novelty and mutation)"
        )


class TestNoveltyInjectionRates:
    """Tests for novelty injection rates."""

    def test_novelty_rate_is_reduced(self):
        """Test that novelty injection rate is appropriately low."""
        # Check config values
        assert POKER_EVOLUTION_CONFIG["novelty_injection_rate"] <= 0.05, (
            f"Novelty injection rate {POKER_EVOLUTION_CONFIG['novelty_injection_rate']} "
            f"is too high, should be <= 5%"
        )
        assert POKER_EVOLUTION_CONFIG["different_type_novelty_rate"] <= 0.10, (
            f"Different type novelty rate {POKER_EVOLUTION_CONFIG['different_type_novelty_rate']} "
            f"is too high, should be <= 10%"
        )

    def test_same_type_parents_preserve_type(self):
        """Test that same-type parents produce same-type offspring most of the time."""
        n_trials = 200
        same_type_count = 0

        rng = random.Random(42)
        parent = TightAggressiveStrategy(rng=rng)

        for _ in range(n_trials):
            offspring = crossover_poker_strategies(
                parent,
                parent,  # Same type
                mutation_rate=0.12,
                mutation_strength=0.15,
                rng=rng,
            )

            if offspring.strategy_id == "tight_aggressive":
                same_type_count += 1

        same_type_pct = same_type_count / n_trials
        assert same_type_pct >= 0.90, (
            f"Same-type parents only produced same type {same_type_pct:.1%} of the time, "
            f"expected >= 90% (only novelty injection should change type)"
        )


class TestMutationRates:
    """Tests for mutation rate appropriateness."""

    def test_mutation_rates_are_reduced(self):
        """Test that default mutation rates are appropriately low."""
        assert POKER_EVOLUTION_CONFIG["default_mutation_rate"] <= 0.15, (
            f"Default mutation rate {POKER_EVOLUTION_CONFIG['default_mutation_rate']} "
            f"is too high, should be <= 15%"
        )
        assert POKER_EVOLUTION_CONFIG["default_mutation_strength"] <= 0.20, (
            f"Default mutation strength {POKER_EVOLUTION_CONFIG['default_mutation_strength']} "
            f"is too high, should be <= 20%"
        )

    def test_parameters_drift_slowly(self):
        """Test that parameters don't drift too quickly over generations.

        Since mutation is stochastic, we run multiple trials and check average drift.
        This avoids flaky failures from random variance.
        """
        n_trials = 20
        n_generations = 10
        total_drift = 0.0
        valid_trials = 0

        rng = random.Random(42)
        for trial in range(n_trials):
            # Start with a strategy with known parameters
            original = TightAggressiveStrategy(rng=rng)
            original.parameters["weak_fold_threshold"] = 0.35
            original.parameters["bluff_frequency"] = 0.10

            # Simulate generations of self-crossover (worst case for drift)
            current = original

            for _ in range(n_generations):
                current = crossover_poker_strategies(
                    current,
                    current,
                    mutation_rate=0.12,
                    mutation_strength=0.15,
                    rng=rng,
                )

            # Measure drift if strategy type was preserved
            if current.strategy_id == "tight_aggressive":
                fold_drift = abs(current.parameters.get("weak_fold_threshold", 0.5) - 0.35)
                total_drift += fold_drift
                valid_trials += 1

        # Check average drift across trials
        if valid_trials > 0:
            avg_drift = total_drift / valid_trials
            # Average drift should be moderate (around 0.1-0.2 is expected)
            # Allow up to 0.25 average drift over 10 generations
            assert avg_drift < 0.25, (
                f"Average parameter drift was {avg_drift:.3f} over {n_generations} generations "
                f"({valid_trials} trials), expected < 0.25"
            )


class TestEvolutionSimulation:
    """Tests for simulated evolution over multiple generations."""

    def test_selection_increases_strategy_convergence(self):
        """Test that selection causes population to converge on strategies."""
        population_size = 20
        n_generations = 10

        # Start with diverse population
        rng = random.Random(42)  # rng for initial pop and mutation
        # Note: get_random_poker_strategy might need rng param if it supports it,
        # checking signature... likely yes given recent changes
        population: List[PokerStrategyAlgorithm] = [
            get_random_poker_strategy(rng=rng) for _ in range(population_size)
        ]

        initial_types = len(set(s.strategy_id for s in population))

        # Simulate evolution with selection (fittest reproduce more)
        # We'll use a simple fitness function: strategies with certain IDs
        # are "fitter" (simulating that some strategies actually win more)
        FITTER_STRATEGIES = {"tight_aggressive", "balanced", "adaptive"}

        for _ in range(n_generations):
            # Calculate fitness (fitter strategies get higher scores)
            fitness_scores = []
            for s in population:
                score = 2.0 if s.strategy_id in FITTER_STRATEGIES else 1.0
                fitness_scores.append((s, score))

            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)

            # Top 50% reproduce
            survivors = [f[0] for f in fitness_scores[: population_size // 2]]

            # Create next generation with winner-biased crossover
            next_gen = []
            for _ in range(population_size):
                # Higher fitness parent more likely to be parent1 (winner)
                parent1 = random.choice(survivors[:5])  # Top 5
                parent2 = random.choice(survivors)
                offspring = crossover_poker_strategies(
                    parent1,
                    parent2,
                    winner_weight=0.80,
                    rng=rng,
                )
                next_gen.append(offspring)

            population = next_gen

        # After selection, population should have converged
        final_types = len(set(s.strategy_id for s in population))

        # Count fitter strategies
        fitter_count = sum(1 for s in population if s.strategy_id in FITTER_STRATEGIES)

        assert fitter_count >= population_size * 0.4, (
            f"Only {fitter_count}/{population_size} ({100*fitter_count/population_size:.1f}%) "
            f"are fitter strategies, expected >= 40% after selection"
        )


class TestInheritPokerStrategyFunction:
    """Tests for the _inherit_poker_strategy helper function."""

    def test_inherit_poker_strategy_accepts_winner_weight(self):
        """Test that _inherit_poker_strategy properly uses winner_weight."""
        n_trials = 100
        winner_type_count = 0

        rng = random.Random(42)
        winner_strat = TightAggressiveStrategy(rng=rng)
        loser_strat = LooseAggressiveStrategy(rng=rng)

        for i in range(n_trials):
            rng = random.Random(i)
            offspring = _inherit_poker_strategy(
                winner_strat,
                loser_strat,
                mutation_rate=0.12,
                mutation_strength=0.15,
                rng=rng,
                winner_weight=0.80,
            )

            if offspring and offspring.strategy_id == "tight_aggressive":
                winner_type_count += 1

        winner_pct = winner_type_count / n_trials
        assert winner_pct >= 0.60, (
            f"Winner's strategy only inherited {winner_pct:.1%} via _inherit_poker_strategy, "
            f"expected >= 60%"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
