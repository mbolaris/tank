"""RCSS-Lite physics mode for agent movement near the ball.

When enabled, agents near the ball switch to RCSS-Lite physics which includes:
- Stamina-limited movement (energy cost for dashing)
- Turn inertia (slower turns when moving fast)
- Acceleration-based movement (not direct velocity)
- Speed capping based on stamina

This enables more realistic and constrained movement for strategic gameplay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities.fish import Fish


@dataclass
class RCSSLitePhysicsParams:
    """Physics parameters for RCSS-Lite movement mode.

    These mirror the soccer engine physics for consistency.
    """

    # Acceleration and speed
    dash_power_rate: float = 0.006  # Acceleration per power unit
    player_speed_max: float = 1.05  # Max velocity per cycle
    player_decay: float = 0.4  # Velocity retention ratio

    # Stamina system
    stamina_max: float = 8000.0  # Maximum stamina
    stamina_inc_max: float = 45.0  # Recovery per cycle
    dash_consume_rate: float = 1.0  # Stamina per power unit
    effort_dec: float = 0.005  # Effort degradation per cycle
    effort_min: float = 0.6  # Minimum effort multiplier
    effort_inc: float = 0.01  # Effort recovery per cycle
    recover_dec: float = 0.002  # Recovery degradation
    recover_min: float = 0.5  # Minimum recovery multiplier

    # Turn mechanics
    inertia_moment: float = 5.0  # Speed-dependent turn reduction
    max_moment: float = 180.0  # Max turn angle (degrees)


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

    stamina: float = 8000.0
    effort: float = 1.0
    recovery: float = 1.0
    body_angle: float = 0.0  # Radians
    velocity: Vector2 = None  # Will be initialized as Vector2(0, 0)
    last_dash_power: float = 0.0
    last_turn_moment: float = 0.0

    def __post_init__(self):
        """Initialize velocity if not provided."""
        if self.velocity is None:
            self.velocity = Vector2(0.0, 0.0)


class RCSSLitePhysicsEngine:
    """RCSS-Lite physics engine for constrained agent movement.

    Applies RCSS-compatible physics including stamina limiting,
    turn inertia, and acceleration-based movement.
    """

    def __init__(self, params: Optional[RCSSLitePhysicsParams] = None):
        """Initialize the RCSS-Lite physics engine.

        Args:
            params: Physics parameters (uses defaults if None)
        """
        self.params = params or RCSSLitePhysicsParams()

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
        moment = max(-self.params.max_moment, min(self.params.max_moment, moment))

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
        stamina=8000.0,  # Start with full stamina
        effort=1.0,
        recovery=1.0,
        body_angle=body_angle,
        velocity=fish.vel.copy(),
    )

    return state
