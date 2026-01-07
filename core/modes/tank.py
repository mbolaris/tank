"""Tank mode pack definition and config normalization."""

from __future__ import annotations

from typing import Any

from core.config.display import FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH
from core.config.ecosystem import CRITICAL_POPULATION_THRESHOLD, MAX_POPULATION
from core.config.food import AUTO_FOOD_ENABLED, AUTO_FOOD_SPAWN_RATE
from core.modes.interfaces import ModeConfig, ModePackDefinition

TANK_MODE_DEFAULTS = {
    "screen_width": SCREEN_WIDTH,
    "screen_height": SCREEN_HEIGHT,
    "frame_rate": FRAME_RATE,
    "max_population": MAX_POPULATION,
    "critical_population_threshold": CRITICAL_POPULATION_THRESHOLD,
    "auto_food_enabled": AUTO_FOOD_ENABLED,
    "auto_food_spawn_rate": AUTO_FOOD_SPAWN_RATE,
}


def normalize_tank_config(config: ModeConfig) -> ModeConfig:
    normalized: dict[str, Any] = dict(config)

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
        supports_persistence=True,
        supports_actions=False,
        supports_websocket=True,
        supports_transfer=True,  # Tank supports fish transfer between tanks
        has_fish=True,
        snapshot_builder_factory=snapshot_builder_factory,
        normalizer=normalize_tank_config,
    )
