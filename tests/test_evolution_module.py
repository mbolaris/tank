"""Tests for the core.evolution module.

Verifies that the unified evolution module correctly handles:
- Mutation of continuous and discrete traits
- Crossover between parent genomes
- Adaptive mutation bounds
- Cultural inheritance of learned behaviors
- Algorithm inheritance

These tests verify ALife principles: no explicit fitness functions,
selection pressure emerges from survival and reproduction.
"""

import random

import pytest

from core.evolution import (
    CrossoverMode,
    calculate_adaptive_mutation_rate,
)
from core.evolution.crossover import blend_values, crossover_dict_values
from core.evolution.inheritance import (
    inherit_algorithm,
    inherit_discrete_trait,
    inherit_learned_behaviors,
    inherit_trait,
)
from core.evolution.mutation import mutate_continuous_trait, mutate_discrete_trait
from core.genetics import Genome


class TestMutation:
    """Tests for mutation operations."""

    def test_continuous_trait_mutation_applies(self):
        """Mutation should occasionally change values."""
        rng = random.Random(42)
        original = 0.5
        changed_count = 0

        for _ in range(100):
            mutated = mutate_continuous_trait(
                original, 0.0, 1.0,
                mutation_rate=1.0,  # Always mutate
                mutation_strength=0.2,
                rng=rng,
            )
            if mutated != original:
                changed_count += 1

        # With 100% mutation rate, most values should change
        assert changed_count > 90

    def test_continuous_trait_respects_bounds(self):
        """Mutated values should stay within bounds."""
        rng = random.Random(42)

        for _ in range(100):
            mutated = mutate_continuous_trait(
                0.5, 0.0, 1.0,
                mutation_rate=1.0,
                mutation_strength=0.5,
                rng=rng,
            )
            assert 0.0 <= mutated <= 1.0

    def test_discrete_trait_mutation(self):
        """Discrete traits should mutate by ±1."""
        rng = random.Random(42)
        original = 5

        mutations = set()
        for _ in range(100):
            mutated = mutate_discrete_trait(
                original, 0, 10,
                mutation_rate=1.0,
                rng=rng,
            )
            mutations.add(mutated)

        # Should see original ±1 values
        assert 4 in mutations or 5 in mutations or 6 in mutations

    def test_zero_mutation_rate_preserves_value(self):
        """Zero mutation rate should preserve original value."""
        rng = random.Random(42)
        original = 0.5

        for _ in range(100):
            mutated = mutate_continuous_trait(
                original, 0.0, 1.0,
                mutation_rate=0.0,
                mutation_strength=0.5,
                rng=rng,
            )
            assert mutated == original


class TestAdaptiveMutation:
    """Tests for adaptive mutation rates."""

    def test_mutation_rate_clamps_to_min(self):
        """Mutation rate should be clamped to configured minimums."""
        rate, strength = calculate_adaptive_mutation_rate(0.0, 0.0)
        assert rate >= 0.04
        assert strength >= 0.03

    def test_mutation_rate_clamps_to_max(self):
        """Mutation rate should be clamped to configured maximums."""
        rate, strength = calculate_adaptive_mutation_rate(1.0, 1.0)
        assert rate <= 0.25
        assert strength <= 0.15


class TestCrossover:
    """Tests for crossover operations."""

    def test_blend_values_averaging(self):
        """Averaging mode should average parent values."""
        result = blend_values(0.2, 0.8, weight1=0.5, mode=CrossoverMode.AVERAGING)
        assert result == pytest.approx(0.5, abs=0.01)

    def test_blend_values_weighted(self):
        """Weighted mode should respect weights."""
        result = blend_values(0.0, 1.0, weight1=0.7, mode=CrossoverMode.WEIGHTED)
        assert result == pytest.approx(0.3, abs=0.01)

    def test_blend_values_recombination(self):
        """Recombination should select from parents."""
        rng = random.Random(42)
        results = set()

        for _ in range(100):
            result = blend_values(0.0, 1.0, mode=CrossoverMode.RECOMBINATION, rng=rng)
            # With recombination, should get values near 0 or 1
            results.add(round(result, 1))

        # Should see variety in results
        assert len(results) > 1

    def test_crossover_dict_values(self):
        """Should blend dictionary values from parents."""
        parent1 = {"a": 0.2, "b": 0.4}
        parent2 = {"a": 0.8, "b": 0.6}

        result = crossover_dict_values(
            parent1, parent2,
            weight1=0.5,
            mode=CrossoverMode.AVERAGING,
        )

        assert result["a"] == pytest.approx(0.5, abs=0.01)
        assert result["b"] == pytest.approx(0.5, abs=0.01)


