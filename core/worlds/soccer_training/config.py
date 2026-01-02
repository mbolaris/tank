"""Configuration for the in-process soccer training world."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_FIELD_WIDTH = 105.0
DEFAULT_FIELD_HEIGHT = 68.0
DEFAULT_GOAL_WIDTH = 7.32

DEFAULT_TEAM_SIZE = 11
DEFAULT_FRAME_RATE = 30

DEFAULT_PLAYER_MAX_SPEED = 1.6
DEFAULT_PLAYER_ACCELERATION = 0.3
DEFAULT_PLAYER_TURN_RATE = 0.35
DEFAULT_PLAYER_FRICTION = 0.92
DEFAULT_PLAYER_RADIUS = 0.3

DEFAULT_BALL_FRICTION = 0.985
DEFAULT_BALL_RADIUS = 0.11
DEFAULT_BALL_KICK_POWER_MAX = 3.5
DEFAULT_KICK_RANGE = 0.8

DEFAULT_ENERGY_MAX = 100.0
DEFAULT_BASE_METABOLISM = 0.01
DEFAULT_DASH_ENERGY_COST = 0.2

DEFAULT_GOAL_REWARD = 20.0
DEFAULT_ASSIST_REWARD = 10.0
DEFAULT_POSSESSION_REWARD = 0.05
DEFAULT_POSSESSION_RADIUS = 1.2


@dataclass
class SoccerTrainingConfig:
    """Configuration for the soccer training world."""

    field_width: float = DEFAULT_FIELD_WIDTH
    field_height: float = DEFAULT_FIELD_HEIGHT
    goal_width: float = DEFAULT_GOAL_WIDTH

    team_size: int = DEFAULT_TEAM_SIZE
    frame_rate: int = DEFAULT_FRAME_RATE

    player_max_speed: float = DEFAULT_PLAYER_MAX_SPEED
    player_acceleration: float = DEFAULT_PLAYER_ACCELERATION
    player_turn_rate: float = DEFAULT_PLAYER_TURN_RATE
    player_friction: float = DEFAULT_PLAYER_FRICTION
    player_radius: float = DEFAULT_PLAYER_RADIUS

    ball_friction: float = DEFAULT_BALL_FRICTION
    ball_radius: float = DEFAULT_BALL_RADIUS
    ball_kick_power_max: float = DEFAULT_BALL_KICK_POWER_MAX
    kick_range: float = DEFAULT_KICK_RANGE

    energy_max: float = DEFAULT_ENERGY_MAX
    base_metabolism: float = DEFAULT_BASE_METABOLISM
    dash_energy_cost: float = DEFAULT_DASH_ENERGY_COST

    goal_reward: float = DEFAULT_GOAL_REWARD
    assist_reward: float = DEFAULT_ASSIST_REWARD
    possession_reward: float = DEFAULT_POSSESSION_REWARD
    possession_radius: float = DEFAULT_POSSESSION_RADIUS

    headless: bool = True

    @property
    def physics_timestep(self) -> float:
        """Compute physics timestep from frame rate."""
        return 1.0 / self.frame_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_width": self.field_width,
            "field_height": self.field_height,
            "goal_width": self.goal_width,
            "team_size": self.team_size,
            "frame_rate": self.frame_rate,
            "player_max_speed": self.player_max_speed,
            "player_acceleration": self.player_acceleration,
            "player_turn_rate": self.player_turn_rate,
            "player_friction": self.player_friction,
            "player_radius": self.player_radius,
            "ball_friction": self.ball_friction,
            "ball_radius": self.ball_radius,
            "ball_kick_power_max": self.ball_kick_power_max,
            "kick_range": self.kick_range,
            "energy_max": self.energy_max,
            "base_metabolism": self.base_metabolism,
            "dash_energy_cost": self.dash_energy_cost,
            "goal_reward": self.goal_reward,
            "assist_reward": self.assist_reward,
            "possession_reward": self.possession_reward,
            "possession_radius": self.possession_radius,
            "headless": self.headless,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoccerTrainingConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> None:
        if self.team_size < 1 or self.team_size > 11:
            raise ValueError(f"team_size must be 1-11, got {self.team_size}")
        if self.field_width <= 0 or self.field_height <= 0:
            raise ValueError("Field dimensions must be positive")
        if self.goal_width <= 0 or self.goal_width > self.field_height:
            raise ValueError("goal_width must be positive and within field height")
        if not 0.0 <= self.ball_friction <= 1.0:
            raise ValueError("ball_friction must be in [0, 1]")
        if not 0.0 <= self.player_friction <= 1.0:
            raise ValueError("player_friction must be in [0, 1]")
        if self.player_max_speed <= 0:
            raise ValueError("player_max_speed must be positive")
        if self.player_acceleration <= 0:
            raise ValueError("player_acceleration must be positive")
        if self.player_turn_rate <= 0:
            raise ValueError("player_turn_rate must be positive")
        if self.energy_max <= 0:
            raise ValueError("energy_max must be positive")
        if self.base_metabolism < 0:
            raise ValueError("base_metabolism must be non-negative")
        if self.dash_energy_cost < 0:
            raise ValueError("dash_energy_cost must be non-negative")
        if self.possession_radius <= 0:
            raise ValueError("possession_radius must be positive")
