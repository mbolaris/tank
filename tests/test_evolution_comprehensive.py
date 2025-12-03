"""
Comprehensive tests for evolution components to verify they can do evolution.

This test suite covers:
- Edge cases and boundary conditions
- Multi-generation evolution integration
- Poker-specific evolution
- Plant genetics and L-systems
- Statistical properties of evolution
- Serialization and persistence
"""

import pytest
import random
from typing import List, Dict, Any

from core.evolution.mutation import (
    mutate_continuous_trait,
    mutate_discrete_trait,
    calculate_adaptive_mutation_rate,
    should_switch_algorithm,
    MutationConfig,
)
from core.evolution.crossover import (
    CrossoverMode,
    blend_values,
    blend_discrete,
    crossover_dict_values,
    crossover_genomes,
    crossover_genomes_weighted,
)
from core.evolution.inheritance import (
    inherit_trait,
    inherit_discrete_trait,
    inherit_algorithm,
    inherit_learned_behaviors,
)
from core.genetics import Genome
from core.plant_genetics import PlantGenome
from core.algorithms import (
    BehaviorAlgorithm,
    crossover_algorithms,
    crossover_algorithms_weighted,
    GreedyFoodSeeker,
    PokerChallenger,
)
from core.poker.strategy.implementations import (
    crossover_poker_strategies,
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    ManiacStrategy,
)


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions for evolution."""

    def test_mutation_with_zero_rate(self):
        """Mutation with 0.0 rate should never mutate."""
        original = 0.5
        mutated_count = 0
        for _ in range(100):
            result = mutate_continuous_trait(original, 0.0, 1.0, mutation_rate=0.0, mutation_strength=0.1)
            if result != original:
                mutated_count += 1
        assert mutated_count == 0, "Zero mutation rate should never mutate"

    def test_mutation_with_max_rate(self):
        """Mutation with 1.0 rate should always mutate."""
        original = 0.5
        mutated_count = 0
        for _ in range(100):
            result = mutate_continuous_trait(original, 0.0, 1.0, mutation_rate=1.0, mutation_strength=0.1)
            if result != original:
                mutated_count += 1
        # With 1.0 rate, most should mutate (allow some due to Gaussian randomness)
        assert mutated_count > 90, f"Max mutation rate should mutate most times, got {mutated_count}/100"

    def test_mutation_respects_bounds(self):
        """Mutation should never exceed min/max bounds."""
        for _ in range(1000):
            value = random.uniform(0.0, 1.0)
            result = mutate_continuous_trait(
                value,
                0.0,  # min_val
                1.0,  # max_val
                mutation_rate=1.0,
                mutation_strength=1.0,  # Very strong mutation
            )
            assert 0.0 <= result <= 1.0, f"Mutation {result} exceeded bounds [0.0, 1.0]"

    def test_extreme_population_stress(self):
        """Test adaptive mutation with extreme population stress."""
        config = MutationConfig()

        # Zero stress should give base rate
        rate_zero = calculate_adaptive_mutation_rate(0.0, config)
        assert rate_zero == config.base_rate

        # Extreme stress should hit max rate
        rate_extreme = calculate_adaptive_mutation_rate(1.0, config)
        assert rate_extreme <= config.max_rate
        assert rate_extreme >= config.base_rate

        # Negative stress should clamp to base rate
        rate_negative = calculate_adaptive_mutation_rate(-0.5, config)
        assert rate_negative == config.base_rate

    def test_discrete_mutation_with_empty_list(self):
        """Discrete mutation with empty options should return original."""
        result = mutate_discrete_trait(5, options=[], mutation_rate=1.0)
        assert result == 5

    def test_discrete_mutation_with_single_option(self):
        """Discrete mutation with single option should return that option."""
        result = mutate_discrete_trait(5, options=[10], mutation_rate=1.0)
        assert result == 10

    def test_algorithm_switch_probability(self):
        """Test algorithm switching follows configured probability."""
        switch_count = 0
        trials = 10000
        switch_rate = 0.1

        for _ in range(trials):
            if should_switch_algorithm(switch_rate):
                switch_count += 1

        # Should be within reasonable range (use 3 sigma for 99.7% confidence)
        expected = trials * switch_rate
        std_dev = (trials * switch_rate * (1 - switch_rate)) ** 0.5
        assert abs(switch_count - expected) < 3 * std_dev, \
            f"Algorithm switch rate {switch_count/trials:.3f} deviates from expected {switch_rate}"

    def test_crossover_with_none_values(self):
        """Crossover should handle None values gracefully."""
        # blend_values with None should prefer non-None
        result = blend_values(None, 5.0, CrossoverMode.AVERAGING, 0.5)
        assert result == 5.0

        result = blend_values(5.0, None, CrossoverMode.AVERAGING, 0.5)
        assert result == 5.0

        # Both None should return None
        result = blend_values(None, None, CrossoverMode.AVERAGING, 0.5)
        assert result is None

    def test_genome_with_extreme_traits(self):
        """Test genome creation with extreme trait values."""
        genome = Genome(
            speed_modifier=1.5,  # Max
            size_modifier=0.5,   # Min
            vision_range=200.0,  # Max
            metabolism_rate=0.5, # Min
            max_energy=200.0,    # Max
            aggression=1.0,      # Max
            social_tendency=0.0, # Min
        )

        # Should be valid
        assert genome.speed_modifier == 1.5
        assert genome.aggression == 1.0
        assert genome.social_tendency == 0.0

    def test_blend_discrete_distribution(self):
        """Test discrete blending follows probability distribution."""
        trials = 10000
        parent1_count = 0

        for _ in range(trials):
            result = blend_discrete("A", "B", weight1=0.7)
            if result == "A":
                parent1_count += 1

        # Should be roughly 70% parent1 (allow 3 sigma)
        expected = trials * 0.7
        std_dev = (trials * 0.7 * 0.3) ** 0.5
        assert abs(parent1_count - expected) < 3 * std_dev, \
            f"Discrete blend {parent1_count/trials:.3f} deviates from expected 0.7"


class TestMultiGenerationEvolution:
    """Integration tests for multi-generation evolution."""

    def test_fish_evolution_over_generations(self):
        """Test fish genome evolution over multiple generations."""
        # Create initial population
        population = [Genome.random() for _ in range(20)]

        # Track diversity over generations
        generations = 10
        speed_ranges = []

        for gen in range(generations):
            # Calculate diversity
            speeds = [g.speed_modifier for g in population]
            speed_ranges.append(max(speeds) - min(speeds))

            # Breed next generation
            next_gen = []
            for _ in range(20):
                parent1 = random.choice(population)
                parent2 = random.choice(population)
                child = Genome.from_parents(parent1, parent2, population_stress=0.0)
                next_gen.append(child)

            population = next_gen

        # Evolution should maintain some diversity
        assert len(population) == 20
        final_speeds = [g.speed_modifier for g in population]
        assert max(final_speeds) - min(final_speeds) > 0.01, \
            "Evolution should maintain genetic diversity"

    def test_weighted_evolution_favors_winner(self):
        """Test that weighted crossover favors winner's traits."""
        # Create genomes with distinct traits
        winner = Genome(speed_modifier=1.5, aggression=1.0)
        loser = Genome(speed_modifier=0.5, aggression=0.0)

        # Generate many offspring
        offspring = []
        for _ in range(100):
            child = Genome.from_parents_weighted(
                winner, loser,
                winner_weight=0.8,
                population_stress=0.0
            )
            offspring.append(child)

        # Offspring should be biased toward winner
        avg_speed = sum(o.speed_modifier for o in offspring) / len(offspring)
        avg_aggression = sum(o.aggression for o in offspring) / len(offspring)

        # Should be closer to winner (1.5, 1.0) than loser (0.5, 0.0)
        assert avg_speed > 1.0, f"Speed {avg_speed:.3f} should favor winner's 1.5"
        assert avg_aggression > 0.5, f"Aggression {avg_aggression:.3f} should favor winner's 1.0"

    def test_population_stress_increases_variation(self):
        """Test that population stress increases genetic variation."""
        parent1 = Genome(speed_modifier=1.0)
        parent2 = Genome(speed_modifier=1.0)

        # Low stress offspring
        low_stress_offspring = [
            Genome.from_parents(parent1, parent2, population_stress=0.0)
            for _ in range(100)
        ]

        # High stress offspring
        high_stress_offspring = [
            Genome.from_parents(parent1, parent2, population_stress=1.0)
            for _ in range(100)
        ]

        # Calculate variance
        low_variance = sum((o.speed_modifier - 1.0) ** 2 for o in low_stress_offspring) / 100
        high_variance = sum((o.speed_modifier - 1.0) ** 2 for o in high_stress_offspring) / 100

        assert high_variance > low_variance, \
            f"High stress variance {high_variance:.4f} should exceed low stress {low_variance:.4f}"

    def test_plant_evolution_preserves_variant(self):
        """Test that plant evolution preserves variant type."""
        parent = PlantGenome.create_claude_variant()

        # Generate offspring through asexual reproduction
        offspring = []
        for _ in range(50):
            child = PlantGenome.from_parent(parent, population_stress=0.0)
            offspring.append(child)

        # All should maintain Claude variant characteristics
        for child in offspring:
            # Claude variant has specific color range
            assert 250 <= child.color_hue <= 290, \
                f"Claude variant hue {child.color_hue} outside expected range"


