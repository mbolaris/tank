import random

import pytest

from core.genetics import Genome


def test_validate_ok_for_random_genome() -> None:
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)
    result = g.validate()
    assert result["ok"] is True
    assert result["issues"] == []


def test_assert_valid_raises_on_out_of_range_trait() -> None:
    rng = random.Random(2)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Break a spec-bounded trait.
    g.physical.size_modifier.value = 999.0

    with pytest.raises(ValueError, match="Invalid genome"):
        g.assert_valid()


def test_assert_valid_raises_on_nan_trait() -> None:
    rng = random.Random(3)
    g = Genome.random(use_algorithm=False, rng=rng)
    g.behavioral.aggression.value = float("nan")

    with pytest.raises(ValueError, match="not finite"):
        g.assert_valid()
