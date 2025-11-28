"""Collision detection system.

This module provides collision detection for entity objects in the simulation.
"""

from typing import TYPE_CHECKING

from core.constants import FRACTAL_PLANTS_ENABLED
from core.entities.fractal_plant import PlantNectar

if TYPE_CHECKING:
    from core.entities import Agent
    from core.simulation_engine import SimulationEngine


class CollisionDetector:
    """Base class for collision detection strategies."""

    def collides(self, agent1: "Agent", agent2: "Agent") -> bool:
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

    def collides(self, agent1: "Agent", agent2: "Agent") -> bool:
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
            x1 + w1 < x2  # agent1 is left of agent2
            or x1 > x2 + w2  # agent1 is right of agent2
            or y1 + h1 < y2  # agent1 is above agent2
            or y1 > y2 + h2  # agent1 is below agent2
        )


class CircleCollisionDetector(CollisionDetector):
    """Circle-based collision detection (distance-based)."""

    def collides(self, agent1: "Agent", agent2: "Agent", threshold: float = None) -> bool:
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
        distance = (dx**2 + dy**2) ** 0.5

        # Default threshold is average of widths
        if threshold is None:
            threshold = (w1 + w2) / 2

        return distance < threshold


# Default collision detector
default_collision_detector = RectCollisionDetector()


class CollisionSystem:
    """Collision utilities that delegate to the simulation engine."""

    def __init__(self, engine: "SimulationEngine") -> None:
        self.engine = engine

    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide using bounding box collision."""
        return (
            e1.pos.x < e2.pos.x + e2.width
            and e1.pos.x + e1.width > e2.pos.x
            and e1.pos.y < e2.pos.y + e2.height
            and e1.pos.y + e1.height > e2.pos.y
        )

    def handle_fish_food_collision(self, fish: "Agent", food: "Agent") -> None:
        """Handle collision between a fish and food, including plant nectar."""
        if isinstance(food, PlantNectar) and FRACTAL_PLANTS_ENABLED:
            fish.eat(food)

            if food.is_consumed():
                parent_genome = food.consume()
                parent_x = food.source_plant.pos.x if food.source_plant else food.pos.x
                parent_y = food.source_plant.pos.y if food.source_plant else food.pos.y

                self.engine.sprout_new_plant(parent_genome, parent_x, parent_y)
                self.engine.remove_entity(food)
        else:
            fish.eat(food)

            if food.is_fully_consumed():
                food.get_eaten()
                self.engine.remove_entity(food)