class TestPokerEvolution:
    """Test poker-specific evolution pathways."""

    def test_poker_algorithm_crossover(self):
        """Test poker algorithm crossover between parents."""
        parent1_algo = TightAggressiveStrategy()
        parent2_algo = LooseAggressiveStrategy()

        # Create offspring strategies
        offspring_algos = []
        for _ in range(50):
            child_algo = crossover_poker_strategies(parent1_algo, parent2_algo, weight1=0.5)
            offspring_algos.append(child_algo)

        # Should get a mix of strategy types
        strategy_types = set(type(algo).__name__ for algo in offspring_algos)
        assert len(strategy_types) > 1, "Should inherit different strategy types from parents"

    def test_poker_weighted_genome_crossover(self):
        """Test that poker winners pass more traits to offspring."""
        winner = Genome(
            aggression=0.9,
            poker_algorithm=PokerChallenger(),
            poker_strategy_algorithm=TightAggressiveStrategy(),
        )

        loser = Genome(
            aggression=0.1,
            poker_algorithm=PokerChallenger(),
            poker_strategy_algorithm=ManiacStrategy(),
        )

        # Generate offspring with winner advantage
        offspring = []
        for _ in range(100):
            child = Genome.from_parents_weighted(
                winner, loser,
                winner_weight=0.75,
                population_stress=0.0
            )
            offspring.append(child)

        # Offspring should inherit more from winner
        avg_aggression = sum(o.aggression for o in offspring) / len(offspring)
        assert avg_aggression > 0.5, \
            f"Offspring aggression {avg_aggression:.3f} should favor winner's 0.9"

        # Check strategy distribution
        tight_aggressive_count = sum(
            1 for o in offspring
            if isinstance(o.poker_strategy_algorithm, TightAggressiveStrategy)
        )
        assert tight_aggressive_count > 40, \
            f"Should inherit winner's strategy more often, got {tight_aggressive_count}/100"


