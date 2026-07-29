"""Guards the platform-independent normal sampler used by genetics.

``random.gauss`` is Box-Muller and calls ``math.cos``, which comes from the
platform libm and measurably differs between Windows and Linux (see
docs/CROSS_PLATFORM_DIVERGENCE.md and tools/float_fingerprint.py). Because
``gauss`` is the mutation sampler, that made every genetic mutation
platform-dependent, and benchmark scores irreproducible across machines.

``core.deterministic_random.normal`` uses the Marsaglia polar method, which
needs only ``random()``, ``log()`` and ``sqrt()`` - all verified bit-identical
across those platforms.
"""

from __future__ import annotations

import math
import random
import statistics

import pytest

from core.deterministic_random import normal


def test_no_transcendental_calls_in_the_sampler(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole point: this must never reach a platform-dependent libm call.

    ``cos`` and ``tan`` were the only primitives that disagreed across
    platforms, so touching either would reintroduce exactly the bug this
    module exists to remove.
    """
    for name in ("cos", "sin", "tan", "exp", "pow"):

        def forbidden(*args: float, _name: str = name, **kwargs: float) -> float:
            raise AssertionError(f"normal() called math.{_name}, which is platform-dependent")

        monkeypatch.setattr(math, name, forbidden)

    rng = random.Random(42)
    for _ in range(1000):
        normal(rng, 0.0, 1.0)


def test_sampler_is_reproducible_for_a_seed() -> None:
    first_rng = random.Random(99)
    first = [normal(first_rng) for _ in range(50)]

    second_rng = random.Random(99)
    second = [normal(second_rng) for _ in range(50)]

    assert first == second
    assert len(set(first)) == len(first), "a seeded stream should not repeat values"


def test_sampler_matches_the_normal_distribution() -> None:
    """Sanity on the statistics, not just the determinism."""
    rng = random.Random(12345)
    samples = [normal(rng, 0.0, 1.0) for _ in range(50_000)]

    assert statistics.mean(samples) == pytest.approx(0.0, abs=0.02)
    assert statistics.stdev(samples) == pytest.approx(1.0, abs=0.02)

    within_one_sigma = sum(1 for s in samples if abs(s) <= 1.0) / len(samples)
    assert within_one_sigma == pytest.approx(0.6827, abs=0.01)


def test_mu_and_sigma_are_applied() -> None:
    rng = random.Random(3)
    samples = [normal(rng, 10.0, 4.0) for _ in range(50_000)]

    assert statistics.mean(samples) == pytest.approx(10.0, abs=0.1)
    assert statistics.stdev(samples) == pytest.approx(4.0, abs=0.1)


def test_genetics_no_longer_calls_random_gauss() -> None:
    """core/ must not reintroduce the platform-dependent sampler.

    A single ``rng.gauss`` reaching a mutation path is enough to make scores
    machine-specific again, and the symptom (a champion that reproduces
    locally but not in CI) is expensive to trace back here.
    """
    from pathlib import Path

    core_dir = Path(__file__).resolve().parents[1] / "core"
    offenders = [
        f"{path.relative_to(core_dir.parent)}:{number}"
        for path in core_dir.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if ".gauss(" in line
    ]

    assert not offenders, (
        "core/ calls random.gauss, which is Box-Muller over the platform's "
        "math.cos and therefore differs between Windows and Linux. Use "
        "core.deterministic_random.normal instead.\n  " + "\n  ".join(offenders)
    )
