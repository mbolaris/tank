"""Deterministic, cross-process-stable hashing for telemetry / diversity IDs.

Python's builtin ``hash()`` is randomized per process for ``str`` / ``bytes``
inputs unless ``PYTHONHASHSEED`` is pinned, so ``hash(some_string) % N`` returns
different values in different processes. Anything derived from it is therefore
not reproducible across runs - in this codebase that made the ecosystem_health
benchmark's diversity metric (and thus its score) non-reproducible across
processes, violating the determinism guarantee (see ADR-012, ADR-014).

Use :func:`stable_algorithm_id` whenever a string (e.g. a composable
``behavior_id`` or a strategy class name) must become a stable integer id.
"""

from __future__ import annotations

import zlib


def stable_algorithm_id(name: str) -> int:
    """Return a deterministic, process-independent integer id for ``name``.

    Unlike the builtin :func:`hash`, the result is identical across processes
    and Python invocations. CRC32 yields a 32-bit value with negligible
    collision probability at this codebase's scale (tens to low hundreds of
    distinct behaviors), so - unlike the previous ``hash(name) % 1000`` - it
    does not silently merge distinct algorithms into the same bucket.
    """
    return zlib.crc32(name.encode("utf-8"))