class TestPlantGenetics:
    """Test plant-specific genetics including L-systems."""

    def test_lsystem_parameter_evolution(self):
        """Test L-system parameters evolve properly."""
        parent = PlantGenome(
            axiom="F",
            angle=25.0,
            length_ratio=0.9,
            branch_probability=0.5,
        )

        offspring = []
        for _ in range(100):
            child = PlantGenome.from_parent(parent, population_stress=0.3)
            offspring.append(child)

        # Parameters should vary
        angles = [o.angle for o in offspring]
        length_ratios = [o.length_ratio for o in offspring]

        assert max(angles) - min(angles) > 1.0, "Angles should vary across offspring"
        assert max(length_ratios) - min(length_ratios) > 0.01, "Length ratios should vary"

        # But stay within bounds
        for child in offspring:
            assert 5.0 <= child.angle <= 90.0
            assert 0.3 <= child.length_ratio <= 0.95

    def test_floral_trait_evolution(self):
        """Test floral trait evolution in plants."""
        parent = PlantGenome(
            floral_type="daisy",
            floral_petals=8,
            floral_layers=2,
            floral_spin=0.0,
        )

        offspring = []
        for _ in range(100):
            child = PlantGenome.from_parent(parent, population_stress=0.5)
            offspring.append(child)

        # Discrete traits should sometimes mutate
        floral_types = set(o.floral_type for o in offspring)
        assert len(floral_types) > 1, "Floral type should mutate"

        # Continuous traits should vary
        spins = [o.floral_spin for o in offspring]
        assert max(spins) - min(spins) > 0.1, "Floral spin should vary"

    def test_cosmic_fern_variant(self):
        """Test cosmic fern variant creation and evolution."""
        fern = PlantGenome.create_cosmic_fern_variant()

        # Should have specific characteristics
        assert fern.lsystem == "cosmic_fern"
        assert 140 <= fern.color_hue <= 200  # Cyan range

        # Evolve it
        offspring = [PlantGenome.from_parent(fern, population_stress=0.2) for _ in range(50)]

        # Should maintain hue range
        for child in offspring:
            assert 140 <= child.color_hue <= 200, \
                f"Cosmic fern offspring hue {child.color_hue} outside expected range"

    def test_plant_energy_parameters(self):
        """Test plant energy parameter evolution."""
        parent = PlantGenome(
            base_energy_rate=1.0,
            growth_efficiency=0.8,
            nectar_threshold_ratio=0.7,
        )

        offspring = [PlantGenome.from_parent(parent, population_stress=0.4) for _ in range(100)]

        # Energy parameters should evolve
        energy_rates = [o.base_energy_rate for o in offspring]
        efficiencies = [o.growth_efficiency for o in offspring]

        assert max(energy_rates) - min(energy_rates) > 0.1
        assert max(efficiencies) - min(efficiencies) > 0.05

        # Should stay in valid ranges
        for child in offspring:
            assert child.base_energy_rate > 0
            assert 0.0 <= child.growth_efficiency <= 1.0
            assert 0.0 <= child.nectar_threshold_ratio <= 1.0


