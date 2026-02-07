import random

import pytest

from core.entities.fish import Fish
from core.environment import Environment
from core.genetics import (BehavioralTraits, GeneticCrossoverMode,
                           GeneticTrait, Genome, PhysicalTraits)


class TestGeneticsRefactor:
    def test_genetic_trait_initialization(self):
        """Test that GeneticTrait initializes correctly with default and custom metadata."""
        # Default metadata
        trait = GeneticTrait(1.0)
        assert trait.value == 1.0
        assert trait.mutation_rate == 1.0
        assert trait.mutation_strength == 1.0
        assert trait.hgt_probability == 0.1

        # Custom metadata
        trait_custom = GeneticTrait(
            0.5, mutation_rate=2.0, mutation_strength=0.5, hgt_probability=0.8
        )
        assert trait_custom.value == 0.5
        assert trait_custom.mutation_rate == 2.0
        assert trait_custom.mutation_strength == 0.5
        assert trait_custom.hgt_probability == 0.8

    def test_genetic_trait_mutation(self):
        """Test that GeneticTrait metadata can mutate."""
        rng = random.Random(42)
        trait = GeneticTrait(1.0)

        # Force mutation by calling multiple times or mocking rng if needed
        # Since we use a seeded rng, we can just check if values change over many iterations
        initial_rate = trait.mutation_rate
        changed = False
        for _ in range(100):
            trait.mutate_meta(rng)
            if trait.mutation_rate != initial_rate:
                changed = True
                break

        assert changed, "Metadata should mutate over time"

    def test_physical_traits_random(self):
        """Test random generation of PhysicalTraits."""
        rng = random.Random(123)
        phys = PhysicalTraits.random(rng)

        assert isinstance(phys.size_modifier, GeneticTrait)
        assert 0.5 <= phys.size_modifier.value <= 2.0

        assert isinstance(phys.template_id, GeneticTrait)
        assert isinstance(phys.template_id.value, int)
        assert 0 <= phys.template_id.value <= 5

    def test_behavioral_traits_random(self):
        """Test random generation of BehavioralTraits."""
        rng = random.Random(456)
        behav = BehavioralTraits.random(rng)

        assert isinstance(behav.aggression, GeneticTrait)
        assert 0.0 <= behav.aggression.value <= 1.0

        assert isinstance(behav.mate_preferences, GeneticTrait)
        assert isinstance(behav.mate_preferences.value, dict)
        assert "prefer_similar_size" in behav.mate_preferences.value
        assert "prefer_high_pattern_intensity" in behav.mate_preferences.value
        assert "size_modifier" in behav.mate_preferences.value
        assert "pattern_type" in behav.mate_preferences.value

    def test_genome_traits(self):
        """Test that Genome trait containers expose expected values."""
        rng = random.Random(42)
        genome = Genome.random(rng=rng)

        # Test value access
        val = genome.physical.size_modifier.value
        assert val == genome.physical.size_modifier.value

        # Test mutation through container
        genome.physical.size_modifier.value = 1.25
        assert genome.physical.size_modifier.value == 1.25

        # Test derived property
        # speed_modifier depends on template_id, fin_size, tail_size, body_aspect
        # Just ensure it returns a float and doesn't crash
        assert isinstance(genome.speed_modifier, float)
        assert isinstance(genome.metabolism_rate, float)

    def test_genome_inheritance(self):
        """Test inheritance from parents."""
        rng = random.Random(42)
        parent1 = Genome.random(rng=rng)
        parent2 = Genome.random(rng=rng)

        # Set distinct values to verify mixing
        parent1.physical.size_modifier.value = 0.8
        parent2.physical.size_modifier.value = 1.2

        # Set metadata to verify inheritance
        parent1.physical.size_modifier.mutation_rate = 0.5
        parent2.physical.size_modifier.mutation_rate = 1.5

        offspring = Genome.from_parents(
            parent1, parent2, mutation_rate=0.0, mutation_strength=0.0, rng=rng
        )

        # With 0 mutation, value should be between parents (weighted average logic in base inherit_trait)
        # Note: inherit_trait might add small noise even with 0 mutation if not careful,
        # but generally it blends.
        assert 0.8 <= offspring.physical.size_modifier.value <= 1.2

        # Check metadata inheritance (average of parents)
        # 0.5 and 1.5 average to 1.0. Allow small float error or mutation noise if any.
        assert 0.9 <= offspring.physical.size_modifier.mutation_rate <= 1.1

    def test_genome_crossover_modes(self):
        """Test different crossover modes (interface check)."""
        rng = random.Random(42)
        p1 = Genome.random(rng=rng)
        p2 = Genome.random(rng=rng)

        # Currently implementation delegates to weighted average, but we ensure it runs
        offspring_avg = Genome.from_parents(
            p1, p2, crossover_mode=GeneticCrossoverMode.AVERAGING, rng=rng
        )
        assert isinstance(offspring_avg, Genome)

        offspring_rec = Genome.from_parents(
            p1, p2, crossover_mode=GeneticCrossoverMode.RECOMBINATION, rng=rng
        )
        assert isinstance(offspring_rec, Genome)

    def test_fish_integration(self):
        """Test that a Fish entity can be created and updated with the new Genome."""
        # Mock environment
        rng = random.Random(42)
        env = Environment(width=800, height=600, rng=rng)

        # Create fish with random genome
        from core.movement_strategy import AlgorithmicMovement

        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="test_fish",
            x=100,
            y=100,
            speed=5.0,
        )

        # Check accessing traits via fish properties (if any exist) or genome
        assert isinstance(fish.genome, Genome)
        assert isinstance(fish.genome.physical.size_modifier.value, float)

        # Run update loop
        try:
            fish.update(16)  # 16ms frame
        except Exception as e:
            pytest.fail(f"Fish update failed with new genetics: {e}")

    def test_mate_attraction(self):
        """Test mate attraction calculation."""
        rng = random.Random(42)
        g1 = Genome.random(rng=rng)
        g2 = Genome.random(rng=rng)

        score = g1.calculate_mate_attraction(g2)
        assert 0.0 <= score <= 1.0

        # Identical genomes should have high compatibility (based on size/traits)
        # but color preference might lower it (prefer different colors)
        g3 = Genome.random(rng=rng)
        g3.physical = g1.physical  # Clone physical traits
        # Reset color to be different to maximize score if preference is for difference
        g3.physical.color_hue.value = (g1.physical.color_hue.value + 0.5) % 1.0

        score_clone = g1.calculate_mate_attraction(g3)
        assert score_clone > 0.0

    def test_meta_mutation_occurs(self):
        """Test that meta-genetic parameters can mutate."""
        rng = random.Random(42)
        trait = GeneticTrait(1.0, mutation_rate=1.0, mutation_strength=1.0, hgt_probability=0.5)

        # Record initial values
        initial_rate = trait.mutation_rate
        initial_strength = trait.mutation_strength
        initial_hgt = trait.hgt_probability

        # Run many mutations to ensure at least one parameter changes
        changed = False
        for _ in range(200):
            trait.mutate_meta(rng)
            if (
                trait.mutation_rate != initial_rate
                or trait.mutation_strength != initial_strength
                or trait.hgt_probability != initial_hgt
            ):
                changed = True
                break

        assert changed, "Meta-genetic parameters should mutate over time"

    def test_meta_mutation_respects_bounds(self):
        """Test that meta-genetic mutations stay within valid bounds."""
        rng = random.Random(123)
        trait = GeneticTrait(1.0)

        # Mutate many times
        for _ in range(500):
            trait.mutate_meta(rng)

            # Check bounds
            assert (
                0.1 <= trait.mutation_rate <= 5.0
            ), f"mutation_rate out of bounds: {trait.mutation_rate}"
            assert (
                0.1 <= trait.mutation_strength <= 5.0
            ), f"mutation_strength out of bounds: {trait.mutation_strength}"
            assert (
                0.0 <= trait.hgt_probability <= 1.0
            ), f"hgt_probability out of bounds: {trait.hgt_probability}"

    def test_meta_inheritance_in_offspring(self):
        """Test that meta-genetic parameters are inherited and can evolve."""
        # Create parents with distinct meta-parameters
        rng = random.Random(42)
        parent1 = Genome.random(rng=rng)
        parent1.physical.size_modifier.mutation_rate = 0.5
        parent1.physical.size_modifier.mutation_strength = 0.5

        parent2 = Genome.random(rng=rng)
        parent2.physical.size_modifier.mutation_rate = 2.0
        parent2.physical.size_modifier.mutation_strength = 2.0

        # Create offspring
        offspring = Genome.from_parents_weighted(
            parent1, parent2, mutation_rate=0.0, mutation_strength=0.0, rng=rng
        )

        # Offspring should have averaged meta-parameters (with possible mutation)
        # Average would be 1.25, allow some deviation from mutation
        assert 0.5 <= offspring.physical.size_modifier.mutation_rate <= 2.5
        assert 0.5 <= offspring.physical.size_modifier.mutation_strength <= 2.5

    def test_meta_evolution_over_generations(self):
        """Test that meta-parameters evolve over multiple generations."""
        # Start with population with varying mutation rates to introduce diversity
        # Meta-mutation has only 1% chance per generation, so we need initial variation
        # to reliably test that the system preserves/propagates variation
        population = []
        rng = random.Random(42)
        for i in range(20):
            g = Genome.random(rng=rng)
            # Start with some variation to test inheritance/mutation
            g.physical.size_modifier.mutation_rate = 0.3 + (i * 0.02)
            g.physical.size_modifier.mutation_strength = 0.3 + (i * 0.015)
            population.append(g)

        # Evolve for many generations to allow 1% meta-mutation to accumulate
        for gen in range(50):
            new_population = []
            for _ in range(20):
                p1 = random.choice(population)
                p2 = random.choice(population)
                offspring = Genome.from_parents(p1, p2, rng=rng)
                new_population.append(offspring)
            population = new_population

        # Check that meta-parameters have varied
        mutation_rates = [g.physical.size_modifier.mutation_rate for g in population]

        # Should have some variation (not all the same)
        # With 1% meta-mutation per trait per generation over 50 generations,
        # we expect some variation due to both inheritance averaging and mutation
        assert len(set(mutation_rates)) > 1, "Meta-parameters should vary across population"

        # All should still be within valid bounds (clamped to 0.5-2.0 in mutate_meta)
        for rate in mutation_rates:
            assert 0.1 <= rate <= 5.0


if __name__ == "__main__":
    # Manually run tests if executed as script
    t = TestGeneticsRefactor()
    t.test_genetic_trait_initialization()
    t.test_genetic_trait_mutation()
    t.test_physical_traits_random()
    t.test_behavioral_traits_random()
    t.test_genome_traits()
    t.test_genome_inheritance()
    t.test_genome_crossover_modes()
    # t.test_fish_integration() # Requires more setup
    t.test_mate_attraction()
    t.test_meta_mutation_occurs()
    t.test_meta_mutation_respects_bounds()
    t.test_meta_inheritance_in_offspring()
    t.test_meta_evolution_over_generations()
    print("All manual tests passed!")
