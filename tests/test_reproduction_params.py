import random

from core.genetics import Genome, ReproductionParams


def test_from_parents_weighted_params_matches_direct_call() -> None:
    rng = random.Random(123)
    parent1 = Genome.random(use_algorithm=False, rng=rng)
    parent2 = Genome.random(use_algorithm=False, rng=rng)

    params = ReproductionParams(mutation_rate=0.0, mutation_strength=0.0)

    child_direct = Genome.from_parents_weighted(
        parent1=parent1,
        parent2=parent2,
        parent1_weight=0.6,
        mutation_rate=0.0,
        mutation_strength=0.0,
        rng=random.Random(999),
    )
    child_params = Genome.from_parents_weighted_params(
        parent1=parent1,
        parent2=parent2,
        parent1_weight=0.6,
        params=params,
        rng=random.Random(999),
    )

    assert child_params.debug_snapshot() == child_direct.debug_snapshot()
