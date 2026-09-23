"""The performance ratchet: deterministic work counts, pinned like file sizes.

Wall-clock time cannot gate CI, so nothing used to stop a change from quietly
making the engine or the live broadcast slower. ``tools/cost_counters.py``
measures work instead - calls into this repository's functions, spatial
queries, genome serializations, wire bytes - on fixed-seed runs. Those counts
are a property of the trajectory, not the machine: measured identical on
CPython 3.10 through 3.13.

This works like ``LEGACY_MAX_LINES`` in ``test_god_class_limits.py``, and only
ever tightens:

- A counter may not rise past its pin. If yours did on purpose, re-pin it in
  the same PR and say why; for a ``*.calls_per_frame`` total, back the re-pin
  with ``python tools/perf_check.py`` timings (see the module docstring of
  ``tools/cost_counters.py`` for why a total can rise on a change that is
  faster).
- A counter may not fall clearly below its pin either: that is a win, and the
  pin must come down with it so the next regression cannot spend it.

Re-pin by pasting the output of ``python tools/cost_counters.py``.
"""

from __future__ import annotations

import pytest

from tools.cost_counters import _repo_relative, measure_costs

# Measured 2026-09-23 (seed 42; see tools/cost_counters.py for each scenario).
COST_PINS: dict[str, float] = {
    # 15607.2 -> 15315.8 and 12346.7 -> 12094.6: one identity lookup per energy delta.
    # 15315.8 -> 15088.4 and 12094.6 -> 11887.5: per-genome diversity profile cache.
    "benchmark_tank.calls_per_frame": 15088.4,
    "benchmark_tank.spatial_calls_per_frame": 1035.2,
    # 12778.2 -> 12346.7: poker proximity builds its graph among ready fish first.
    "default_tank.calls_per_frame": 11887.5,
    # 1300.1 -> 1171.0 and 33510.3 -> 20960.0: deltas carry stats at 6 Hz, not 15.
    "broadcast.calls_per_delta": 1171.0,
    "broadcast.genome_serializations_per_delta": 0.1,
    "broadcast.bytes_per_delta": 20960.0,
    "broadcast.bytes_per_full_sync": 90122.0,
}

# Counts are exact on one platform. The slack absorbs cross-platform float
# drift reaching a decision inside the short measured window (see
# docs/CROSS_PLATFORM_DIVERGENCE.md), and the absolute floor keeps near-zero
# counters from failing on a single extra call.
RELATIVE_SLACK = 0.02
ABSOLUTE_SLACK = 0.5


def _band(pin: float) -> float:
    return max(pin * RELATIVE_SLACK, ABSOLUTE_SLACK)


@pytest.fixture(scope="module")
def costs() -> dict[str, float]:
    return measure_costs()


def test_every_counter_is_pinned(costs: dict[str, float]) -> None:
    assert set(costs) == set(COST_PINS), (
        "COST_PINS and tools/cost_counters.py disagree on the counter set; "
        "paste `python tools/cost_counters.py` output into COST_PINS"
    )


def test_no_cost_rose_past_its_pin(costs: dict[str, float]) -> None:
    risen = [
        f"  {key}: {costs[key]:.1f} > pin {pin:.1f} (+{100 * (costs[key] / pin - 1):.1f}%)"
        for key, pin in COST_PINS.items()
        if key in costs and costs[key] > pin + _band(pin)
    ]
    assert not risen, (
        "Work done rose past the ratchet (a regression, or a deliberate cost to re-pin "
        "with a reason):\n" + "\n".join(risen)
    )


def test_wins_are_harvested(costs: dict[str, float]) -> None:
    fallen = [
        f'  "{key}": {costs[key]:.1f},  # was {pin:.1f}'
        for key, pin in COST_PINS.items()
        if key in costs and costs[key] < pin - _band(pin)
    ]
    assert (
        not fallen
    ), "Work done fell below the ratchet - lower these pins so the win is kept:\n" + "\n".join(
        fallen
    )


@pytest.mark.parametrize(
    "filename",
    ["<frozen abc>", "<string>", "/usr/lib/python3.11/abc.py", "../outside_the_repo/x.py"],
)
def test_non_repo_code_is_never_counted(filename: str) -> None:
    """Stdlib and synthesized code differ between Python versions; counting
    them made 3.10 and 3.11 disagree by 1.6% on an identical trajectory."""
    assert _repo_relative(filename) is None


def test_repo_code_is_counted_by_relative_path() -> None:
    from tools import cost_counters

    assert _repo_relative(cost_counters.__file__) == "tools/cost_counters.py"
