"""Tests for the soccer evolution experiment runner."""

from core.code_pool import create_default_genome_code_pool
from core.experiments.soccer_training_evolution import (
    EvolutionResult,
    GenerationStats,
    create_population,
    run_generations,
    select_parents,
)


class TestSoccerEvolutionRunner:
    """Test soccer evolution experiment runner."""

    def test_run_generations_deterministic(self):
        """Same seed produces identical results (determinism)."""
        result1 = run_generations(
            seed=42,
            generations=3,
            population_size=6,
            episode_frames=50,
            top_k_selection=2,
        )

        result2 = run_generations(
            seed=42,
            generations=3,
            population_size=6,
            episode_frames=50,
            top_k_selection=2,
        )

        # Same seed should produce identical stats
        assert len(result1.generations) == len(result2.generations)
        for s1, s2 in zip(result1.generations, result2.generations):
            assert s1.best_fitness == s2.best_fitness
            assert s1.mean_fitness == s2.mean_fitness
            assert s1.goals_left == s2.goals_left
            assert s1.goals_right == s2.goals_right

    def test_run_generations_different_seeds(self):
        """Different seeds produce different results."""
        result1 = run_generations(
            seed=42,
            generations=2,
            population_size=4,
            episode_frames=30,
        )

        result2 = run_generations(
            seed=12345,
            generations=2,
            population_size=4,
            episode_frames=30,
        )

        # Different seeds should produce different stats (with high probability)
        # At least one stat should differ
        any_different = False
        for s1, s2 in zip(result1.generations, result2.generations):
            if s1.best_fitness != s2.best_fitness or s1.mean_fitness != s2.mean_fitness:
                any_different = True
                break

        assert any_different, "Different seeds should produce different results"

    def test_run_generations_returns_result(self):
        """run_generations returns a structured EvolutionResult."""
        result = run_generations(
            seed=42,
            generations=2,
            population_size=4,
            episode_frames=30,
        )

        assert isinstance(result, EvolutionResult)
        assert len(result.generations) == 2
        assert result.best_genome is not None
        assert isinstance(result.best_fitness, float)

    def test_run_generations_smoke_test(self):
        """Runner completes quickly with small parameters (smoke test)."""
        import time

        start = time.time()

        result = run_generations(
            seed=42,
            generations=2,
            population_size=4,
            episode_frames=20,
        )

        elapsed = time.time() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0, f"Smoke test took too long: {elapsed:.2f}s"
        assert len(result.generations) == 2

    def test_generation_stats_structure(self):
        """GenerationStats has correct structure."""
        result = run_generations(
            seed=42,
            generations=1,
            population_size=4,
            episode_frames=20,
        )

        assert len(result.generations) == 1
        stats = result.generations[0]

        assert isinstance(stats, GenerationStats)
        assert stats.generation == 0
        assert isinstance(stats.best_fitness, float)
        assert isinstance(stats.mean_fitness, float)
        assert isinstance(stats.population_size, int)

    def test_create_population_size(self):
        """create_population creates correct number of genomes."""
        import random

        rng = random.Random(42)
        pool = create_default_genome_code_pool()

        population = create_population(rng, 10, pool)

        assert len(population) == 10

    def test_select_parents_top_k(self):
        """select_parents returns top K genomes by fitness."""
        import random

        from core.experiments.soccer_training_evolution import AgentResult
        from core.genetics import Genome

        rng = random.Random(42)
        results = [
            AgentResult(
                player_id=f"p{i}",
                team="left",
                goals=0,
                fitness=float(i * 10),
                genome=Genome.random(use_algorithm=False, rng=rng),
            )
            for i in range(5)
        ]

        parents = select_parents(results, top_k=2)

        assert len(parents) == 2
        # Best fitness (40) and second best (30) should be selected
