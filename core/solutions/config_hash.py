"""Stable configuration hashing for benchmark results and champion records.

A champion score is only meaningful against the configuration it was recorded
with. Changing core config (energy costs, spawn rates, population caps)
silently invalidates every champion unless something notices. This module
computes a stable hash of the *effective* configuration of a benchmark run:

    config_hash = sha256(seed, benchmark_id, benchmark CONFIG, core config)

``tools/run_bench.py`` stamps the hash into every result, and
``tools/validate_improvement.py`` refuses to compare scores across mismatched
hashes ("config changed - re-baseline") instead of emitting a misleading
better/worse verdict.

See docs/IMPROVEMENT_PROPOSALS.md section 1.1.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from types import ModuleType
from typing import Any

# core.config modules whose constants affect simulation outcomes.
# display and server are intentionally excluded: they only affect rendering
# and transport, so changing them must not invalidate champions.
SIM_CONFIG_MODULES: tuple[str, ...] = (
    "ecosystem",
    "entities",
    "fish",
    "food",
    "plants",
    "poker",
    "simulation",
    "soccer",
)


def _snapshot_module(module: ModuleType) -> dict[str, Any]:
    """Collect the UPPER_CASE constants of a config module into a plain dict."""
    snapshot: dict[str, Any] = {}
    for name in dir(module):
        if name.startswith("_") or not name.isupper():
            continue
        value = getattr(module, name)
        if isinstance(value, (bool, int, float, str, type(None))):
            snapshot[name] = value
        elif isinstance(value, (list, tuple, set, frozenset)):
            snapshot[name] = sorted(repr(v) for v in value)
        elif isinstance(value, dict):
            snapshot[name] = {
                str(k): repr(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
            }
        # Callables, modules, and classes are not configuration values.
    return snapshot


def core_config_snapshot() -> dict[str, dict[str, Any]]:
    """Snapshot every simulation-relevant core.config module."""
    return {
        name: _snapshot_module(importlib.import_module(f"core.config.{name}"))
        for name in SIM_CONFIG_MODULES
    }


def compute_config_hash(
    benchmark_id: str,
    seed: int,
    benchmark_config: dict[str, Any] | None = None,
) -> str:
    """Compute the stable config hash for a benchmark run.

    Args:
        benchmark_id: e.g. "tank/survival_5k"
        seed: the seed the benchmark was run with (scores from different
            seeds are never comparable)
        benchmark_config: the benchmark module's CONFIG dict, if it has one

    Returns:
        A 16-hex-char digest, stable across processes and platforms.
    """
    payload = {
        "benchmark_id": benchmark_id,
        "seed": seed,
        "benchmark_config": benchmark_config or {},
        "core_config": core_config_snapshot(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
