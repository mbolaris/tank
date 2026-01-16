"""Goal zone entity for soccer scoring."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.entities.base import Entity

if TYPE_CHECKING:
    from core.entities.ball import Ball
    from core.world import World


class GoalZone(Entity):
    """Zone that detects ball entry for scoring."""

    def __init__(self, environment: World, x: float, y: float, team_id: str, radius: float = 30.0):
        super().__init__(environment, x, y)
        self.id = id(self) % 1000000000  # Unique ID for frontend
        self.team_id = team_id  # "A" or "B"
        self.radius = radius
        self.set_size(self.radius * 2, self.radius * 2)
        self.score_count = 0
        self.is_goal = True  # Tag for renderers
        self.color = "#FF0000" if team_id == "A" else "#0000FF"

    def update(self, frame: int = 0, time_modifier: float = 1.0, time_of_day: float = 0.0) -> Any:
        """Update logic (no-op for static goal)."""
        from core.entities.base import EntityUpdateResult

        return EntityUpdateResult()

    def check_goal(self, ball: Ball) -> bool:
        """Check if ball is inside goal zone.

        Args:
            ball: The ball entity

        Returns:
            True if ball center is within radius
        """
        dist_sq = (self.pos - ball.pos).length_squared()
        return dist_sq < (self.radius * self.radius)
