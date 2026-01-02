"""Soccer world configuration.

This module defines the configuration for the soccer training environment.
Configuration is independent of whether training locally or evaluating with rcssserver.
"""

from dataclasses import dataclass
from typing import Any, Dict

# Default soccer field dimensions (RoboCup standard is 105m x 68m, scaled down)
DEFAULT_FIELD_WIDTH = 105.0  # meters
DEFAULT_FIELD_HEIGHT = 68.0  # meters

# Default team sizes (supports 11v11 but can use smaller for faster training)
DEFAULT_TEAM_SIZE = 11
DEFAULT_HALF_TIME_DURATION = 3000  # frames (50 seconds at 60 fps)
DEFAULT_FRAME_RATE = 60  # Hz

# Physics parameters
DEFAULT_BALL_FRICTION = 0.98  # Ball velocity decay per frame
DEFAULT_PLAYER_MAX_SPEED = 1.2  # m/s
DEFAULT_PLAYER_ACCELERATION = 0.3  # m/s^2
DEFAULT_BALL_KICK_POWER_MAX = 3.0  # m/s max ball velocity from kick
DEFAULT_BALL_RADIUS = 0.085  # meters (official soccer ball radius)
DEFAULT_PLAYER_RADIUS = 0.3  # meters (collision radius)

# Energy/stamina parameters
DEFAULT_STAMINA_MAX = 100.0
DEFAULT_STAMINA_RECOVERY_RATE = 0.05  # per frame when not sprinting
DEFAULT_STAMINA_SPRINT_COST = 0.2  # per frame when sprinting
DEFAULT_STAMINA_KICK_COST = 2.0  # per kick action

# Reward shaping weights
DEFAULT_GOAL_REWARD = 100.0
DEFAULT_SHOT_REWARD = 5.0
DEFAULT_PASS_REWARD = 2.0
DEFAULT_POSSESSION_REWARD = 0.1  # per frame
DEFAULT_SPACING_REWARD = 0.05  # per frame for good positioning


@dataclass
class SoccerWorldConfig:
    """Configuration for SoccerTrainingWorld.

    All parameters have sensible defaults but can be overridden for experimentation.
    This config works for both training mode and (future) rcssserver evaluation.
    """

    # Field dimensions
    field_width: float = DEFAULT_FIELD_WIDTH
    field_height: float = DEFAULT_FIELD_HEIGHT

    # Team configuration
    team_size: int = DEFAULT_TEAM_SIZE  # Players per team (1-11)
    half_time_duration: int = DEFAULT_HALF_TIME_DURATION
    frame_rate: int = DEFAULT_FRAME_RATE

    # Physics parameters
    ball_friction: float = DEFAULT_BALL_FRICTION
    player_max_speed: float = DEFAULT_PLAYER_MAX_SPEED
    player_acceleration: float = DEFAULT_PLAYER_ACCELERATION
    ball_kick_power_max: float = DEFAULT_BALL_KICK_POWER_MAX
    ball_radius: float = DEFAULT_BALL_RADIUS
    player_radius: float = DEFAULT_PLAYER_RADIUS

    # Energy/stamina
    stamina_max: float = DEFAULT_STAMINA_MAX
    stamina_recovery_rate: float = DEFAULT_STAMINA_RECOVERY_RATE
    stamina_sprint_cost: float = DEFAULT_STAMINA_SPRINT_COST
    stamina_kick_cost: float = DEFAULT_STAMINA_KICK_COST

    # Reward shaping (only used in training mode)
    goal_reward: float = DEFAULT_GOAL_REWARD
    shot_reward: float = DEFAULT_SHOT_REWARD
    pass_reward: float = DEFAULT_PASS_REWARD
    possession_reward: float = DEFAULT_POSSESSION_REWARD
    spacing_reward: float = DEFAULT_SPACING_REWARD

    # Simulation control
    headless: bool = True  # Run without rendering

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "field_width": self.field_width,
            "field_height": self.field_height,
            "team_size": self.team_size,
            "half_time_duration": self.half_time_duration,
            "frame_rate": self.frame_rate,
            "ball_friction": self.ball_friction,
            "player_max_speed": self.player_max_speed,
            "player_acceleration": self.player_acceleration,
            "ball_kick_power_max": self.ball_kick_power_max,
            "ball_radius": self.ball_radius,
            "player_radius": self.player_radius,
            "stamina_max": self.stamina_max,
            "stamina_recovery_rate": self.stamina_recovery_rate,
            "stamina_sprint_cost": self.stamina_sprint_cost,
            "stamina_kick_cost": self.stamina_kick_cost,
            "goal_reward": self.goal_reward,
            "shot_reward": self.shot_reward,
            "pass_reward": self.pass_reward,
            "possession_reward": self.possession_reward,
            "spacing_reward": self.spacing_reward,
            "headless": self.headless,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoccerWorldConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> None:
        """Validate configuration parameters.

        Raises:
            ValueError: If any parameters are invalid
        """
        if self.team_size < 1 or self.team_size > 11:
            raise ValueError(f"team_size must be 1-11, got {self.team_size}")

        if self.field_width <= 0 or self.field_height <= 0:
            raise ValueError("Field dimensions must be positive")

        if self.ball_friction < 0 or self.ball_friction > 1:
            raise ValueError("ball_friction must be in [0, 1]")

        if self.player_max_speed <= 0:
            raise ValueError("player_max_speed must be positive")
