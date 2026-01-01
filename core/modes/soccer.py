"""Soccer mode pack definition and config normalization."""

from __future__ import annotations

from typing import Any

from core.modes.interfaces import ModeConfig, ModePackDefinition
from core.worlds.soccer.config import (
    DEFAULT_BALL_FRICTION,
    DEFAULT_BALL_KICK_POWER_MAX,
    DEFAULT_BALL_RADIUS,
    DEFAULT_FIELD_HEIGHT,
    DEFAULT_FIELD_WIDTH,
    DEFAULT_FRAME_RATE,
    DEFAULT_GOAL_REWARD,
    DEFAULT_HALF_TIME_DURATION,
    DEFAULT_PASS_REWARD,
    DEFAULT_PLAYER_ACCELERATION,
    DEFAULT_PLAYER_MAX_SPEED,
    DEFAULT_PLAYER_RADIUS,
    DEFAULT_POSSESSION_REWARD,
    DEFAULT_SHOT_REWARD,
    DEFAULT_SPACING_REWARD,
    DEFAULT_STAMINA_KICK_COST,
    DEFAULT_STAMINA_MAX,
    DEFAULT_STAMINA_RECOVERY_RATE,
    DEFAULT_STAMINA_SPRINT_COST,
    DEFAULT_TEAM_SIZE,
)

# Legacy key aliases for backwards compatibility
LEGACY_KEY_ALIASES = {
    "width": "field_width",
    "height": "field_height",
    "fps": "frame_rate",
    "players_per_team": "team_size",
}

# Default configuration values
SOCCER_MODE_DEFAULTS = {
    # Field dimensions
    "field_width": DEFAULT_FIELD_WIDTH,
    "field_height": DEFAULT_FIELD_HEIGHT,
    # Team configuration
    "team_size": DEFAULT_TEAM_SIZE,
    "half_time_duration": DEFAULT_HALF_TIME_DURATION,
    "frame_rate": DEFAULT_FRAME_RATE,
    # Physics parameters
    "ball_friction": DEFAULT_BALL_FRICTION,
    "player_max_speed": DEFAULT_PLAYER_MAX_SPEED,
    "player_acceleration": DEFAULT_PLAYER_ACCELERATION,
    "ball_kick_power_max": DEFAULT_BALL_KICK_POWER_MAX,
    "ball_radius": DEFAULT_BALL_RADIUS,
    "player_radius": DEFAULT_PLAYER_RADIUS,
    # Energy/stamina
    "stamina_max": DEFAULT_STAMINA_MAX,
    "stamina_recovery_rate": DEFAULT_STAMINA_RECOVERY_RATE,
    "stamina_sprint_cost": DEFAULT_STAMINA_SPRINT_COST,
    "stamina_kick_cost": DEFAULT_STAMINA_KICK_COST,
    # Reward shaping
    "goal_reward": DEFAULT_GOAL_REWARD,
    "shot_reward": DEFAULT_SHOT_REWARD,
    "pass_reward": DEFAULT_PASS_REWARD,
    "possession_reward": DEFAULT_POSSESSION_REWARD,
    "spacing_reward": DEFAULT_SPACING_REWARD,
    # Simulation control
    "headless": True,
}


def _normalize_soccer_config(config: ModeConfig) -> ModeConfig:
    """Normalize soccer config by handling legacy keys and applying defaults.

    Args:
        config: Raw configuration dict

    Returns:
        Normalized configuration with all defaults applied
    """
    normalized: dict[str, Any] = dict(config)

    # Handle legacy key aliases
    for legacy_key, canonical_key in LEGACY_KEY_ALIASES.items():
        if legacy_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(legacy_key)

    # Apply defaults for missing keys
    for key, default in SOCCER_MODE_DEFAULTS.items():
        normalized.setdefault(key, default)

    return normalized


def create_soccer_mode_pack(
    *,
    snapshot_builder_factory: Any | None = None,
) -> ModePackDefinition:
    """Create the Soccer mode pack with optional snapshot builder hook.

    Args:
        snapshot_builder_factory: Optional factory for custom snapshot building

    Returns:
        ModePackDefinition for soccer mode
    """
    return ModePackDefinition(
        mode_id="soccer",
        world_type="soccer",
        default_view_mode="topdown",
        display_name="Soccer Pitch",
        supports_persistence=False,  # Soccer matches are ephemeral
        supports_actions=True,       # Requires agent actions each step
        supports_websocket=True,
        supports_transfer=False,     # No entity transfer between soccer worlds
        snapshot_builder_factory=snapshot_builder_factory,
        normalizer=_normalize_soccer_config,
    )
