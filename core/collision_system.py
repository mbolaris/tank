"""Collision detection system (pure logic, no pygame dependency).

This module provides collision detection that works with pure entity objects
without requiring pygame sprites.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Agent


class CollisionDetector:
    """Base class for collision detection strategies."""

    def collides(self, agent1: 'Agent', agent2: 'Agent') -> bool:
        """Check if two agents collide.

        Args:
            agent1: First agent
            agent2: Second agent

        Returns:
            True if agents are colliding
        """
        raise NotImplementedError("Subclasses must implement collides()")


class RectCollisionDetector(CollisionDetector):
    """Rectangle-based collision detection (AABB)."""

    def collides(self, agent1: 'Agent', agent2: 'Agent') -> bool:
        """Check if two agents' bounding boxes collide.

        Args:
            agent1: First agent
            agent2: Second agent

        Returns:
            True if bounding boxes overlap
        """
        # Get bounding boxes
        x1, y1, w1, h1 = agent1.get_rect()
        x2, y2, w2, h2 = agent2.get_rect()

        # AABB collision detection
        return not (
            x1 + w1 < x2 or  # agent1 is left of agent2
            x1 > x2 + w2 or  # agent1 is right of agent2
            y1 + h1 < y2 or  # agent1 is above agent2
            y1 > y2 + h2     # agent1 is below agent2
        )


class CircleCollisionDetector(CollisionDetector):
    """Circle-based collision detection (distance-based)."""

    def collides(self, agent1: 'Agent', agent2: 'Agent', threshold: float = None) -> bool:
        """Check if two agents collide based on distance.

        Args:
            agent1: First agent
            agent2: Second agent
            threshold: Distance threshold (if None, uses average of widths)

        Returns:
            True if distance between centers is less than threshold
        """
        # Calculate centers
        x1, y1, w1, h1 = agent1.get_rect()
        x2, y2, w2, h2 = agent2.get_rect()

        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2

        # Calculate distance
        dx = center2_x - center1_x
        dy = center2_y - center1_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # Default threshold is average of widths
        if threshold is None:
            threshold = (w1 + w2) / 2

        return distance < threshold


# Default collision detector
default_collision_detector = RectCollisionDetector()
