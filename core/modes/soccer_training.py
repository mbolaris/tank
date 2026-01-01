"""Soccer training mode pack definition and config normalization."""

from __future__ import annotations

from typing import Any

from core.modes.interfaces import ModeConfig, ModePackDefinition
from core.worlds.soccer_training.config import (
    DEFAULT_ASSIST_REWARD,
    DEFAULT_BALL_FRICTION,
    DEFAULT_BALL_KICK_POWER_MAX,
    DEFAULT_BALL_RADIUS,
    DEFAULT_BASE_METABOLISM,
    DEFAULT_DASH_ENERGY_COST,
    DEFAULT_ENERGY_MAX,
    DEFAULT_FIELD_HEIGHT,
    DEFAULT_FIELD_WIDTH,
    DEFAULT_FRAME_RATE,
    DEFAULT_GOAL_REWARD,
    DEFAULT_GOAL_WIDTH,
    DEFAULT_KICK_RANGE,
    DEFAULT_PLAYER_ACCELERATION,
    DEFAULT_PLAYER_FRICTION,
    DEFAULT_PLAYER_MAX_SPEED,
    DEFAULT_PLAYER_RADIUS,
    DEFAULT_PLAYER_TURN_RATE,
    DEFAULT_POSSESSION_RADIUS,
    DEFAULT_POSSESSION_REWARD,
    DEFAULT_TEAM_SIZE,
)

LEGACY_KEY_ALIASES = {
    "width": "field_width",
    "height": "field_height",
    "fps": "frame_rate",
    "players_per_team": "team_size",
}

SOCCER_TRAINING_DEFAULTS = {
    "field_width": DEFAULT_FIELD_WIDTH,
    "field_height": DEFAULT_FIELD_HEIGHT,
    "goal_width": DEFAULT_GOAL_WIDTH,
    "team_size": DEFAULT_TEAM_SIZE,
    "frame_rate": DEFAULT_FRAME_RATE,
    "player_max_speed": DEFAULT_PLAYER_MAX_SPEED,
    "player_acceleration": DEFAULT_PLAYER_ACCELERATION,
    "player_turn_rate": DEFAULT_PLAYER_TURN_RATE,
    "player_friction": DEFAULT_PLAYER_FRICTION,
    "player_radius": DEFAULT_PLAYER_RADIUS,
    "ball_friction": DEFAULT_BALL_FRICTION,
    "ball_radius": DEFAULT_BALL_RADIUS,
    "ball_kick_power_max": DEFAULT_BALL_KICK_POWER_MAX,
    "kick_range": DEFAULT_KICK_RANGE,
    "energy_max": DEFAULT_ENERGY_MAX,
    "base_metabolism": DEFAULT_BASE_METABOLISM,
    "dash_energy_cost": DEFAULT_DASH_ENERGY_COST,
    "goal_reward": DEFAULT_GOAL_REWARD,
    "assist_reward": DEFAULT_ASSIST_REWARD,
    "possession_reward": DEFAULT_POSSESSION_REWARD,
    "possession_radius": DEFAULT_POSSESSION_RADIUS,
    "headless": True,
}


def _normalize_soccer_training_config(config: ModeConfig) -> ModeConfig:
    normalized: dict[str, Any] = dict(config)

    for legacy_key, canonical_key in LEGACY_KEY_ALIASES.items():
        if legacy_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(legacy_key)

    for key, default in SOCCER_TRAINING_DEFAULTS.items():
        normalized.setdefault(key, default)

    return normalized


def create_soccer_training_mode_pack(
    *,
    snapshot_builder_factory: Any | None = None,
) -> ModePackDefinition:
    return ModePackDefinition(
        mode_id="soccer_training",
        world_type="soccer_training",
        default_view_mode="topdown",
        display_name="Soccer Training",
        supports_persistence=False,  # Training sessions are ephemeral
        supports_actions=True,       # Requires agent actions
        supports_websocket=True,
        supports_transfer=False,
        snapshot_builder_factory=snapshot_builder_factory,
        normalizer=_normalize_soccer_training_config,
    )
