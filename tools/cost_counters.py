#!/usr/bin/env python3
"""Deterministic cost counters for the performance ratchet (IMPROVEMENT_PROPOSALS 13.4).

Wall-clock time cannot gate CI: it is noisy and machine-dependent, which is why
nothing used to stop a change from quietly making the engine slower. *Work done*
can. For a fixed seed, the number of calls into this repository's own Python
functions is a property of the trajectory, not of the machine - measured
identical on CPython 3.10, 3.11, 3.12 and 3.13 - and so are the bytes a
broadcast puts on the wire.

``tests/test_cost_ratchet.py`` pins each counter below and fails when one rises
past its pin (a regression, or a deliberate cost that needs a reviewed re-pin)
or falls clearly below it (a win that must be harvested by lowering the pin, so
the ratchet only ever tightens).

Only functions defined in repository files are counted, and never synthesized
code objects (``<listcomp>``, ``<genexpr>``, ``<lambda>``, dataclass-generated
methods): CPython inlines comprehensions from 3.12 on, so counting them would
make the numbers version-dependent.

What the totals do and do not see. ``*.calls_per_frame`` is a broad proxy for
interpreter work, and it can move the wrong way: replacing a per-item
dataclass allocation (synthesized ``__init__``, uncounted) with a call to a
small helper (counted) made ``select_food_target`` 5% faster on survival_5k
while *raising* ``benchmark_tank.calls_per_frame`` 2.5%. So a raised total is a
question, not a verdict - answer it with ``tools/perf_check.py`` timings and
re-pin. The named counters (spatial queries, genome serializations, wire
bytes) count domain operations and cannot be fooled by refactoring.

Print the current values, ready to paste into the test's ``COST_PINS``::

    python tools/cost_counters.py
"""

from __future__ import annotations

import cProfile
import importlib.util
import os
import pstats
import sys
from collections import Counter
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any, TypeVar

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

T = TypeVar("T")

SEED = 42
# Enough fish that per-fish and fish-pair costs dominate, without the long
# warmup a naturally grown population needs (survival_5k starts near 15).
INITIAL_FISH = 50
WARMUP_FRAMES = 200
MEASURED_FRAMES = 100
BROADCAST_WARMUP_FRAMES = 150
MEASURED_BROADCASTS = 20
GENOME_TO_DICT = "core/genetics/genome_codec.py:genome_to_dict"


def _repo_relative(filename: str) -> str | None:
    """Repo-relative path of a code object's file, or None if outside the repo."""
    if filename.startswith("<"):  # <frozen abc>, <string> (dataclass __init__), ...
        return None
    path = os.path.normpath(os.path.abspath(filename))
    root = str(ROOT)
    if not path.startswith(root + os.sep):
        return None
    return path[len(root) + 1 :].replace(os.sep, "/")


def profile_repo_calls(run: Callable[[], T]) -> tuple[T, Counter[str]]:
    """Profile ``run``; return its result and repo call counts keyed ``"path:name"``."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        result = run()
    finally:
        profiler.disable()

    counts: Counter[str] = Counter()
    stats: dict[Any, Any] = pstats.Stats(profiler).stats  # type: ignore[attr-defined]
    for (filename, _line, name), (_cc, calls, _tt, _ct, _callers) in stats.items():
        if name.startswith("<"):
            continue
        rel = _repo_relative(filename)
        if rel is not None:
            counts[f"{rel}:{name}"] += calls
    return result, counts


def _prefixed(counts: Counter[str], prefix: str) -> int:
    return sum(n for key, n in counts.items() if key.startswith(prefix))


def _survival_world_config() -> dict[str, Any]:
    path = ROOT / "benchmarks" / "tank" / "survival_5k.py"
    spec = importlib.util.spec_from_file_location("_cost_counters_survival_5k", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.WORLD_CONFIG)


def _engine_counters(config: dict[str, Any]) -> tuple[float, float]:
    from core.worlds import WorldRegistry
    from core.worlds.interfaces import FAST_STEP_ACTION

    world = WorldRegistry.create_world("tank", seed=SEED, config=config)
    world.reset(seed=SEED, config=config)
    fast: dict[str, object] = {FAST_STEP_ACTION: True}
    for _ in range(WARMUP_FRAMES):
        world.step(fast)

    def run() -> None:
        for _ in range(MEASURED_FRAMES):
            world.step(fast)

    _, counts = profile_repo_calls(run)
    total = sum(counts.values())
    return total / MEASURED_FRAMES, _prefixed(counts, "core/spatial/") / MEASURED_FRAMES


def _broadcast_counters() -> dict[str, float]:
    """Costs of building and sending one 15 Hz delta frame (the live server path)."""
    import logging

    from backend.simulation_runner import SimulationRunner
    from core.worlds.interfaces import FAST_STEP_ACTION

    logging.disable(logging.WARNING)
    try:
        runner = SimulationRunner(seed=SEED, world_id="cost-counters")
    finally:
        logging.disable(logging.NOTSET)
    runner.running = True
    publisher = runner.state_publisher
    fast: dict[str, object] = {FAST_STEP_ACTION: True}

    def loop_step() -> None:
        # What backend/runner/loop.py does per frame.
        runner.world.step(fast)
        runner._sample_metrics_if_due()

    for _ in range(BROADCAST_WARMUP_FRAMES):
        loop_step()
    full_bytes = len(
        publisher.serialize_state(publisher.get_state(runner, force_full=True, allow_delta=False))
    )

    delta_bytes = 0
    counts: Counter[str] = Counter()
    for _ in range(MEASURED_BROADCASTS):
        loop_step()
        loop_step()  # the broadcast runs at 15 Hz against a 30 Hz sim
        state, frame_counts = profile_repo_calls(
            partial(publisher.get_state, runner, force_full=False, allow_delta=True)
        )
        counts += frame_counts
        delta_bytes += len(publisher.serialize_state(state))
    n = MEASURED_BROADCASTS
    return {
        "broadcast.calls_per_delta": sum(counts.values()) / n,
        "broadcast.genome_serializations_per_delta": counts[GENOME_TO_DICT] / n,
        "broadcast.bytes_per_delta": delta_bytes / n,
        "broadcast.bytes_per_full_sync": float(full_bytes),
    }


def measure_costs() -> dict[str, float]:
    """Every ratcheted counter, keyed as in ``tests/test_cost_ratchet.py::COST_PINS``."""
    benchmark_config = dict(_survival_world_config(), initial_fish_count=INITIAL_FISH)
    bench_calls, bench_spatial = _engine_counters(benchmark_config)
    full_calls, _ = _engine_counters({"headless": True, "initial_fish_count": INITIAL_FISH})
    return {
        "benchmark_tank.calls_per_frame": bench_calls,
        "benchmark_tank.spatial_calls_per_frame": bench_spatial,
        "default_tank.calls_per_frame": full_calls,
        **_broadcast_counters(),
    }


def main() -> int:
    costs = measure_costs()
    print("COST_PINS: dict[str, float] = {")
    for key, value in costs.items():
        print(f'    "{key}": {value:.1f},')
    print("}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
