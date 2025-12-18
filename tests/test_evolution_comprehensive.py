"""
Comprehensive tests for evolution components to verify they can do evolution.

This test suite covers:
- Edge cases and boundary conditions
- Multi-generation evolution integration
- Poker-specific evolution
- Plant genetics and L-systems
- Statistical properties of evolution
"""

import random

import pytest

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
from core.genetics import Genome, GeneticTrait, PhysicalTraits, BehavioralTraits
from core.genetics import PlantGenome
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

        # Zero stress should give base rates
        rate_zero, strength_zero = calculate_adaptive_mutation_rate(
            config.base_rate, config.base_strength, population_stress=0.0, config=config
        )
        assert rate_zero == config.base_rate

        # Extreme stress should increase rates
        rate_extreme, strength_extreme = calculate_adaptive_mutation_rate(
            config.base_rate, config.base_strength, population_stress=1.0, config=config
        )
        assert rate_extreme >= config.base_rate
        assert strength_extreme >= config.base_strength

    def test_discrete_mutation_with_single_value_range(self):
        """Discrete mutation with single value range should stay the same."""
        result = mutate_discrete_trait(5, min_val=5, max_val=5, mutation_rate=1.0)
        assert result == 5

    def test_discrete_mutation_respects_bounds(self):
        """Discrete mutation should stay within min/max bounds."""
        for _ in range(100):
            result = mutate_discrete_trait(5, min_val=0, max_val=10, mutation_rate=1.0)
            assert 0 <= result <= 10

    def test_algorithm_switch_probability(self):
        """Test algorithm switching follows configured probability."""
        switch_count = 0
        trials = 10000
        base_mutation_rate = 0.08  # Base mutation rate

        # Effective rate = config.algorithm_switch_rate * (1 + mutation_rate)
        # With config.algorithm_switch_rate = 0.04 and mutation_rate = 0.08:
        effective_switch_rate = 0.04 * (1 + base_mutation_rate)  # ~0.0432

        for _ in range(trials):
            if should_switch_algorithm(base_mutation_rate):
                switch_count += 1

        # Should be within reasonable range (use 3 sigma for 99.7% confidence)
        expected = trials * effective_switch_rate
        std_dev = (trials * effective_switch_rate * (1 - effective_switch_rate)) ** 0.5
        assert abs(switch_count - expected) < 3 * std_dev, \
            f"Algorithm switch rate {switch_count/trials:.3f} deviates from expected {effective_switch_rate:.3f}"

    def test_crossover_modes(self):
        """Test different crossover modes."""
        # Test AVERAGING mode
        result = blend_values(5.0, 10.0, weight1=0.5, mode=CrossoverMode.AVERAGING)
        assert 5.0 <= result <= 10.0

        # Test RECOMBINATION mode
        result = blend_values(5.0, 10.0, weight1=0.5, mode=CrossoverMode.RECOMBINATION)
        assert 5.0 <= result <= 10.0

    def test_genome_with_extreme_traits(self):
        """Test genome creation with extreme trait values."""
        # Note: speed_modifier, vision_range, metabolism_rate are now computed properties
        # derived from template_id, fin_size, tail_size, body_aspect, and eye_size
        genome = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(0.5),  # Min (valid range is 0.5-2.0)
                color_hue=GeneticTrait(0.5),
                template_id=GeneticTrait(1),      # Streamlined (1.2x speed)
                fin_size=GeneticTrait(1.4),       # Max fins
                tail_size=GeneticTrait(1.4),      # Max tail
                body_aspect=GeneticTrait(0.8),    # Optimal for speed
                eye_size=GeneticTrait(1.3),       # Max eyes (affects vision_range)
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(1.0),       # Max
                social_tendency=GeneticTrait(0.0),  # Min
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(None),
                poker_strategy_algorithm=GeneticTrait(None),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        # Should be valid
        assert genome.physical.size_modifier.value == 0.5
        assert genome.behavioral.aggression.value == 1.0
        assert genome.behavioral.social_tendency.value == 0.0
        # speed_modifier is computed from visual traits
        assert genome.speed_modifier > 1.0  # Should be high with these settings
        # vision_range equals eye_size
        assert genome.vision_range == 1.3

    def test_blend_discrete_distribution(self):
        """Test discrete blending follows probability distribution."""
        # Use seeded RNG for deterministic test results
        rng = random.Random(42)
        trials = 10000
        parent1_count = 0

        for _ in range(trials):
            result = blend_discrete("A", "B", weight1=0.7, rng=rng)
            if result == "A":
                parent1_count += 1

        # Should be roughly 70% parent1
        # With seed 42 and 10000 trials, we get deterministic results
        # Use 4 sigma for robustness if seed changes (99.994% confidence)
        expected = trials * 0.7
        std_dev = (trials * 0.7 * 0.3) ** 0.5
        assert abs(parent1_count - expected) < 4 * std_dev, \
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
        # Create genomes with distinct traits (using actual dataclass fields, not computed properties)
        winner = Genome.random(use_algorithm=False)
        winner.behavioral.aggression.value = 1.0
        winner.physical.fin_size.value = 1.4
        winner.physical.tail_size.value = 1.4  # High aggression, large fins

        loser = Genome.random(use_algorithm=False)
        loser.behavioral.aggression.value = 0.0
        loser.physical.fin_size.value = 0.6
        loser.physical.tail_size.value = 0.6  # Low aggression, small fins

        # Generate many offspring with parent1_weight (not winner_weight)
        offspring = []
        for _ in range(100):
            child = Genome.from_parents_weighted(
                winner, loser,
                parent1_weight=0.8,  # Corrected parameter name
                population_stress=0.0
            )
            offspring.append(child)

        # Offspring should be biased toward winner (parent1)
        avg_fin_size = sum(o.physical.fin_size.value for o in offspring) / len(offspring)
        avg_aggression = sum(o.behavioral.aggression.value for o in offspring) / len(offspring)

        # Should be closer to winner (1.4, 1.0) than loser (0.6, 0.0)
        assert avg_fin_size > 1.0, f"Fin size {avg_fin_size:.3f} should favor winner's 1.4"
        assert avg_aggression > 0.5, f"Aggression {avg_aggression:.3f} should favor winner's 1.0"

    def test_population_stress_increases_variation(self):
        """Test that population stress increases genetic variation."""
        parent1 = Genome.random(use_algorithm=False)
        parent1.physical.fin_size.value = 1.0
        parent1.physical.tail_size.value = 1.0

        parent2 = Genome.random(use_algorithm=False)
        parent2.physical.fin_size.value = 1.0
        parent2.physical.tail_size.value = 1.0

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

        # Calculate variance using fin_size (directly inherited trait)
        low_variance = sum((o.physical.fin_size.value - 1.0) ** 2 for o in low_stress_offspring) / 100
        high_variance = sum((o.physical.fin_size.value - 1.0) ** 2 for o in high_stress_offspring) / 100

        assert high_variance > low_variance, \
            f"High stress variance {high_variance:.4f} should exceed low stress {low_variance:.4f}"

    def test_plant_evolution_preserves_variant(self):
        """Test that plant evolution preserves variant type."""
        parent = PlantGenome.create_claude_variant()

        # Generate offspring through asexual reproduction (no population_stress param)
        offspring = []
        for _ in range(50):
            child = PlantGenome.from_parent(parent)
            offspring.append(child)

        # All should maintain Claude variant type (most important characteristic)
        for child in offspring:
            assert child.fractal_type == "claude", \
                f"Offspring fractal_type {child.fractal_type} should maintain parent's 'claude' type"

        # Color should still have some variety across offspring
        colors = [child.color_hue for child in offspring]
        assert max(colors) - min(colors) > 0.01, "Colors should vary across offspring"


