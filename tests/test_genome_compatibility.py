import random

from core.genetics import Genome


def test_trait_containers():
    rng = random.Random(42)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Read trait containers
    assert isinstance(g.physical.size_modifier.value, float)
    assert isinstance(g.behavioral.aggression.value, float)
    assert isinstance(g.behavioral.mate_preferences.value, dict)

    # Set values directly on GeneticTrait containers
    g.physical.size_modifier.value = 1.77
    assert abs(g.physical.size_modifier.value - 1.77) < 1e-6

    g.behavioral.aggression.value = 0.12
    assert abs(g.behavioral.aggression.value - 0.12) < 1e-6


def test_cache_invalidation_on_trait_change():
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Compute baseline speed
    base_speed = g.speed_modifier

    # Change a trait that affects speed and invalidate caches via API
    g.physical.fin_size.value = g.physical.fin_size.value + 0.5
    g.invalidate_caches()
    new_speed = g.speed_modifier

    assert new_speed != base_speed
