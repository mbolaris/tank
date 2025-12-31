"""Soccer-specific observation and action interfaces.

This module defines the domain-agnostic interfaces for soccer agents that can work with:
1. Pure-python SoccerTrainingWorld for evolution/training
2. Future rcssserver adapter for evaluation (via UDP protocol)

The interfaces are designed to be high-level enough for policies to reason about,
while being translatable to low-level rcssserver commands (dash, turn, kick).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple


# Type aliases for clarity
Observation = Dict[str, Any]
TeamID = Literal["left", "right"]
PlayerID = str  # e.g., "left_1", "right_5"


@dataclass(frozen=True)
class Vector2D:
    """2D vector for positions, velocities, directions."""

    x: float
    y: float

    def magnitude(self) -> float:
        """Calculate the magnitude of the vector."""
        return (self.x**2 + self.y**2) ** 0.5

    def normalized(self) -> "Vector2D":
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
class SoccerObservation:
    """Complete observation for a soccer agent.

    This is what a policy sees when deciding what action to take.
    Designed to be translatable to/from rcssserver's visual/sensory info.

    Attributes:
        self_state: The observing player's own state
        ball: Ball state (may be estimated/noisy in rcssserver mode)
        teammates: List of visible teammate states
        opponents: List of visible opponent states
        game_time: Current game time in seconds
        play_mode: Current play mode (e.g., "play_on", "kick_off_left", "goal_left")
        field_bounds: (width, height) of the field in meters
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


@dataclass(frozen=True)
class SoccerAction:
    """High-level soccer action that can be translated to rcssserver commands.

    This represents the agent's intent, which will be translated to:
    - Training mode: Direct physics updates
    - rcssserver mode: (dash power angle), (turn angle), (kick power direction) commands

    Attributes:
        move_target: Target position to move towards (None = no movement intent)
        face_angle: Desired facing angle in radians (None = no turn intent)
        kick_power: Kick power [0.0, 1.0] (0 = no kick)
        kick_angle: Kick direction relative to facing angle in radians
    """

    move_target: Optional[Vector2D] = None
    face_angle: Optional[float] = None
    kick_power: float = 0.0
    kick_angle: float = 0.0

    def is_valid(self) -> bool:
        """Check if action parameters are within valid bounds."""
        if self.kick_power < 0.0 or self.kick_power > 1.0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "kick_power": self.kick_power,
            "kick_angle": self.kick_angle,
        }
        if self.move_target is not None:
            result["move_target"] = {"x": self.move_target.x, "y": self.move_target.y}
        if self.face_angle is not None:
            result["face_angle"] = self.face_angle
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoccerAction":
        """Create action from dictionary format."""
        move_target = None
        if "move_target" in data and data["move_target"] is not None:
            move_target = Vector2D(x=data["move_target"]["x"], y=data["move_target"]["y"])

        face_angle = data.get("face_angle")

        return cls(
            move_target=move_target,
            face_angle=face_angle,
            kick_power=data.get("kick_power", 0.0),
            kick_angle=data.get("kick_angle", 0.0),
        )


@dataclass
class SoccerReward:
    """Reward shaping components for soccer training.

    These are used in the training environment to provide learning signals.
    Not used in rcssserver evaluation mode.
    """

    goal_scored: float = 0.0
    goal_conceded: float = 0.0
    shot_on_goal: float = 0.0
    pass_completed: float = 0.0
    pass_failed: float = 0.0
    ball_possession: float = 0.0
    distance_to_ball_delta: float = 0.0  # Reward approaching ball
    spacing_quality: float = 0.0  # Reward good field positioning
    stamina_efficiency: float = 0.0  # Reward efficient movement

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
