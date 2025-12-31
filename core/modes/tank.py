"""Tank mode pack definition and config normalization."""

from __future__ import annotations

from typing import Any

from core.config.display import FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH
from core.config.ecosystem import CRITICAL_POPULATION_THRESHOLD, MAX_POPULATION
from core.config.food import AUTO_FOOD_ENABLED, AUTO_FOOD_SPAWN_RATE
from core.modes.interfaces import ModeConfig, ModePackDefinition

LEGACY_KEY_ALIASES = {
    "width": "screen_width",
    "height": "screen_height",
    "fps": "frame_rate",
}

TANK_MODE_DEFAULTS = {
    "screen_width": SCREEN_WIDTH,
    "screen_height": SCREEN_HEIGHT,
    "frame_rate": FRAME_RATE,
    "headless": True,
    "max_population": MAX_POPULATION,
    "critical_population_threshold": CRITICAL_POPULATION_THRESHOLD,
    "auto_food_spawn_rate": AUTO_FOOD_SPAWN_RATE,
    "auto_food_enabled": AUTO_FOOD_ENABLED,
}


def _normalize_tank_config(config: ModeConfig) -> ModeConfig:
    normalized: dict[str, Any] = dict(config)

    for legacy_key, canonical_key in LEGACY_KEY_ALIASES.items():
        if legacy_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(legacy_key)

    for key, default in TANK_MODE_DEFAULTS.items():
        normalized.setdefault(key, default)

    return normalized


def create_tank_mode_pack(
    *,
    snapshot_builder_factory: Any | None = None,
) -> ModePackDefinition:
    """Create the Tank mode pack with optional snapshot builder hook."""
    return ModePackDefinition(
        mode_id="tank",
        world_type="tank",
        default_view_mode="side",
        display_name="Fish Tank",
        snapshot_builder_factory=snapshot_builder_factory,
        normalizer=_normalize_tank_config,
    )
