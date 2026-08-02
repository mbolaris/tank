"""One-way production adapters into canonical soccer space."""

from core.minigames.soccer.adapters.tank_adapter import (
    TankMatchAdapter,
    adapt_engine_ball,
    adapt_engine_player,
    adapt_engine_state,
    tank_to_canonical,
)

__all__ = [
    "TankMatchAdapter",
    "adapt_engine_ball",
    "adapt_engine_player",
    "adapt_engine_state",
    "tank_to_canonical",
]
