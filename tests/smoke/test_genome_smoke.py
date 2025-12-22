"""Smoke tests for Genome trait containers."""

import random

from core.genetics import Genome


def smoke():
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)
    print("size_modifier:", g.physical.size_modifier.value)
    print("aggression:", g.behavioral.aggression.value)
    print("mate_prefs:", g.behavioral.mate_preferences.value)


if __name__ == "__main__":
    smoke()