class TestStatisticalProperties:
    """Test statistical properties of evolution."""

    def test_mutation_is_gaussian(self):
        """Test that continuous mutation follows Gaussian distribution."""
        original = 0.5
        mutations = []

        for _ in range(10000):
            mutated = mutate_continuous_trait(
                original,
                0.0,  # min_val
                1.0,  # max_val
                mutation_rate=1.0,  # Always mutate
                mutation_strength=0.1,
            )
            mutations.append(mutated - original)

        # Calculate statistics
        mean_change = sum(mutations) / len(mutations)
        variance = sum((m - mean_change) ** 2 for m in mutations) / len(mutations)

        # Mean should be near zero (symmetric)
        assert abs(mean_change) < 0.01, f"Mutation mean {mean_change:.4f} should be near 0"

        # Should have some variance
        assert variance > 0.0001, "Mutations should have variance"

    def test_genetic_diversity_maintained(self):
        """Test that evolution maintains genetic diversity."""
        # Start with diverse population
        population = [Genome.random() for _ in range(50)]

        # Evolve for several generations
        for _ in range(20):
            next_gen = []
            for _ in range(50):
                p1, p2 = random.sample(population, 2)
                child = Genome.from_parents(p1, p2, population_stress=0.2)
                next_gen.append(child)
            population = next_gen

        # Calculate diversity metrics
        speeds = [g.speed_modifier for g in population]
        aggression = [g.aggression for g in population]

        speed_variance = sum((s - sum(speeds)/50) ** 2 for s in speeds) / 50
        aggression_variance = sum((a - sum(aggression)/50) ** 2 for a in aggression) / 50

        # Should maintain diversity (not converge to single value)
        assert speed_variance > 0.001, f"Speed variance {speed_variance:.4f} too low"
        assert aggression_variance > 0.001, f"Aggression variance {aggression_variance:.4f} too low"

    def test_trait_correlation_in_offspring(self):
        """Test that offspring traits correlate with parents."""
        parent1 = Genome(speed_modifier=1.5, size_modifier=1.5)
        parent2 = Genome(speed_modifier=0.5, size_modifier=0.5)

        offspring = [
            Genome.from_parents(parent1, parent2, population_stress=0.0)
            for _ in range(200)
        ]

        # Offspring speeds and sizes should correlate with parents
        avg_speed = sum(o.speed_modifier for o in offspring) / len(offspring)
        avg_size = sum(o.size_modifier for o in offspring) / len(offspring)

        # Should be between parents (roughly average)
        assert 0.8 < avg_speed < 1.2, f"Average speed {avg_speed:.3f} should be near 1.0"
        assert 0.8 < avg_size < 1.2, f"Average size {avg_size:.3f} should be near 1.0"


