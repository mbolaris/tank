"""RCSS-Lite physics mode for agent movement near the ball.

When enabled, agents near the ball switch to RCSS-Lite physics which includes:
- Stamina-limited movement (energy cost for dashing)
- Turn inertia (slower turns when moving fast)
- Acceleration-based movement (not direct velocity)
- Speed capping based on stamina

This enables more realistic and constrained movement for strategic gameplay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.math_utils import Vector2
from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS, RCSSParams

if TYPE_CHECKING:
    from core.entities.fish import Fish


@dataclass
class RCSSLiteAgentState:
    """Per-agent RCSS-Lite state tracking.

    Attributes:
        stamina: Current stamina [0 to stamina_max]
        effort: Effort multiplier [effort_min to 1.0]
        recovery: Recovery multiplier [recovery_min to 1.0]
        body_angle: Agent facing angle in radians
        velocity: Current velocity vector
        last_dash_power: Power of last dash command [0-100]
    """

    stamina: float = SOCCER_CANONICAL_PARAMS.stamina_max
    effort: float = 1.0
    recovery: float = 1.0
    body_angle: float = 0.0  # Radians
    velocity: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    last_dash_power: float = 0.0
    last_turn_moment: float = 0.0


class RCSSLitePhysicsEngine:
    """RCSS-Lite physics engine for constrained agent movement.

    Applies RCSS-compatible physics including stamina limiting,
    turn inertia, and acceleration-based movement.
    """

    def __init__(self, params: RCSSParams | None = None):
        """Initialize the RCSS-Lite physics engine.

        Args:
            params: Canonical RCSS parameters (uses defaults if None)
        """
        self.params = params or SOCCER_CANONICAL_PARAMS

    def apply_dash_command(
        self, agent: Fish, agent_state: RCSSLiteAgentState, power: float
    ) -> None:
        """Apply a dash command to an agent.

        Args:
            agent: The fish agent
            agent_state: The agent's RCSS-Lite state
            power: Dash power [0-100]
        """
        # Clamp power
        power = max(0.0, min(100.0, power))

        # Check stamina (need at least abs(power) * dash_consume_rate)
        stamina_cost = abs(power) * self.params.dash_consume_rate
        if agent_state.stamina < stamina_cost:
            power = agent_state.stamina / self.params.dash_consume_rate

        # Consume stamina
        agent_state.stamina -= abs(power) * self.params.dash_consume_rate

        # Apply acceleration based on body angle and effort
        effective_power = power * agent_state.effort
        acceleration = effective_power * self.params.dash_power_rate

        # Calculate acceleration direction (relative to body angle)
        import math

        accel_x = acceleration * math.cos(agent_state.body_angle)
        accel_y = acceleration * math.sin(agent_state.body_angle)

        # Add acceleration to velocity
        agent_state.velocity.x += accel_x
        agent_state.velocity.y += accel_y

        # Cap speed
        speed = agent_state.velocity.length()
        if speed > self.params.player_speed_max:
            agent_state.velocity = agent_state.velocity / speed * self.params.player_speed_max

        agent_state.last_dash_power = power

    def apply_turn_command(self, agent_state: RCSSLiteAgentState, moment: float) -> None:
        """Apply a turn command to an agent.

        Args:
            agent_state: The agent's RCSS-Lite state
            moment: Turn moment [-180, 180] degrees
        """
        # Clamp moment
        moment = max(self.params.min_moment, min(self.params.max_moment, moment))

        # Apply inertia based on speed
        speed = agent_state.velocity.length()
        inertia_factor = 1.0 + self.params.inertia_moment * speed

        # Calculate actual turn (in radians)
        import math

        actual_turn_degrees = moment / inertia_factor
        actual_turn_radians = math.radians(actual_turn_degrees)

        # Apply turn to body angle
        agent_state.body_angle += actual_turn_radians

        # Normalize angle to [-pi, pi]
        while agent_state.body_angle > math.pi:
            agent_state.body_angle -= 2 * math.pi
        while agent_state.body_angle < -math.pi:
            agent_state.body_angle += 2 * math.pi

        agent_state.last_turn_moment = moment

    def update_physics(self, agent_state: RCSSLiteAgentState) -> None:
        """Update agent physics state (velocity decay, stamina recovery).

        Should be called after all commands are applied in a cycle.

        Args:
            agent_state: The agent's RCSS-Lite state
        """
        # Apply velocity decay
        agent_state.velocity *= self.params.player_decay

        # Update stamina recovery based on thresholds
        recover_dec_thr = self.params.stamina_max * 0.25  # 25%
        effort_dec_thr = self.params.stamina_max * 0.25  # 25%
        effort_inc_thr = self.params.stamina_max * 0.6  # 60%

        if agent_state.stamina <= recover_dec_thr:
            agent_state.recovery *= 1.0 - self.params.recover_dec
            agent_state.recovery = max(self.params.recover_min, agent_state.recovery)

        if agent_state.stamina <= effort_dec_thr:
            agent_state.effort *= 1.0 - self.params.effort_dec
            agent_state.effort = max(self.params.effort_min, agent_state.effort)

        # Recover stamina
        agent_state.stamina += self.params.stamina_inc_max * agent_state.recovery
        agent_state.stamina = min(self.params.stamina_max, agent_state.stamina)

        # Recover effort when stamina is good
        if agent_state.stamina >= effort_inc_thr and agent_state.effort < 1.0:
            agent_state.effort += self.params.effort_inc
            agent_state.effort = min(1.0, agent_state.effort)

    def get_stamina_level(self, agent_state: RCSSLiteAgentState) -> str:
        """Get stamina level description.

        Args:
            agent_state: The agent's RCSS-Lite state

        Returns:
            "high", "good", "low", or "critical"
        """
        stamina_ratio = agent_state.stamina / self.params.stamina_max

        if stamina_ratio >= 0.75:
            return "high"
        elif stamina_ratio >= 0.5:
            return "good"
        elif stamina_ratio >= 0.25:
            return "low"
        else:
            return "critical"


def create_rcss_agent_state(fish: Fish) -> RCSSLiteAgentState:
    """Create RCSS-Lite agent state from a fish.

    Args:
        fish: The fish entity

    Returns:
        RCSSLiteAgentState initialized from fish state
    """
    import math

    # Get current facing angle (or use 0 if not available)
    body_angle = 0.0
    if hasattr(fish, "angle"):
        body_angle = fish.angle
    elif fish.vel.length() > 0:
        body_angle = math.atan2(fish.vel.y, fish.vel.x)

    state = RCSSLiteAgentState(
        stamina=SOCCER_CANONICAL_PARAMS.stamina_max,
        effort=1.0,
        recovery=1.0,
        body_angle=body_angle,
        velocity=fish.vel.copy(),
    )

    return state
