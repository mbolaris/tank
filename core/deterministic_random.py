"""Platform-independent normal sampling for the genetics path.

Why not ``random.gauss``
------------------------
CPython implements ``random.gauss`` with the Box-Muller transform::

    x2pi = random() * TWOPI
    g2rad = _sqrt(-2.0 * _log(1.0 - random()))
    z = _cos(x2pi) * g2rad

``math.cos`` comes from the platform libm. IEEE 754 pins ``+ - * /`` and
``sqrt`` to correctly-rounded results but says nothing about transcendentals,
so ``cos`` is free to differ in the last ulp between Windows and glibc - and
measurably does. ``tools/float_fingerprint.py`` compared every primitive the
simulation touches across Windows/CPython 3.14 and CI's Linux/CPython 3.10;
``cos`` and ``tan`` were the only two that disagreed, and ``gauss`` inherited
it. Notably ``sin`` agreed while ``cos`` did not, so this had to be measured
rather than reasoned about. See docs/CROSS_PLATFORM_DIVERGENCE.md.

That made every genetic mutation platform-dependent from the first draw, which
is why the same commit and seed scored 10.150218544250826 on Windows and
9.967411959401476 on Linux CI.

The Marsaglia polar method reaches the same distribution using only
``random()``, ``log()`` and ``sqrt()`` - all three verified bit-identical
across those platforms.

This is deliberately *not* a drop-in for every ``gauss`` call in the codebase.
It is for paths that must reproduce across machines: genetics and anything
feeding a benchmark score.
"""

from __future__ import annotations

import math
import random


def normal(rng: random.Random, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Sample a normal deviate identically on every platform.

    Args:
        rng: Source of uniform randomness. Its ``random()`` stream is
            specified exactly by the Mersenne Twister, so it is safe.
        mu: Mean.
        sigma: Standard deviation.

    Returns:
        A sample from ``N(mu, sigma)``.

    Note:
        Consumes a *variable* number of draws from ``rng`` - the rejection
        loop runs until it lands inside the unit circle (~21.5% rejection
        rate). ``random.gauss`` consumes exactly two. Switching between them
        therefore reshuffles every downstream random decision and moves
        benchmark scores, so champions must be re-baselined alongside it.
    """
    while True:
        u = 2.0 * rng.random() - 1.0
        v = 2.0 * rng.random() - 1.0
        s = u * u + v * v
        # s == 0 would divide by zero; s >= 1 is outside the unit circle.
        if 0.0 < s < 1.0:
            return mu + sigma * u * math.sqrt(-2.0 * math.log(s) / s)
