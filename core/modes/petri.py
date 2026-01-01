"""Petri dish mode pack definition and config normalization."""

from __future__ import annotations

from typing import Any

from core.modes.interfaces import ModePackDefinition
from core.modes.tank import normalize_tank_config


def create_petri_mode_pack(
    *,
    snapshot_builder_factory: Any | None = None,
) -> ModePackDefinition:
    """Create the Petri Dish mode pack.

    Petri mode reuses the Tank simulation defaults while presenting a top-down view.
    """
    return ModePackDefinition(
        mode_id="petri",
        world_type="petri",
        default_view_mode="topdown",
        display_name="Petri Dish",
        supports_persistence=True,
        supports_actions=False,
        supports_websocket=True,
        supports_transfer=True,  # Petri also supports entity transfer
        snapshot_builder_factory=snapshot_builder_factory,
        normalizer=normalize_tank_config,
    )