class TestSerializationAndPersistence:
    """Test genome serialization and persistence."""

    def test_genome_to_dict_roundtrip(self):
        """Test Genome can serialize and deserialize."""
        original = Genome.random()

        # Serialize to dict
        genome_dict = original.to_dict()

        # Should be a dict
        assert isinstance(genome_dict, dict)
        assert "speed_modifier" in genome_dict
        assert "aggression" in genome_dict

        # Deserialize
        restored = Genome.from_dict(genome_dict)

        # Should match original
        assert restored.speed_modifier == original.speed_modifier
        assert restored.aggression == original.aggression
        assert restored.color_hue == original.color_hue

    def test_plant_genome_to_dict_roundtrip(self):
        """Test PlantGenome can serialize and deserialize."""
        original = PlantGenome(
            axiom="F",
            angle=25.0,
            lsystem="claude",
            floral_type="daisy",
        )

        # Serialize
        genome_dict = original.to_dict()

        assert isinstance(genome_dict, dict)
        assert genome_dict["axiom"] == "F"
        assert genome_dict["angle"] == 25.0

        # Deserialize
        restored = PlantGenome.from_dict(genome_dict)

        assert restored.axiom == original.axiom
        assert restored.angle == original.angle
        assert restored.lsystem == original.lsystem

    def test_genome_with_algorithms_serializes(self):
        """Test genome with algorithms can serialize."""
        genome = Genome(
            behavior_algorithm=GreedyFoodSeeker(),
            poker_algorithm=PokerChallenger(),
        )

        genome_dict = genome.to_dict()

        # Algorithms should serialize
        assert "behavior_algorithm" in genome_dict
        assert "poker_algorithm" in genome_dict

        # Restore
        restored = Genome.from_dict(genome_dict)

        assert restored.behavior_algorithm.name == "GreedyFoodSeeker"
        assert restored.poker_algorithm.name == "PokerChallenger"

    def test_evolved_genome_serialization(self):
        """Test that evolved genomes serialize correctly."""
        parent1 = Genome.random()
        parent2 = Genome.random()

        child = Genome.from_parents(parent1, parent2, population_stress=0.3)

        # Serialize and restore
        child_dict = child.to_dict()
        restored = Genome.from_dict(child_dict)

        # All traits should match
        assert restored.speed_modifier == child.speed_modifier
        assert restored.size_modifier == child.size_modifier
        assert restored.vision_range == child.vision_range
        assert restored.metabolism_rate == child.metabolism_rate