class TestPokerEvolution:
    """Test poker-specific evolution pathways."""

    def test_poker_algorithm_crossover(self):
        """Test poker algorithm crossover between parents."""
        parent1_algo = TightAggressiveStrategy()
        parent2_algo = LooseAggressiveStrategy()

        # Create offspring strategies (no weight1 param)
        offspring_algos = []
        for _ in range(50):
            child_algo = crossover_poker_strategies(parent1_algo, parent2_algo)
            offspring_algos.append(child_algo)

        # Should get a mix of strategy types
        strategy_types = set(type(algo).__name__ for algo in offspring_algos)
        assert len(strategy_types) > 1, "Should inherit different strategy types from parents"

    def test_poker_weighted_genome_crossover(self):
        """Test that poker winners pass more traits to offspring."""
        winner = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(1.0),
                color_hue=GeneticTrait(0.5),
                template_id=GeneticTrait(0),
                fin_size=GeneticTrait(1.0),
                tail_size=GeneticTrait(1.0),
                body_aspect=GeneticTrait(1.0),
                eye_size=GeneticTrait(1.0),
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(0.9),
                social_tendency=GeneticTrait(0.5),
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(PokerChallenger()),
                poker_strategy_algorithm=GeneticTrait(TightAggressiveStrategy()),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        loser = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(1.0),
                color_hue=GeneticTrait(0.5),
                template_id=GeneticTrait(0),
                fin_size=GeneticTrait(1.0),
                tail_size=GeneticTrait(1.0),
                body_aspect=GeneticTrait(1.0),
                eye_size=GeneticTrait(1.0),
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(0.1),
                social_tendency=GeneticTrait(0.5),
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(PokerChallenger()),
                poker_strategy_algorithm=GeneticTrait(ManiacStrategy()),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        # Generate offspring with winner advantage (parent1_weight)
        offspring = []
        for _ in range(100):
            child = Genome.from_parents_weighted(
                winner, loser,
                parent1_weight=0.75,  # Corrected parameter name
                population_stress=0.0
            )
            offspring.append(child)

        # Offspring should inherit more from winner
        avg_aggression = sum(o.behavioral.aggression.value for o in offspring) / len(offspring)
        assert avg_aggression > 0.5, \
            f"Offspring aggression {avg_aggression:.3f} should favor winner's 0.9"

        # Check strategy distribution
        # Note: With 10% novelty injection in poker crossover, we expect fewer direct inheritances
        # With parent1_weight=0.75 and 10% random replacement among 10 strategies,
        # we expect roughly 90% * 75% = 68% max, but with added strategy switching we lower the bar
        tight_aggressive_count = sum(
            1 for o in offspring
            if isinstance(o.behavioral.poker_strategy_algorithm.value, TightAggressiveStrategy)
        )
        assert tight_aggressive_count > 25, \
            f"Should inherit winner's strategy somewhat often (with novelty injection), got {tight_aggressive_count}/100"


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
            child = PlantGenome.from_parent(parent, mutation_rate=0.3)
            offspring.append(child)

        # Parameters should vary (allow smaller variation with moderate mutation)
        angles = [o.angle for o in offspring]
        length_ratios = [o.length_ratio for o in offspring]

        assert max(angles) - min(angles) > 0.2, "Angles should vary across offspring"
        assert max(length_ratios) - min(length_ratios) > 0.005, "Length ratios should vary"

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
            child = PlantGenome.from_parent(parent, mutation_rate=0.5)
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

        # Should have specific characteristics (fractal_type is the key identifier)
        assert fern.fractal_type == "cosmic_fern"
        assert 0.65 <= fern.color_hue <= 0.90  # Initial color range

        # Evolve it
        offspring = [PlantGenome.from_parent(fern, mutation_rate=0.2) for _ in range(50)]

        # All should maintain cosmic_fern variant type (most important)
        for child in offspring:
            assert child.fractal_type == "cosmic_fern", \
                f"Offspring fractal_type {child.fractal_type} should maintain parent's 'cosmic_fern' type"

        # Color should vary across offspring (shows mutation is working)
        colors = [child.color_hue for child in offspring]
        assert max(colors) - min(colors) > 0.01, "Colors should vary across offspring"

    def test_plant_energy_parameters(self):
        """Test plant energy parameter evolution."""
        parent = PlantGenome(
            base_energy_rate=0.03,  # Use value within valid range (0.01-0.05)
            growth_efficiency=0.8,
            nectar_threshold_ratio=0.7,
        )

        offspring = [PlantGenome.from_parent(parent, mutation_rate=0.5) for _ in range(100)]

        # Energy parameters should evolve
        energy_rates = [o.base_energy_rate for o in offspring]
        efficiencies = [o.growth_efficiency for o in offspring]

        # Lower thresholds due to clamping (base_energy_rate has tight bounds 0.01-0.05)
        assert max(energy_rates) - min(energy_rates) > 0.003, "Energy rates should vary"
        assert max(efficiencies) - min(efficiencies) > 0.02, "Efficiencies should vary"

        # Should stay in valid ranges
        for child in offspring:
            assert 0.01 <= child.base_energy_rate <= 0.05
            assert 0.5 <= child.growth_efficiency <= 1.5
            assert 0.6 <= child.nectar_threshold_ratio <= 0.9


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
        aggression = [g.behavioral.aggression.value for g in population]

        speed_variance = sum((s - sum(speeds)/50) ** 2 for s in speeds) / 50
        aggression_variance = sum((a - sum(aggression)/50) ** 2 for a in aggression) / 50

        # Should maintain diversity (not converge to single value)
        # Threshold of 0.0008 is conservative - typical variance is 0.003-0.01
        assert speed_variance > 0.0008, f"Speed variance {speed_variance:.4f} too low"
        assert aggression_variance > 0.0008, f"Aggression variance {aggression_variance:.4f} too low"

    def test_trait_correlation_in_offspring(self):
        """Test that offspring traits correlate with parents."""
        # Use actual dataclass fields (fin_size, tail_size) instead of computed speed_modifier
        parent1 = Genome.random(use_algorithm=False)
        parent1.physical.fin_size.value = 1.4
        parent1.physical.tail_size.value = 1.4
        parent1.physical.size_modifier.value = 1.5

        parent2 = Genome.random(use_algorithm=False)
        parent2.physical.fin_size.value = 0.6
        parent2.physical.tail_size.value = 0.6
        parent2.physical.size_modifier.value = 0.5

        offspring = [
            Genome.from_parents(parent1, parent2, population_stress=0.0)
            for _ in range(200)
        ]

        # Offspring fin_size and sizes should correlate with parents
        avg_fin_size = sum(o.physical.fin_size.value for o in offspring) / len(offspring)
        avg_size = sum(o.physical.size_modifier.value for o in offspring) / len(offspring)

        # Should be between parents (roughly average)
        assert 0.8 < avg_fin_size < 1.2, f"Average fin_size {avg_fin_size:.3f} should be near 1.0"
        assert 0.8 < avg_size < 1.2, f"Average size {avg_size:.3f} should be near 1.0"


