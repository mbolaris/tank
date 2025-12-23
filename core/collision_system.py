"""Collision detection system.

This module provides collision detection for entity objects in the simulation.

Architecture Notes:
- CollisionDetector classes implement the Strategy pattern for different
  collision algorithms (AABB, circle-based, etc.)
- CollisionSystem is a simulation system that handles collision logic
- The system extends BaseSystem and declares UpdatePhase.COLLISION
- Plant sprouting logic is included here for simplicity (triggered when nectar is consumed)
"""

import random
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.config.plants import PLANT_SPROUTING_CHANCE
from core.config.server import PLANTS_ENABLED
from core.entities.plant import PlantNectar
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Agent
    from core.simulation_engine import SimulationEngine
    from core.simulation_runtime import SimulationContext


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


@runs_in_phase(UpdatePhase.COLLISION)
class CollisionSystem(BaseSystem):
    """System for detecting and handling collisions between entities.

    This system runs in the COLLISION phase and:
    - Checks for collisions between fish and food
    - Handles collision effects (eating, etc.)
    - Tracks collision statistics for debugging

    Note: The actual collision iteration is done in SimulationEngine.handle_collisions()
    which uses the spatial grid for efficiency. This system provides the collision
    handling logic.
    """

    def __init__(self, engine: "SimulationEngine", context: Optional["SimulationContext"] = None) -> None:
        """Initialize the collision system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "Collision", context=context)
        # Cumulative stats (all-time)
        self._collisions_checked: int = 0
        self._collisions_detected: int = 0
        self._fish_food_collisions: int = 0

        # Per-frame stats (reset each frame)
        self._frame_collisions_checked: int = 0
        self._frame_collisions_detected: int = 0
        self._frame_food_eaten: int = 0
        self._frame_entities_removed: int = 0

    def _do_update(self, frame: int) -> Optional[SystemResult]:
        """Return statistics about collisions processed this frame.

        Collision detection is triggered by SimulationEngine.handle_collisions()
        which calls check_collision and handle_fish_food_collision. This method
        captures the per-frame stats and resets them for the next frame.

        Returns:
            SystemResult with collision statistics
        """
        result = SystemResult(
            entities_affected=self._frame_collisions_detected,
            entities_removed=self._frame_entities_removed,
            details={
                "collisions_checked": self._frame_collisions_checked,
                "collisions_detected": self._frame_collisions_detected,
                "food_eaten": self._frame_food_eaten,
            },
        )

        # Reset per-frame counters
        self._frame_collisions_checked = 0
        self._frame_collisions_detected = 0
        self._frame_food_eaten = 0
        self._frame_entities_removed = 0

        return result

    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide using bounding box collision.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities are colliding
        """
        self._collisions_checked += 1
        self._frame_collisions_checked += 1
        collides = (
            e1.pos.x < e2.pos.x + e2.width
            and e1.pos.x + e1.width > e2.pos.x
            and e1.pos.y < e2.pos.y + e2.height
            and e1.pos.y + e1.height > e2.pos.y
        )
        if collides:
            self._collisions_detected += 1
            self._frame_collisions_detected += 1
        return collides

    def handle_fish_food_collision(self, fish: "Agent", food: "Agent") -> None:
        """Handle collision between a fish and food, including plant nectar.

        Args:
            fish: The fish entity
            food: The food entity being eaten

        Note: Plant sprouting logic is included here (when nectar is consumed,
        there's a chance to sprout a new plant nearby).
        """
        self._fish_food_collisions += 1
        self._frame_food_eaten += 1

        if isinstance(food, PlantNectar) and PLANTS_ENABLED:
            fish.eat(food)

            if food.is_consumed():
                parent_genome = food.consume()
                parent_x = food.source_plant.pos.x if food.source_plant else food.pos.x
                parent_y = food.source_plant.pos.y if food.source_plant else food.pos.y

                # Check sprouting chance (use engine RNG for determinism)
                rng = getattr(self._engine.ecosystem, "rng", random) if hasattr(self._engine, "ecosystem") and self._engine.ecosystem else random
                if rng.random() < PLANT_SPROUTING_CHANCE:
                    self.engine.sprout_new_plant(parent_genome, parent_x, parent_y)

                self.engine.remove_entity(food)
                self._frame_entities_removed += 1
        else:
            fish.eat(food)

            if food.is_fully_consumed():
                food.get_eaten()
                self.engine.remove_entity(food)
                self._frame_entities_removed += 1

    def get_debug_info(self) -> Dict[str, Any]:
        """Return collision statistics for debugging."""
        return {
            **super().get_debug_info(),
            "collisions_checked": self._collisions_checked,
            "collisions_detected": self._collisions_detected,
            "fish_food_collisions": self._fish_food_collisions,
            "hit_rate": (
                self._collisions_detected / self._collisions_checked
                if self._collisions_checked > 0
                else 0.0
            ),
        }