class TestComplexIntegration:
    """Test complex integration scenarios."""

    def test_mate_compatibility_calculation(self):
        """Test mate compatibility scoring."""
        fish1 = Genome(
            speed_modifier=1.0,
            size_modifier=1.0,
            color_hue=180.0,
        )

        # Similar fish - high compatibility
        fish2 = Genome(
            speed_modifier=1.1,
            size_modifier=1.0,
            color_hue=185.0,
        )

        # Very different fish - low compatibility
        fish3 = Genome(
            speed_modifier=0.5,
            size_modifier=1.5,
            color_hue=0.0,
        )

        compatibility_similar = fish1.calculate_mate_compatibility(fish2)
        compatibility_different = fish1.calculate_mate_compatibility(fish3)

        # Similar fish should have higher compatibility
        assert compatibility_similar > compatibility_different, \
            f"Similar fish compatibility {compatibility_similar:.3f} should exceed different fish {compatibility_different:.3f}"

    def test_fitness_tracking_updates(self):
        """Test fitness score updates across lifetime."""
        genome = Genome.random()

        # Simulate lifetime events
        genome.update_fitness(survived_seconds=100, food_eaten=10, fights_won=3)

        initial_fitness = genome.fitness_score
        assert initial_fitness > 0, "Fitness should increase from achievements"

        # More achievements
        genome.update_fitness(survived_seconds=200, food_eaten=20, fights_won=5)

        assert genome.fitness_score > initial_fitness, \
            "Fitness should increase with more achievements"

    def test_learned_behaviors_inheritance(self):
        """Test learned behaviors are inherited culturally."""
        parent1 = Genome(
            learned_behaviors={"food_strategy": "ambush", "territory_size": 50}
        )

        parent2 = Genome(
            learned_behaviors={"food_strategy": "chase", "social_rank": 3}
        )

        # Inherit behaviors
        child_behaviors = inherit_learned_behaviors(
            parent1.learned_behaviors,
            parent2.learned_behaviors,
            inheritance_rate=0.7
        )

        # Should have some behaviors from parents
        assert len(child_behaviors) > 0, "Should inherit some behaviors"

        # Check inheritance probability
        trials = 1000
        inherited_counts = {key: 0 for key in set(list(parent1.learned_behaviors.keys()) + list(parent2.learned_behaviors.keys()))}

        for _ in range(trials):
            behaviors = inherit_learned_behaviors(
                parent1.learned_behaviors,
                parent2.learned_behaviors,
                inheritance_rate=0.7
            )
            for key in behaviors:
                inherited_counts[key] += 1

        # Each behavior should be inherited roughly 70% of the time
        for key, count in inherited_counts.items():
            rate = count / trials
            assert 0.5 < rate < 0.9, \
                f"Behavior '{key}' inherited {rate:.2f} of time, expected ~0.7"

    def test_algorithm_evolution_preserves_functionality(self):
        """Test that evolved algorithms remain functional."""
        parent1_algo = GreedyFoodSeeker()
        parent2_algo = GreedyFoodSeeker()

        # Mutate parameters slightly
        parent2_algo.parameters["search_radius"] = 150.0

        # Crossover
        child_algo = crossover_algorithms(parent1_algo, parent2_algo, 0.5, 0.1)

        # Should still be GreedyFoodSeeker
        assert isinstance(child_algo, GreedyFoodSeeker)

        # Should have blended parameters
        assert child_algo.parameters["search_radius"] != parent1_algo.parameters["search_radius"] or \
               child_algo.parameters["search_radius"] != parent2_algo.parameters["search_radius"]

        # Should be valid
        assert 50.0 <= child_algo.parameters["search_radius"] <= 300.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
