import random

from core.genetics import Genome


def test_getters_and_setters():
    rng = random.Random(42)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Read compatibility properties and compare to nested trait values
    assert g.size_modifier == g.physical.size_modifier.value
    assert g.aggression == g.behavioral.aggression.value
    assert g.mate_preferences == g.behavioral.mate_preferences.value

    # Set properties and ensure underlying GeneticTrait values update
    g.size_modifier = 1.77
    assert abs(g.physical.size_modifier.value - 1.77) < 1e-6

    g.aggression = 0.12
    assert abs(g.behavioral.aggression.value - 0.12) < 1e-6


def test_cache_invalidation_on_trait_change():
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Compute baseline speed
    base_speed = g.speed_modifier

    # Change a trait that affects speed and invalidate caches via API
    g.fin_size = g.fin_size + 0.5
    g.invalidate_caches()
    new_speed = g.speed_modifier

    assert new_speed != base_speed