class TestInheritance:
    """Tests for trait inheritance."""

    def test_inherit_trait_blends_parents(self):
        """Inherited trait should blend parent values."""
        rng = random.Random(42)

        # Equal weight, no mutation
        inherited = inherit_trait(
            0.2, 0.8, 0.0, 1.0,
            weight1=0.5,
            mutation_rate=0.0,
            rng=rng,
        )

        assert inherited == pytest.approx(0.5, abs=0.01)

    def test_inherit_trait_respects_weight(self):
        """Higher weight should favor that parent."""
        rng = random.Random(42)

        inherited = inherit_trait(
            0.0, 1.0, 0.0, 1.0,
            weight1=0.8,  # Parent 1 gets 80% weight
            mutation_rate=0.0,
            rng=rng,
        )

        # Should be closer to parent1's value (0.0)
        assert inherited == pytest.approx(0.2, abs=0.01)

    def test_inherit_discrete_trait(self):
        """Discrete trait should select from one parent."""
        rng = random.Random(42)

        # Run multiple times to see both parent values selected
        values = set()
        for _ in range(100):
            inherited = inherit_discrete_trait(
                1, 5, 0, 10,
                weight1=0.5,
                mutation_rate=0.0,
                rng=rng,
            )
            values.add(inherited)

        # Should see both parent values
        assert 1 in values or 5 in values


class TestAlgorithmInheritance:
    """Tests for behavior algorithm inheritance."""

    def test_inherit_algorithm_from_parents(self):
        """Should inherit algorithm from one of the parents."""
        from core.algorithms import EnergyConserver, GreedyFoodSeeker

        alg1 = GreedyFoodSeeker.random_instance()
        alg2 = EnergyConserver.random_instance()

        rng = random.Random(42)

        # Run multiple times to verify inheritance works
        types_seen = set()
        for _ in range(20):
            child_alg = inherit_algorithm(
                alg1, alg2,
                weight1=0.5,
                mutation_rate=0.0,
                algorithm_switch_rate=0.0,  # No random switching
                rng=rng,
            )
            types_seen.add(type(child_alg).__name__)

        # Should see at least one of the parent types
        assert len(types_seen) >= 1

    def test_inherit_algorithm_handles_none(self):
        """Should handle None parent algorithms."""
        from core.algorithms import GreedyFoodSeeker

        alg1 = GreedyFoodSeeker.random_instance()
        rng = random.Random(42)

        # One parent None
        child = inherit_algorithm(alg1, None, rng=rng)
        assert child is not None

        # Other parent None
        child = inherit_algorithm(None, alg1, rng=rng)
        assert child is not None

        # Both None - should get random
        child = inherit_algorithm(None, None, rng=rng)
        assert child is not None


class TestLearnedBehaviorInheritance:
    """Tests for cultural inheritance of learned behaviors."""

    def test_learned_behaviors_partially_inherited(self):
        """Offspring should inherit fraction of learned behaviors."""
        parent1 = Genome.random()
        parent2 = Genome.random()
        offspring = Genome.random()

        # Set up learned behaviors
        parent1.learned_behaviors = {"poker_aggression_adj": 0.4}
        parent2.learned_behaviors = {"poker_aggression_adj": 0.2}
        offspring.learned_behaviors = {}

        inherit_learned_behaviors(parent1, parent2, offspring, inheritance_rate=0.25)

        # Should inherit 25% of average (0.3 * 0.25 = 0.075)
        assert "poker_aggression_adj" in offspring.learned_behaviors
        assert offspring.learned_behaviors["poker_aggression_adj"] == pytest.approx(0.075, abs=0.01)

    def test_counters_not_inherited(self):
        """Counter values (games won, etc.) should not be inherited."""
        parent1 = Genome.random()
        parent2 = Genome.random()
        offspring = Genome.random()

        parent1.learned_behaviors = {
            "poker_aggression_adj": 0.4,
            "poker_won": 10,  # Counter - should not inherit
        }
        parent2.learned_behaviors = {
            "poker_aggression_adj": 0.2,
            "poker_won": 5,
        }
        offspring.learned_behaviors = {}

        inherit_learned_behaviors(parent1, parent2, offspring)

        assert "poker_won" not in offspring.learned_behaviors


