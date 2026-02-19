"""RCSS-compatible physics parameters.

This module defines physics parameters that match the RoboCup Soccer Simulator
(rcssserver) defaults. These enable training that transfers to the real server.

Reference: https://rcsoccersim.readthedocs.io/en/latest/soccerserver.html
"""

from dataclasses import dataclass


@dataclass
class RCSSParams:
    """RCSS-compatible physics parameters.

    All defaults match rcssserver 18.x unless noted. The simulation uses
    cycle-based timing (100ms per cycle = 10 Hz) rather than frame-based.

    Reference: https://rcsoccersim.readthedocs.io/en/latest/soccerserver.html
    """

    # =========================================================================
    # Timing
    # =========================================================================
    cycle_ms: int = 100  # 100ms per cycle (10 Hz)

    # =========================================================================
    # Movement decay (applied each cycle after velocity update)
    # =========================================================================
    player_decay: float = 0.4  # server default: player_decay
    ball_decay: float = 0.94  # server default: ball_decay

    # =========================================================================
    # Dash mechanics
    # =========================================================================
    dash_power_rate: float = 0.006  # acceleration = power * rate
    player_speed_max: float = 1.05  # max speed per cycle
    stamina_max: float = 8000.0  # max stamina
    stamina_inc_max: float = 45.0  # recovery per cycle when not dashing
    dash_consume_rate: float = 1.0  # stamina consumed per dash power

    # Recovery/Effort mechanics (RCSS standard)
    recover_dec: float = 0.002
    recover_min: float = 0.5
    effort_dec: float = 0.005
    effort_min: float = 0.6
    effort_inc: float = 0.01

    # =========================================================================
    # Kick mechanics
    # =========================================================================
    kick_power_rate: float = 0.027  # ball speed = power * rate
    kickable_margin: float = 0.7  # ball within this radius is kickable
    kick_rand: float = 0.1  # kick direction noise (radians)
    ball_speed_max: float = 3.0  # max ball speed per cycle

    # =========================================================================
    # Turn mechanics
    # =========================================================================
    inertia_moment: float = 5.0  # turn rate affected by speed
    max_moment: float = 180.0  # max turn angle (degrees)
    min_moment: float = -180.0  # min turn angle (degrees)
    max_neck_angle: float = 90.0  # max neck angle relative to body (degrees)
    min_neck_angle: float = -90.0  # min neck angle relative to body (degrees)

    # =========================================================================
    # Field dimensions (standard RoboCup)
    # =========================================================================
    field_length: float = 105.0  # x-axis (horizontal)
    field_width: float = 68.0  # y-axis (vertical)
    goal_width: float = 14.02  # goal mouth width
    goal_depth: float = 2.44  # goal depth behind goal line

    # =========================================================================
    # Player/Ball geometry
    # =========================================================================
    player_size: float = 0.3  # collision radius
    ball_size: float = 0.085  # ball radius

    # =========================================================================
    # Noise parameters
    # =========================================================================
    player_rand: float = 0.1  # movement noise factor

    # =========================================================================
    # Noise (optional, disabled by default for deterministic training)
    # =========================================================================
    noise_enabled: bool = False
    noise_seed: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "cycle_ms": self.cycle_ms,
            "player_decay": self.player_decay,
            "ball_decay": self.ball_decay,
            "dash_power_rate": self.dash_power_rate,
            "player_speed_max": self.player_speed_max,
            "stamina_max": self.stamina_max,
            "stamina_inc_max": self.stamina_inc_max,
            "dash_consume_rate": self.dash_consume_rate,
            "recover_dec": self.recover_dec,
            "recover_min": self.recover_min,
            "effort_dec": self.effort_dec,
            "effort_min": self.effort_min,
            "effort_inc": self.effort_inc,
            "kick_power_rate": self.kick_power_rate,
            "kickable_margin": self.kickable_margin,
            "kick_rand": self.kick_rand,
            "ball_speed_max": self.ball_speed_max,
            "inertia_moment": self.inertia_moment,
            "max_moment": self.max_moment,
            "min_moment": self.min_moment,
            "field_length": self.field_length,
            "field_width": self.field_width,
            "goal_width": self.goal_width,
            "goal_depth": self.goal_depth,
            "player_size": self.player_size,
            "ball_size": self.ball_size,
            "noise_enabled": self.noise_enabled,
            "noise_seed": self.noise_seed,
            "player_rand": self.player_rand,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RCSSParams":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Default parameters for training (noise disabled)
DEFAULT_RCSS_PARAMS = RCSSParams()

# Small field preset for faster training (100x60 instead of RCSS standard 105x68)
# Used by default in SoccerMatch and SoccerMatchRunner for compatibility with
# existing champions and faster episode evaluation
SMALL_FIELD_PARAMS = RCSSParams(
    field_length=100.0,
    field_width=60.0,
)

# Canonical evaluation params for soccer (Match / Runner / QuickEval defaults).
# Keep this as a single source of truth to avoid evaluation drift across harnesses.
SOCCER_CANONICAL_PARAMS = SMALL_FIELD_PARAMS

# Parameters with noise for more realistic training
NOISY_RCSS_PARAMS = RCSSParams(noise_enabled=True)
