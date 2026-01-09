import random

import pytest

from core.code_pool.pool import BUILTIN_SEEK_NEAREST_FOOD_ID
from core.genetics import Genome
from core.genetics.behavioral import BehavioralTraits


def test_behavioral_traits_random_defaults():
    """Test that BehavioralTraits.random() sets the default policy."""
    rng = random.Random(42)
    traits = BehavioralTraits.random(rng)

    assert traits.movement_policy_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    # Legacy fields should be gone/None (not testing them as they are removed)


def test_mutation_can_swap_policy():
    """Test that mutation can swap to a different available policy."""
    rng = random.Random(42)

    # Parent with default policy
    parent = BehavioralTraits.random(rng)
    assert parent.movement_policy_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID

    # Force mutation with a new available policy
    # We need to run many trials because swap chance is small (10% of mutation rate)
    swapped = False
    available = ["NEW_POLICY_ID"]

    for _ in range(200):
        # High mutation rate to increase chance
        child = BehavioralTraits.from_parents(
            parent,
            parent,
            mutation_rate=1.0,
            mutation_strength=1.0,
            rng=rng,
            available_policies=available,
        )
        if child.movement_policy_id.value == "NEW_POLICY_ID":
            swapped = True
            break

    assert swapped, "Mutation failed to swap policy component ID"


def test_genome_clone_passes_policies():
    """Test that Genome.clone_with_mutation correctly propagates available_policies."""
    rng = random.Random(42)
    # create a random genome
    parent = Genome.random(rng=rng)

    # Clone with available policies
    # This previously raised TypeError: Genome.from_parents_weighted() got an unexpected keyword argument 'available_policies'
    child = Genome.clone_with_mutation(parent, rng=rng, available_policies=["NEW_POLICY"])

    assert child is not None


if __name__ == "__main__":
    pytest.main([__file__])
