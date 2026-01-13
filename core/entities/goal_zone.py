"""Goal zone entity for soccer gameplay in tank and Petri dish environments.

Goals are fixed zones that detect when the ball enters and reward the scoring team.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.entities.base import Entity
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities.ball import Ball
    from core.world import World


@dataclass
class GoalEvent:
    """Event data when a goal is scored."""

    goal_id: str  # Unique ID for this goal zone
    team: str  # Team that scored ('A' or 'B')
    scorer_id: int | None  # Fish ID of the scorer (if tracked)
    assister_id: int | None  # Fish ID of the assister (if tracked)
    position: Vector2  # Position where ball entered goal
    timestamp: int  # Frame number when goal occurred
    base_energy_reward: float  # Base energy given to scoring team


class GoalZone(Entity):
    """Fixed goal zone that detects ball scoring.

    Goals are placed at field boundaries and award energy to the scoring team.
    This is a static entity (extends Entity, not Agent).

    Attributes:
        team: Team that owns the goal ('A' or 'B')
        position: Center position of goal area
        radius: Radius of goal detection zone
        goal_id: Unique identifier for this goal
        last_goal_time: Frame number of last goal scored
        goal_counter: Total goals scored in this zone
    """

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        team: str,
        goal_id: str = "",
        radius: float = 10.0,
        base_energy_reward: float = 50.0,
    ) -> None:
        """Initialize a goal zone.

        Args:
            environment: The world the goal zone exists in
            x: Center x position
            y: Center y position
            team: Team that benefits from this goal ('A' or 'B')
            goal_id: Unique identifier (e.g., 'goal_left', 'goal_right')
            radius: Radius of goal detection zone
            base_energy_reward: Base energy awarded for scoring
        """
        super().__init__(environment, x, y)

        self.team = team
        self.goal_id = goal_id
        self.radius = radius
        self.base_energy_reward = base_energy_reward

        # Statistics tracking
        self.last_goal_time: int = -1000  # Frame number of last goal
        self.goal_counter: int = 0  # Total goals scored in this zone

        # Visualization size
        pixel_radius = int(radius * 2)  # Rough conversion to pixels
        self.set_size(pixel_radius * 2, pixel_radius * 2)

    def check_goal(self, ball: Ball, frame_count: int) -> GoalEvent | None:
        """Check if the ball has entered the goal zone.

        Args:
            ball: The ball to check
            frame_count: Current frame number

        Returns:
            GoalEvent if goal detected, None otherwise
        """
        # Calculate distance from goal center to ball center
        distance = (self.pos - ball.pos).length()

        # Goal detected if ball is within radius
        if distance <= self.radius + ball.size:
            # Determine scorer and assister from ball kick history
            scorer_id = None
            if ball.last_kicker is not None:
                scorer_id = getattr(ball.last_kicker, "fish_id", None)

            # Create goal event
            goal_event = GoalEvent(
                goal_id=self.goal_id,
                team=self.team,
                scorer_id=scorer_id,
                assister_id=None,  # Could be enhanced with assist tracking
                position=ball.pos.copy(),
                timestamp=frame_count,
                base_energy_reward=self.base_energy_reward,
            )

            # Update statistics
            self.last_goal_time = frame_count
            self.goal_counter += 1

            return goal_event

        return None

    def is_ball_in_goal(self, ball: Ball) -> bool:
        """Quick check if ball is in goal zone (without event creation).

        Args:
            ball: The ball to check

        Returns:
            True if ball is in goal zone
        """
        distance = (self.pos - ball.pos).length()
        return distance <= self.radius + ball.size

    def get_distance_to_ball(self, ball: Ball) -> float:
        """Get distance from goal center to ball.

        Args:
            ball: The ball

        Returns:
            Distance in world units
        """
        return (self.pos - ball.pos).length()

    def reset_stats(self) -> None:
        """Reset goal zone statistics."""
        self.last_goal_time = -1000
        self.goal_counter = 0


class GoalZoneManager:
    """Manager for multiple goal zones in the environment.

    Handles goal detection and energy distribution.
    """

    def __init__(self):
        """Initialize the goal zone manager."""
        self.zones: dict[str, GoalZone] = {}
        self.recent_goals: list[GoalEvent] = []

    def register_zone(self, zone: GoalZone) -> None:
        """Register a goal zone.

        Args:
            zone: Goal zone to register
        """
        self.zones[zone.goal_id] = zone

    def check_all_goals(self, ball: Ball, frame_count: int) -> GoalEvent | None:
        """Check all goal zones for scoring.

        Args:
            ball: The ball to check
            frame_count: Current frame number

        Returns:
            First goal event detected, or None
        """
        for zone in self.zones.values():
            goal_event = zone.check_goal(ball, frame_count)
            if goal_event is not None:
                self.recent_goals.append(goal_event)
                return goal_event

        return None

    def get_zones_by_team(self, team: str) -> list[GoalZone]:
        """Get all goal zones for a team.

        Args:
            team: Team identifier ('A' or 'B')

        Returns:
            List of goal zones belonging to team
        """
        return [zone for zone in self.zones.values() if zone.team == team]

    def reset_all_stats(self) -> None:
        """Reset all goal zone statistics."""
        for zone in self.zones.values():
            zone.reset_stats()
        self.recent_goals.clear()
