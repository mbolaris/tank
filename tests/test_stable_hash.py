"""Determinism tests for stable_algorithm_id.

Guards against regressing to the builtin ``hash()``, which is randomized per
process (PYTHONHASHSEED) and silently broke cross-process reproducibility of
the ecosystem_health benchmark. See ADR-014.
"""

from __future__ import annotations

import subprocess
import sys

from core.util.stable_hash import stable_algorithm_id


def test_known_values_are_pinned():
    """Exact CRC32 values - process-independent, so safe to hardcode."""
    assert stable_algorithm_id("food_seeker") == 3279151184
    assert stable_algorithm_id("panic_flee-direct_pursuit-solo-passive") == 2736156406
    assert stable_algorithm_id("") == 0


def test_deterministic_within_process():
    name = "ambush_feeder-spiral_forager-school-aggressive"
    assert stable_algorithm_id(name) == stable_algorithm_id(name)


def test_stable_across_processes():
    """The whole point: identical value in a separate interpreter process.

    A builtin ``hash(str)`` would (almost always) differ here.
    """
    code = "from core.util.stable_hash import stable_algorithm_id; print(stable_algorithm_id('food_seeker'))"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(3)
    }
    assert outputs == {"3279151184"}, outputs
