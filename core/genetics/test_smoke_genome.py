"""Smoke tests for Genome compatibility after refactor."""

import random
from core.genetics import Genome


def smoke():
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)
    # Access compatibility properties
    print('size_modifier:', g.size_modifier)
    print('aggression:', g.aggression)
    print('mate_prefs:', g.mate_preferences)


if __name__ == '__main__':
    smoke()