class TestComplexIntegration:
    """Test complex integration scenarios."""

    def test_mate_compatibility_calculation(self):
        """Test mate compatibility scoring (lower score = more compatible)."""
        # Note: speed_modifier is a computed property, so we set underlying traits instead
        fish1 = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(1.0),
                color_hue=GeneticTrait(0.5),
                template_id=GeneticTrait(0),
                fin_size=GeneticTrait(1.0),
                tail_size=GeneticTrait(1.0),
                body_aspect=GeneticTrait(1.0),
                eye_size=GeneticTrait(1.0),
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(0.5),
                social_tendency=GeneticTrait(0.5),
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(None),
                poker_strategy_algorithm=GeneticTrait(None),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        # Similar fish - better compatibility (lower score)
        fish2 = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(1.0),
                color_hue=GeneticTrait(0.51),
                template_id=GeneticTrait(0),
                fin_size=GeneticTrait(1.0),
                tail_size=GeneticTrait(1.05),
                body_aspect=GeneticTrait(1.0),
                eye_size=GeneticTrait(1.0),
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(0.5),
                social_tendency=GeneticTrait(0.5),
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(None),
                poker_strategy_algorithm=GeneticTrait(None),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        # Very different fish - worse compatibility (higher score)
        fish3 = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(1.3),  # Changed from 1.5 to valid range
                color_hue=GeneticTrait(0.0),
                template_id=GeneticTrait(0),
                fin_size=GeneticTrait(0.6),
                tail_size=GeneticTrait(0.6),
                body_aspect=GeneticTrait(1.0),
                eye_size=GeneticTrait(1.0),
                pattern_intensity=GeneticTrait(0.5),
                pattern_type=GeneticTrait(0),
                lifespan_modifier=GeneticTrait(1.0),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(0.5),
                social_tendency=GeneticTrait(0.5),
                pursuit_aggression=GeneticTrait(0.5),
                prediction_skill=GeneticTrait(0.5),
                hunting_stamina=GeneticTrait(0.5),
                asexual_reproduction_chance=GeneticTrait(0.5),
                behavior_algorithm=GeneticTrait(None),
                poker_algorithm=GeneticTrait(None),
                poker_strategy_algorithm=GeneticTrait(None),
                mate_preferences=GeneticTrait({
                    "prefer_similar_size": 0.5,
                    "prefer_different_color": 0.5,
                    "prefer_high_energy": 0.5,
                }),
            ),
        )

        compatibility_similar = fish1.calculate_mate_compatibility(fish2)
        compatibility_different = fish1.calculate_mate_compatibility(fish3)

        # Similar fish should have lower compatibility score (lower is better)
        assert compatibility_similar < compatibility_different, \
            f"Similar fish compatibility {compatibility_similar:.3f} should be less than different fish {compatibility_different:.3f}"

    # Note: test_fitness_tracking_updates removed - fitness_score tracking was deprecated
    # Fitness is now implicit through survival and reproduction success

    def test_learned_behaviors_inheritance(self):
        """Test learned behaviors are inherited culturally."""
        # Use numeric values for learned behaviors (not strings)
        parent1_physical = PhysicalTraits(
            size_modifier=GeneticTrait(1.0),
            color_hue=GeneticTrait(0.5),
            template_id=GeneticTrait(0),
            fin_size=GeneticTrait(1.0),
            tail_size=GeneticTrait(1.0),
            body_aspect=GeneticTrait(1.0),
            eye_size=GeneticTrait(1.0),
            pattern_intensity=GeneticTrait(0.5),
            pattern_type=GeneticTrait(0),
            lifespan_modifier=GeneticTrait(1.0),
        )

        parent1_behavioral = BehavioralTraits(
            aggression=GeneticTrait(0.5),
            social_tendency=GeneticTrait(0.5),
            pursuit_aggression=GeneticTrait(0.5),
            prediction_skill=GeneticTrait(0.5),
            hunting_stamina=GeneticTrait(0.5),
            asexual_reproduction_chance=GeneticTrait(0.5),
            behavior_algorithm=GeneticTrait(None),
            poker_algorithm=GeneticTrait(None),
            poker_strategy_algorithm=GeneticTrait(None),
            mate_preferences=GeneticTrait({
                "prefer_similar_size": 0.5,
                "prefer_different_color": 0.5,
                "prefer_high_energy": 0.5,
            }),
        )

        parent1 = Genome(
            physical=parent1_physical,
            behavioral=parent1_behavioral,
            learned_behaviors={"territory_size": 50.0, "hunting_success": 0.8},
        )

        parent2 = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(parent1_physical.size_modifier.value),
                color_hue=GeneticTrait(parent1_physical.color_hue.value),
                template_id=GeneticTrait(parent1_physical.template_id.value),
                fin_size=GeneticTrait(parent1_physical.fin_size.value),
                tail_size=GeneticTrait(parent1_physical.tail_size.value),
                body_aspect=GeneticTrait(parent1_physical.body_aspect.value),
                eye_size=GeneticTrait(parent1_physical.eye_size.value),
                pattern_intensity=GeneticTrait(parent1_physical.pattern_intensity.value),
                pattern_type=GeneticTrait(parent1_physical.pattern_type.value),
                lifespan_modifier=GeneticTrait(parent1_physical.lifespan_modifier.value),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(parent1_behavioral.aggression.value),
                social_tendency=GeneticTrait(parent1_behavioral.social_tendency.value),
                pursuit_aggression=GeneticTrait(parent1_behavioral.pursuit_aggression.value),
                prediction_skill=GeneticTrait(parent1_behavioral.prediction_skill.value),
                hunting_stamina=GeneticTrait(parent1_behavioral.hunting_stamina.value),
                asexual_reproduction_chance=GeneticTrait(parent1_behavioral.asexual_reproduction_chance.value),
                behavior_algorithm=GeneticTrait(parent1_behavioral.behavior_algorithm.value),
                poker_algorithm=GeneticTrait(parent1_behavioral.poker_algorithm.value),
                poker_strategy_algorithm=GeneticTrait(parent1_behavioral.poker_strategy_algorithm.value),
                mate_preferences=GeneticTrait(dict(parent1_behavioral.mate_preferences.value)),
            ),
            learned_behaviors={"territory_size": 30.0, "social_rank": 3.0},
        )

        offspring = Genome(
            physical=PhysicalTraits(
                size_modifier=GeneticTrait(parent1_physical.size_modifier.value),
                color_hue=GeneticTrait(parent1_physical.color_hue.value),
                template_id=GeneticTrait(parent1_physical.template_id.value),
                fin_size=GeneticTrait(parent1_physical.fin_size.value),
                tail_size=GeneticTrait(parent1_physical.tail_size.value),
                body_aspect=GeneticTrait(parent1_physical.body_aspect.value),
                eye_size=GeneticTrait(parent1_physical.eye_size.value),
                pattern_intensity=GeneticTrait(parent1_physical.pattern_intensity.value),
                pattern_type=GeneticTrait(parent1_physical.pattern_type.value),
                lifespan_modifier=GeneticTrait(parent1_physical.lifespan_modifier.value),
            ),
            behavioral=BehavioralTraits(
                aggression=GeneticTrait(parent1_behavioral.aggression.value),
                social_tendency=GeneticTrait(parent1_behavioral.social_tendency.value),
                pursuit_aggression=GeneticTrait(parent1_behavioral.pursuit_aggression.value),
                prediction_skill=GeneticTrait(parent1_behavioral.prediction_skill.value),
                hunting_stamina=GeneticTrait(parent1_behavioral.hunting_stamina.value),
                asexual_reproduction_chance=GeneticTrait(parent1_behavioral.asexual_reproduction_chance.value),
                behavior_algorithm=GeneticTrait(parent1_behavioral.behavior_algorithm.value),
                poker_algorithm=GeneticTrait(parent1_behavioral.poker_algorithm.value),
                poker_strategy_algorithm=GeneticTrait(parent1_behavioral.poker_strategy_algorithm.value),
                mate_preferences=GeneticTrait(dict(parent1_behavioral.mate_preferences.value)),
            ),
        )

        # Inherit behaviors (requires offspring param)
        inherit_learned_behaviors(parent1, parent2, offspring, inheritance_rate=0.7)

        # Should have some behaviors from parents
        assert len(offspring.learned_behaviors) > 0, "Should inherit some behaviors"

        # Check that numeric values were averaged (allow mutation drift)
        if "territory_size" in offspring.learned_behaviors:
            # Should be roughly average of 50.0 and 30.0, with some mutation
            assert 20.0 <= offspring.learned_behaviors["territory_size"] <= 60.0

    def test_algorithm_evolution_preserves_functionality(self):
        """Test that evolved algorithms remain functional."""
        parent1_algo = GreedyFoodSeeker()
        parent2_algo = GreedyFoodSeeker()

        # Mutate parameters slightly (detection_range not search_radius)
        parent2_algo.parameters["detection_range"] = 0.8

        # Crossover (disable algorithm_switch_rate to ensure type preservation)
        child_algo = crossover_algorithms(
            parent1_algo, parent2_algo,
            mutation_rate=0.5,
            mutation_strength=0.1,
            algorithm_switch_rate=0.0  # Disable random algorithm switching for this test
        )

        # Should still be GreedyFoodSeeker
        assert isinstance(child_algo, GreedyFoodSeeker)

        # Should have valid parameters
        assert "detection_range" in child_algo.parameters
        assert 0.5 <= child_algo.parameters["detection_range"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