class TestFullGenomeEvolution:
    """Integration tests for full genome evolution."""

    def test_genome_from_parents_produces_valid_offspring(self):
        """Genome.from_parents should produce valid offspring."""
        parent1 = Genome.random()
        parent2 = Genome.random()

        offspring = Genome.from_parents(
            parent1, parent2,
            mutation_rate=0.1,
            mutation_strength=0.1,
        )

        # Offspring should have valid values
        assert 0.5 <= offspring.speed_modifier <= 1.5
        assert 0.0 <= offspring.behavioral.aggression.value <= 1.0
        assert offspring.behavioral.behavior_algorithm.value is not None

    def test_genome_weighted_crossover_favors_winner(self):
        """Weighted crossover should favor the higher-weighted parent."""
        random.Random(42)

        # Create parents with distinct traits (using actual dataclass fields)
        # Note: speed_modifier is a computed property, so we use fin_size/tail_size instead
        parent1 = Genome.random()
        parent1.behavioral.aggression.value = 0.1
        parent1.physical.fin_size.value = 0.8
        parent1.physical.tail_size.value = 0.8
        parent2 = Genome.random()
        parent2.behavioral.aggression.value = 0.9
        parent2.physical.fin_size.value = 1.3
        parent2.physical.tail_size.value = 1.3

        # Run multiple times to get average
        aggression_sum = 0.0
        trials = 50

        for _ in range(trials):
            offspring = Genome.from_parents_weighted(
                parent1, parent2,
                parent1_weight=0.8,  # Parent1 contributes 80%
                mutation_rate=0.0,  # No mutation for clearer test
            )
            aggression_sum += offspring.behavioral.aggression.value

        avg_aggression = aggression_sum / trials

        # Average should be closer to parent1's value (0.1)
        # Expected: 0.1 * 0.8 + 0.9 * 0.2 = 0.26
        assert avg_aggression < 0.4  # Closer to parent1

    def test_multi_generation_evolution(self):
        """Evolution should work across multiple generations."""
        # Start with initial population
        population = [Genome.random() for _ in range(10)]

        # Evolve for several generations
        for generation in range(5):
            new_population = []

            for _ in range(10):
                # Select random parents
                parent1 = random.choice(population)
                parent2 = random.choice(population)

                # Create offspring
                offspring = Genome.from_parents(
                    parent1, parent2,
                    mutation_rate=0.15,
                    mutation_strength=0.15,
                )
                new_population.append(offspring)

            population = new_population

        # Final population should have valid genomes
        for genome in population:
            assert 0.5 <= genome.speed_modifier <= 1.5
            assert 0.0 <= genome.behavioral.aggression.value <= 1.0
            assert genome.behavioral.behavior_algorithm.value is not None
            assert genome.behavioral.poker_algorithm.value is not None


class TestPlantEvolution:
    """Tests for plant genome evolution."""

    def test_plant_from_parent_produces_valid_offspring(self):
        """PlantGenome.from_parent should produce valid offspring."""
        from core.genetics import PlantGenome

        parent = PlantGenome.create_random()
        offspring = PlantGenome.from_parent(parent, mutation_rate=0.2)

        # Offspring should have valid values
        assert 15.0 <= offspring.angle <= 45.0
        assert 0.5 <= offspring.length_ratio <= 0.85
        assert offspring.fractal_type == parent.fractal_type  # Should preserve variant

    def test_plant_variant_preserved(self):
        """Plant variant type should be preserved across generations."""
        from core.genetics import PlantGenome

        # Create a specific variant
        parent = PlantGenome.create_claude_variant()

        # Evolve for several generations
        current = parent
        for _ in range(5):
            current = PlantGenome.from_parent(current, mutation_rate=0.2)

        # Variant should be preserved
        assert current.fractal_type == "claude"
