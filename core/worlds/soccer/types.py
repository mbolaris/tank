# ruff: noqa: UP006
"""Canonical soccer types for all soccer-related modules.

This module contains the unified action/observation contract used by:
- core/worlds/soccer/backend.py (pure-python training)
- core/worlds/soccer/rcssserver_adapter.py (RCSS evaluation)
- core/worlds/soccer_training (GenomeCodePool training)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple

# Type aliases
TeamID = Literal["left", "right"]
PlayerID = str  # e.g., "left_1", "right_5"
Observation = Dict[str, Any]


@dataclass(frozen=True)
class Vector2D:
    """2D vector for positions, velocities, directions."""

    x: float
    y: float

    def magnitude(self) -> float:
        """Calculate the magnitude of the vector."""
        return (self.x**2 + self.y**2) ** 0.5

    def normalized(self) -> Vector2D:
        """Return a unit vector in the same direction."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0.0, 0.0)
        return Vector2D(self.x / mag, self.y / mag)


@dataclass(frozen=True)
class PlayerState:
    """State information for a single player."""

    player_id: PlayerID
    team: TeamID
    position: Vector2D
    velocity: Vector2D
    stamina: float  # [0.0, 1.0] normalized
    facing_angle: float  # radians, 0 = facing right (+x)


@dataclass(frozen=True)
class BallState:
    """State information for the ball."""

    position: Vector2D
    velocity: Vector2D


@dataclass(frozen=True)
class SoccerAction:
    """Normalized soccer action for policies.

    This is the canonical action format used across all soccer backends.
    Maps cleanly to RCSS server commands (dash, turn, kick).

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
    def from_dict(cls, data: Dict[str, Any]) -> SoccerAction:
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


@dataclass(frozen=True)
class SoccerObservation:
    """Complete observation for a soccer agent.

    Designed to be translatable to/from rcssserver's visual/sensory info.
    """

    self_state: PlayerState
    ball: BallState
    teammates: List[PlayerState]
    opponents: List[PlayerState]
    game_time: float
    play_mode: str
    field_bounds: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for policy input."""
        return {
            "position": {"x": self.self_state.position.x, "y": self.self_state.position.y},
            "velocity": {"x": self.self_state.velocity.x, "y": self.self_state.velocity.y},
            "stamina": self.self_state.stamina,
            "facing_angle": self.self_state.facing_angle,
            "ball_position": {"x": self.ball.position.x, "y": self.ball.position.y},
            "ball_velocity": {"x": self.ball.velocity.x, "y": self.ball.velocity.y},
            "teammates": [
                {
                    "id": tm.player_id,
                    "position": {"x": tm.position.x, "y": tm.position.y},
                    "velocity": {"x": tm.velocity.x, "y": tm.velocity.y},
                    "stamina": tm.stamina,
                }
                for tm in self.teammates
            ],
            "opponents": [
                {
                    "id": opp.player_id,
                    "position": {"x": opp.position.x, "y": opp.position.y},
                    "velocity": {"x": opp.velocity.x, "y": opp.velocity.y},
                    "stamina": opp.stamina,
                }
                for opp in self.opponents
            ],
            "game_time": self.game_time,
            "play_mode": self.play_mode,
            "field_width": self.field_bounds[0],
            "field_height": self.field_bounds[1],
        }


@dataclass
class SoccerReward:
    """Reward shaping components for soccer training."""

    goal_scored: float = 0.0
    goal_conceded: float = 0.0
    shot_on_goal: float = 0.0
    pass_completed: float = 0.0
    pass_failed: float = 0.0
    ball_possession: float = 0.0
    distance_to_ball_delta: float = 0.0
    spacing_quality: float = 0.0
    stamina_efficiency: float = 0.0

    def total(self) -> float:
        """Calculate total reward."""
        return (
            self.goal_scored
            + self.goal_conceded
            + self.shot_on_goal
            + self.pass_completed
            + self.pass_failed
            + self.ball_possession
            + self.distance_to_ball_delta
            + self.spacing_quality
            + self.stamina_efficiency
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for logging/metrics."""
        return {
            "goal_scored": self.goal_scored,
            "goal_conceded": self.goal_conceded,
            "shot_on_goal": self.shot_on_goal,
            "pass_completed": self.pass_completed,
            "pass_failed": self.pass_failed,
            "ball_possession": self.ball_possession,
            "distance_to_ball_delta": self.distance_to_ball_delta,
            "spacing_quality": self.spacing_quality,
            "stamina_efficiency": self.stamina_efficiency,
            "total": self.total(),
        }
