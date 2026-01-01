"""Action/observation interfaces for the soccer training world."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SoccerAction:
    """Action command for soccer training policies.

    Attributes:
        turn: Normalized turn command in [-1, 1] (scaled by turn rate).
        dash: Normalized dash command in [-1, 1] (scaled by acceleration).
        kick_power: Kick power in [0, 1], 0 means no kick.
        kick_angle: Kick direction offset in radians (relative to facing).
    """

    turn: float = 0.0
    dash: float = 0.0
    kick_power: float = 0.0
    kick_angle: float = 0.0

    def is_valid(self) -> bool:
        if self.kick_power < 0.0 or self.kick_power > 1.0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "dash": self.dash,
            "kick_power": self.kick_power,
            "kick_angle": self.kick_angle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoccerAction":
        def _to_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        return cls(
            turn=_to_float(data.get("turn", 0.0)),
            dash=_to_float(data.get("dash", 0.0)),
            kick_power=_to_float(data.get("kick_power", 0.0)),
            kick_angle=_to_float(data.get("kick_angle", 0.0)),
        )
