import random

import pytest

from core.genetics import GeneticCrossoverMode, Genome


def test_crossover_modes_differ_for_continuous_traits() -> None:
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(1))
    parent2 = Genome.random(use_algorithm=False, rng=random.Random(2))

    parent1.physical.size_modifier.value = 0.8
    parent2.physical.size_modifier.value = 1.2

    # Disable mutation for this trait so crossover behavior is visible despite adaptive clamping.
    parent1.physical.size_modifier.mutation_rate = 0.0
    parent2.physical.size_modifier.mutation_rate = 0.0
    parent1.physical.size_modifier.mutation_strength = 0.0
    parent2.physical.size_modifier.mutation_strength = 0.0

    avg_child = Genome.from_parents(
        parent1,
        parent2,
        crossover_mode=GeneticCrossoverMode.AVERAGING,
        rng=random.Random(123),
    )
    rec_child = Genome.from_parents(
        parent1,
        parent2,
        crossover_mode=GeneticCrossoverMode.RECOMBINATION,
        rng=random.Random(123),
    )

    assert avg_child.physical.size_modifier.value == pytest.approx(1.0)
    assert rec_child.physical.size_modifier.value in (0.8, 1.2)
    assert rec_child.physical.size_modifier.value != pytest.approx(1.0)
