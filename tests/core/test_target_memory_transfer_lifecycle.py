"""Subprocess lifecycle regression for repeated transfer-study evaluations.

The in-process stability test (test_target_memory_transfer_gym.py) measures a
warmup plus three evaluations, which cannot catch failures that only appear at
a later call - a fifth-call stall was observed on Python 3.13 while four
consecutive evaluations completed normally. This test runs at least eight full
evaluations in a fresh child interpreter and records per-evaluation wall time,
resident set size, and live object counts, so a late-onset stall, progressive
slowdown, or resource leak fails loudly with diagnostics instead of hanging a
larger study.

The child arms ``faulthandler.dump_traceback_later`` before every evaluation:
if any single evaluation stalls past the per-evaluation timeout, the child
dumps a stack trace of the hung frame to stderr and exits, and the parent
surfaces that trace in the assertion message.

Knobs (env vars, for local investigation - defaults match CI):
- ``TANK_LIFECYCLE_EVALS``: number of evaluations (default 8, minimum 8)
- ``TANK_LIFECYCLE_SEED``: study seed (default 42)
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Generous per-evaluation stall bound: one evaluation takes ~8-20s depending
# on host, and the sibling in-process test already alerts at 40s, so anything
# past this is a hang rather than a slow machine.
_PER_EVAL_TIMEOUT_SECONDS = 150.0

_CHILD_SCRIPT = r"""
import faulthandler, gc, json, sys, time

faulthandler.enable()

from core.behavior.target_memory_transfer_evolution import evaluate_target_memory_transfer

n_evals = int(sys.argv[1])
seed = int(sys.argv[2])
per_eval_timeout = float(sys.argv[3])


def _current_rss_kb() -> int:
    try:
        import psutil
        return int(psutil.Process().memory_info().rss // 1024)
    except ImportError:
        pass
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        pass
    try:
        import resource
        # Fallback: peak RSS (monotonic, so growth checks stay valid but coarser).
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, NameError, OSError):
        return 0


for i in range(n_evals):
    faulthandler.dump_traceback_later(per_eval_timeout, exit=True)
    t0 = time.perf_counter()
    evaluate_target_memory_transfer(seed)
    wall = time.perf_counter() - t0
    faulthandler.cancel_dump_traceback_later()
    print(
        json.dumps(
            {
                "eval": i,
                "wall_seconds": round(wall, 3),
                "rss_kb": _current_rss_kb(),
                "gc_objects": len(gc.get_objects()),
            }
        ),
        flush=True,
    )
"""


@pytest.mark.slow
def test_repeated_evaluations_survive_a_full_study_in_a_fresh_interpreter(tmp_path):
    n_evals = max(8, int(os.environ.get("TANK_LIFECYCLE_EVALS", "8")))
    seed = int(os.environ.get("TANK_LIFECYCLE_SEED", "42"))

    script = tmp_path / "lifecycle_child.py"
    script.write_text(_CHILD_SCRIPT)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT)

    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(n_evals), str(seed), str(_PER_EVAL_TIMEOUT_SECONDS)],
            capture_output=True,
            text=True,
            timeout=n_evals * _PER_EVAL_TIMEOUT_SECONDS + 60.0,
            env=env,
            cwd=str(_REPO_ROOT),
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            "Child process exceeded the overall timeout without the per-eval "
            f"faulthandler firing.\nstdout:\n{exc.stdout}\nstderr:\n{exc.stderr}"
        )

    records = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]

    # A stall makes faulthandler dump the hung stack and kill the child, so
    # the missing-record failure below carries the stack trace in stderr.
    assert proc.returncode == 0 and len(records) == n_evals, (
        f"Only {len(records)}/{n_evals} evaluations completed "
        f"(exit code {proc.returncode}).\nRecords: {records}\nstderr:\n{proc.stderr}"
    )

    walls = [r["wall_seconds"] for r in records]
    baseline = statistics.median(walls[:3])
    for r in records:
        assert r["wall_seconds"] <= baseline * 2.0, (
            f"Evaluation {r['eval']} took {r['wall_seconds']}s, more than twice the "
            f"early-evaluation baseline of {baseline}s - progressive degradation.\n"
            f"All wall times: {walls}"
        )

    rss_growth_kb = records[-1]["rss_kb"] - records[0]["rss_kb"]
    assert rss_growth_kb < 128 * 1024, (
        f"RSS grew {rss_growth_kb / 1024:.1f} MB across {n_evals} evaluations.\n"
        f"Per-eval RSS (kB): {[r['rss_kb'] for r in records]}"
    )

    object_growth = records[-1]["gc_objects"] - records[0]["gc_objects"]
    assert object_growth < 50_000, (
        f"Live object count grew by {object_growth} across {n_evals} evaluations.\n"
        f"Per-eval counts: {[r['gc_objects'] for r in records]}"
    )
