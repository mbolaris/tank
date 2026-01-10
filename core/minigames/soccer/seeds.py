"""Deterministic seed derivation utilities for soccer scheduling."""

from __future__ import annotations

import hashlib
from typing import Any


def stable_seed_from_parts(*parts: Any) -> int:
    """Build a stable 32-bit seed from arbitrary parts."""
    seed_material = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little") & 0xFFFFFFFF


def derive_soccer_seed(seed_base: int | None, match_counter: int, salt: str) -> int | None:
    """Derive deterministic seeds for soccer scheduling."""
    if seed_base is None:
        return None
    return stable_seed_from_parts(seed_base, match_counter, salt)
