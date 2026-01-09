"""Config normalization utilities for world types.

This module provides a single entry point for config normalization,
used by CLI, tests, and backend to ensure consistent config handling.
"""

from __future__ import annotations

from typing import Any

from core.worlds.registry import WorldRegistry


def normalize_config(mode_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize configuration for a world type.

    This is the canonical entry point for config normalization across CLI,
    tests, and backend. It looks up the mode pack and calls its configure()
    method to normalize legacy keys and fill in defaults.

    Args:
        mode_id: The mode identifier (e.g., "tank", "petri")
        config: Optional raw config dict to normalize

    Returns:
        Normalized config dict with defaults applied

    Raises:
        ValueError: If mode_id is not registered
    """
    mode_pack = WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        available = list(WorldRegistry.list_mode_packs().keys())
        raise ValueError(f"Unknown mode '{mode_id}'. Available modes: {available}")

    return mode_pack.configure(config or {})
