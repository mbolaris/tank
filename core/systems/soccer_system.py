"""Soccer system for ball physics and goal checking.

Manages ball physics updates and goal detection/scoring in the simulation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.energy.energy_utils import apply_energy_delta
from core.systems.base import BaseSystem
from core.update_phases import UpdatePhase

if TYPE_CHECKING:
    from core.entities.ball import Ball
    from core.entities.goal_zone import GoalZoneManager
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class SoccerSystem(BaseSystem):
    """System for managing ball physics and goal detection.

    This system:
    1. Updates ball physics each frame (RCSS-Lite: accel→vel→pos→decay)
    2. Detects goals and triggers scoring events
    3. Awards energy to scoring teams
    4. Tracks goal statistics

    The system is optional - if no ball is present, it's a no-op.
    """

    def __init__(self, engine: SimulationEngine):
        """Initialize the soccer system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, name="soccer")
        self.ball: Ball | None = None
        self.goal_manager: GoalZoneManager | None = None
        self.enabled: bool = False

    @property
    def runs_in_phase(self) -> UpdatePhase:
        """Soccer system runs in INTERACTION phase."""
        return UpdatePhase.INTERACTION

    def setup(self) -> None:
        """Setup is called by the engine after initialization."""
        # Check if ball is available on environment
        if self.engine.environment and hasattr(self.engine.environment, "ball"):
            self.ball = self.engine.environment.ball
            self.enabled = self.ball is not None

        # Check if goal manager is available
        if self.engine.environment and hasattr(self.engine.environment, "goal_manager"):
            self.goal_manager = self.engine.environment.goal_manager

    def _do_update(self, frame: int) -> None:
        """Update ball physics and check for goals.

        Args:
            frame: Current frame number
        """
        # Lazy initialization: find ball/goals if not set
        if not self.ball and self.engine.environment:
            if hasattr(self.engine.environment, "ball"):
                self.ball = self.engine.environment.ball
                self.enabled = self.ball is not None

        if not self.goal_manager and self.engine.environment:
            if hasattr(self.engine.environment, "goal_manager"):
                self.goal_manager = self.engine.environment.goal_manager

        if not self.enabled or not self.ball:
            return

        # 1. Auto-kick: Process kicks BEFORE ball physics (RCSS-style)
        # This ensures kicks affect the same frame's physics step
        self._process_auto_kicks(frame)

        # 2. Update ball physics (RCSS-Lite: accel→vel→pos→decay)
        self.ball.update(frame)

        # 3. Check for goals
        if self.goal_manager:
            goal_event = self.goal_manager.check_all_goals(self.ball, frame)

            if goal_event:
                self._handle_goal_scored(goal_event)

    def _process_auto_kicks(self, frame: int) -> None:
        """Auto-kick: Fish near the ball will automatically kick it.

        This provides a simple interaction without requiring trained policies.
        Fish kick the ball toward the opponent's goal.

        Kicker selection is deterministic: the closest eligible fish kicks,
        with fish_id as tie-breaker for equal distances.

        Args:
            frame: Current frame number
        """
        import math

        from core.math_utils import Vector2

        if not self.engine.environment or not self.ball:
            return

        ball_x = self.ball.pos.x
        ball_y = self.ball.pos.y
        # RCSS kickable_margin + player_size = ~1.0m, scaled = 10px
        # Keep slightly larger (30px) since fish are visually bigger than RCSS players
        kickable_distance = 30.0
        kickable_distance_sq = kickable_distance * kickable_distance

        # Deterministic selection without per-frame sort: choose min((dist_sq, fish_id))
        best_key: tuple[float, int] | None = None
        kicker: object | None = None

        for entity in self.engine.entities_list:
            # Use snapshot_type instead of isinstance for loose coupling
            if getattr(entity, "snapshot_type", None) != "fish" or entity.is_dead():
                continue

            # Calculate distance to ball
            dx = ball_x - entity.pos.x
            dy = ball_y - entity.pos.y
            dist_sq = dx * dx + dy * dy

            if 0 < dist_sq <= kickable_distance_sq:
                fish_id = getattr(entity, "fish_id", 0)
                candidate_key = (dist_sq, fish_id)
                if best_key is None or candidate_key < best_key:
                    best_key = candidate_key
                    kicker = entity

        if kicker is None:
            return

        # Determine team: use fish.team if set, fallback to fish_id parity
        fish_team = getattr(kicker, "team", None)
        if fish_team is not None:
            is_team_a = fish_team == "A"
        else:
            fish_id = getattr(kicker, "fish_id", 0)
            is_team_a = (fish_id % 2) == 0

        # Primary kick direction: fish's facing/movement direction
        if hasattr(kicker, "vel") and kicker.vel.length() > 0.1:
            # Kick in direction fish is moving
            kick_dx = kicker.vel.x
            kick_dy = kicker.vel.y
        else:
            # Stationary fish: kick toward opponent goal
            if is_team_a:
                kick_dx = self.engine.environment.width - 50 - ball_x
            else:
                kick_dx = 50 - ball_x
            kick_dy = (self.engine.environment.height / 2) - ball_y

        # Add slight goal-seeking bias without overwhelming direction
        if is_team_a:
            goal_bias_x = (self.engine.environment.width - 50 - ball_x) * 0.2
        else:
            goal_bias_x = (50 - ball_x) * 0.2
        kick_dx += goal_bias_x

        kick_dist = math.sqrt(kick_dx * kick_dx + kick_dy * kick_dy)

        if kick_dist > 0:
            direction = Vector2(kick_dx / kick_dist, kick_dy / kick_dist)
            # Kick power: base + fish speed bonus
            fish_speed = kicker.vel.length() if hasattr(kicker, "vel") else 0
            power = 40.0 + min(fish_speed * 20.0, 40.0)  # Power range: 40-80
            self.ball.kick(power, direction, kicker=kicker)

            # Award small energy reward for kicking via proper channel
            # Fish implements modify_energy(), no fallback needed
            try:
                apply_energy_delta(kicker, 2.0, source="soccer_kick")
            except AttributeError:
                pass

            # Set visual effect for HUD display
            setattr(kicker, "soccer_effect_state", {"type": "kick", "amount": 2.0, "timer": 10})

    def _handle_goal_scored(self, goal_event) -> None:
        """Handle a goal being scored and award energy.

        Args:
            goal_event: GoalEvent with scorer and team information
        """

        if not self.engine.environment:
            return

        # Find the scorer and award energy
        scorer_found = False
        for fish in self.engine.get_fish_list():
            # Use snapshot_type instead of isinstance for loose coupling
            if getattr(fish, "snapshot_type", None) != "fish" or fish.is_dead():
                continue

            # Check if this fish is the scorer
            if fish.fish_id == goal_event.scorer_id:
                # Award big energy reward for scoring via proper channel
                # Fish implements modify_energy(), no fallback needed
                reward = 50.0
                try:
                    apply_energy_delta(fish, reward, source="soccer_goal")
                except AttributeError:
                    pass

                # Set visual effect for HUD display
                fish.soccer_effect_state = {"type": "goal", "amount": reward, "timer": 30}
                scorer_found = True
                logger.info(f"Fish {fish.fish_id} scored a goal! Awarded {reward:.1f} energy")
                break

        if not scorer_found:
            logger.debug("No scorer found to reward (ball may not have been kicked)")

        # Log goal event
        logger.info(
            f"Goal scored by team {goal_event.team} "
            f"in zone {goal_event.goal_id} at frame {goal_event.timestamp}"
        )

        # Reset ball to center after goal
        if self.ball and self.engine.environment:
            from core.math_utils import Vector2

            cx = self.engine.environment.width / 2
            cy = self.engine.environment.height / 2
            self.ball.pos = Vector2(cx, cy)
            self.ball.vel = Vector2(0.0, 0.0)
            self.ball.acceleration = Vector2(0.0, 0.0)
            self.ball.last_kicker = None
            logger.info(f"Ball reset to center ({cx}, {cy})")

        # Emit event for tracking
        if hasattr(self.engine, "event_bus") and self.engine.event_bus:
            try:
                self.engine.event_bus.emit(goal_event)
            except Exception as e:
                logger.warning(f"Failed to emit goal event: {e}")

    def set_ball(self, ball: Ball) -> None:
        """Set the ball entity.

        Args:
            ball: Ball entity
        """
        self.ball = ball
        self.enabled = ball is not None

    def set_goal_manager(self, goal_manager: GoalZoneManager) -> None:
        """Set the goal zone manager.

        Args:
            goal_manager: GoalZoneManager instance
        """
        self.goal_manager = goal_manager
