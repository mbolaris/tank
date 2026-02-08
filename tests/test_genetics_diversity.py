"""Tests for genetic diversity metrics, distance, and speciation support."""

import random

import pytest

from core.genetics import Genome
from core.genetics.diversity import (
    diversity_bonus,
    genetic_distance,
    population_diversity,
    sharing_factor,
)


@pytest.fixture
def seeded_rng():
    return random.Random(42)


@pytest.fixture
def random_genomes(seeded_rng):
    """Create a population of random genomes."""
    return [Genome.random(use_algorithm=True, rng=seeded_rng) for _ in range(10)]


class TestGeneticDistance:
    def test_self_distance_is_zero(self, seeded_rng):
        """A genome's distance to itself should be zero."""
        g = Genome.random(use_algorithm=True, rng=seeded_rng)
        assert genetic_distance(g, g) == 0.0

    def test_distance_is_symmetric(self, seeded_rng):
        """Distance from A to B should equal distance from B to A."""
        g1 = Genome.random(use_algorithm=True, rng=seeded_rng)
        g2 = Genome.random(use_algorithm=True, rng=seeded_rng)
        assert genetic_distance(g1, g2) == pytest.approx(genetic_distance(g2, g1))

    def test_distance_is_non_negative(self, random_genomes):
        """All distances should be non-negative."""
        for i in range(len(random_genomes)):
            for j in range(i + 1, len(random_genomes)):
                d = genetic_distance(random_genomes[i], random_genomes[j])
                assert d >= 0.0

    def test_different_genomes_have_positive_distance(self, seeded_rng):
        """Two independently random genomes should have non-zero distance."""
        g1 = Genome.random(use_algorithm=True, rng=seeded_rng)
        g2 = Genome.random(use_algorithm=True, rng=seeded_rng)
        assert genetic_distance(g1, g2) > 0.0

    def test_clone_has_small_distance(self, seeded_rng):
        """A clone with mutation should have small but positive distance."""
        parent = Genome.random(use_algorithm=True, rng=seeded_rng)
        clone = Genome.clone_with_mutation(parent, rng=seeded_rng)
        d = genetic_distance(parent, clone)
        # Clone should be similar but not identical due to mutation
        assert 0.0 < d < 1.0

    def test_distance_without_algorithm(self, seeded_rng):
        """Distance should work for genomes without composable behavior."""
        g1 = Genome.random(use_algorithm=False, rng=seeded_rng)
        g2 = Genome.random(use_algorithm=False, rng=seeded_rng)
        d = genetic_distance(g1, g2)
        assert d >= 0.0


class TestPopulationDiversity:
    def test_single_genome_has_zero_diversity(self, seeded_rng):
        """A population of one has zero diversity."""
        g = Genome.random(use_algorithm=True, rng=seeded_rng)
        metrics = population_diversity([g])
        assert metrics["mean_distance"] == 0.0
        assert metrics["effective_diversity"] == 0.0

    def test_empty_population(self):
        """Empty population should return zero metrics."""
        metrics = population_diversity([])
        assert metrics["mean_distance"] == 0.0
        assert metrics["num_niches"] == 0

    def test_diverse_population_has_positive_metrics(self, random_genomes):
        """A population of random genomes should have positive diversity."""
        metrics = population_diversity(random_genomes)
        assert metrics["mean_distance"] > 0.0
        assert metrics["max_distance"] > 0.0
        assert metrics["behavioral_entropy"] >= 0.0
        assert metrics["num_niches"] >= 1

    def test_clone_population_has_low_diversity(self, seeded_rng):
        """A population of clones should have low diversity."""
        parent = Genome.random(use_algorithm=True, rng=seeded_rng)
        clones = [Genome.clone_with_mutation(parent, rng=seeded_rng) for _ in range(10)]
        metrics = population_diversity(clones)
        # Clones with mutation should have low but non-zero diversity
        assert metrics["mean_distance"] < 0.5

    def test_effective_diversity_range(self, random_genomes):
        """Effective diversity should be in [0, 1]."""
        metrics = population_diversity(random_genomes)
        assert 0.0 <= metrics["effective_diversity"] <= 1.0

    def test_returns_all_expected_keys(self, random_genomes):
        """Should return all expected metric keys."""
        metrics = population_diversity(random_genomes)
        expected_keys = {
            "mean_distance",
            "max_distance",
            "min_distance",
            "behavioral_entropy",
            "num_niches",
            "effective_diversity",
        }
        assert set(metrics.keys()) == expected_keys


class TestSharingFactor:
    def test_isolated_genome_has_factor_one(self, seeded_rng):
        """A genome far from all others should have sharing factor ~1."""
        genomes = [Genome.random(use_algorithm=True, rng=seeded_rng) for _ in range(5)]
        # With very small sigma, most genomes should be isolated
        sf = sharing_factor(genomes[0], genomes, sigma=0.01)
        assert sf == pytest.approx(1.0, abs=0.01)

    def test_sharing_factor_with_clones(self, seeded_rng):
        """Clones should have high sharing factor."""
        parent = Genome.random(use_algorithm=True, rng=seeded_rng)
        # Create actual clone objects (not same object reference) so `is` check works
        clones = [Genome.clone_with_mutation(parent, rng=random.Random(i)) for i in range(5)]
        sf = sharing_factor(clones[0], clones, sigma=1.0)
        # Clones with light mutation should still be close enough to share
        assert sf >= 2.0

    def test_sharing_factor_non_negative(self, random_genomes):
        """Sharing factor should always be >= 1.0."""
        for g in random_genomes:
            sf = sharing_factor(g, random_genomes, sigma=0.5)
            assert sf >= 1.0


class TestDiversityBonus:
    def test_unique_genome_gets_full_bonus(self, seeded_rng):
        """A unique genome should get the full diversity bonus."""
        genomes = [Genome.random(use_algorithm=True, rng=seeded_rng) for _ in range(5)]
        # With very small sigma, genome is isolated
        bonus = diversity_bonus(genomes[0], genomes, sigma=0.01, bonus_weight=0.1)
        assert bonus == pytest.approx(0.1, abs=0.01)

    def test_clone_gets_small_bonus(self, seeded_rng):
        """A clone in a crowd should get a small bonus."""
        parent = Genome.random(use_algorithm=True, rng=seeded_rng)
        # Create actual clone objects so `is` check doesn't skip them all
        clones = [Genome.clone_with_mutation(parent, rng=random.Random(i)) for i in range(10)]
        bonus = diversity_bonus(clones[0], clones, sigma=1.0, bonus_weight=0.1)
        assert bonus < 0.05  # Much less than full bonus

    def test_bonus_range(self, random_genomes):
        """Bonus should be in [0, bonus_weight]."""
        for g in random_genomes:
            bonus = diversity_bonus(g, random_genomes, sigma=0.5, bonus_weight=0.15)
            assert 0.0 <= bonus <= 0.15
