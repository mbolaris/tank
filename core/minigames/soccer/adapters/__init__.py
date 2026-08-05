"""One-way production adapters into canonical soccer space."""

from core.minigames.soccer.adapters.rcss_monitor_adapter import (
    RcssMonitorAdapter,
    RcssMonitorParseError,
    parse_show_frame,
    rcss_participants,
    rcss_show_to_canonical,
)
from core.minigames.soccer.adapters.tank_adapter import (
    TankMatchAdapter,
    adapt_engine_ball,
    adapt_engine_player,
    adapt_engine_state,
    tank_to_canonical,
)

__all__ = [
    "RcssMonitorAdapter",
    "RcssMonitorParseError",
    "TankMatchAdapter",
    "adapt_engine_ball",
    "adapt_engine_player",
    "adapt_engine_state",
    "parse_show_frame",
    "rcss_participants",
    "rcss_show_to_canonical",
    "tank_to_canonical",
]
