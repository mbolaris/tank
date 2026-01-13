"""Soccer system for ball physics and goal checking.

Manages ball physics updates and goal detection/scoring in the simulation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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

        if self.ball:
            logger.info(f"SoccerSystem initialized with ball at {self.ball.pos}")

    def _do_update(self, frame: int) -> None:
        """Update ball physics and check for goals.

        Args:
            frame: Current frame number
        """
        if not self.enabled or not self.ball:
            return

        # 1. Update ball physics (RCSS-Lite)
        self.ball.update(frame)

        # 2. Check for goals
        if self.goal_manager:
            goal_event = self.goal_manager.check_all_goals(self.ball, frame)

            if goal_event:
                self._handle_goal_scored(goal_event)

    def _handle_goal_scored(self, goal_event) -> None:
        """Handle a goal being scored and award energy.

        Args:
            goal_event: GoalEvent with scorer and team information
        """
        from core.entities import Fish

        if not self.engine.environment:
            return

        # Find all fish on the scoring team
        for fish in self.engine.environment.entities_list:
            if not isinstance(fish, Fish) or fish.is_dead():
                continue

            if fish.team != goal_event.team:
                continue  # Only reward scoring team

            # Award energy
            base_reward = goal_event.base_energy_reward

            # Bonus for actual scorer
            if fish.fish_id == goal_event.scorer_id:
                reward = base_reward * 0.5  # 50% bonus for scorer
            else:
                reward = base_reward * 0.2  # 20% bonus for teammates

            # Apply reward
            fish.energy += reward
            fish.energy = min(fish.energy, fish.max_energy)

            logger.debug(f"Fish {fish.fish_id} awarded {reward:.1f} energy for goal")

        # Log goal event
        logger.info(
            f"Goal scored by team {goal_event.team} "
            f"in zone {goal_event.goal_id} at frame {goal_event.timestamp}"
        )

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
