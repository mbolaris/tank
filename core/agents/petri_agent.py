"""Petri dish microbe agent using shared components.

This is a stub implementation demonstrating how to compose an agent
from shared components. It serves as a template for future agent types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.agents.components import (
    FeedingComponent,
    LocomotionComponent,
    PerceptionComponent,
)
from core.entities.base import Agent
from core.fish_memory import FishMemorySystem

if TYPE_CHECKING:
    from core.world import World


class PetriMicrobeAgent(Agent):
    """Simple microbe agent for Petri dish mode.

    This agent demonstrates composition of shared components to create
    a minimal viable agent. It uses:
    - PerceptionComponent for memory/sensing
    - LocomotionComponent for movement
    - FeedingComponent for energy acquisition

    Unlike Fish, this agent has a simpler lifecycle and no reproduction
    or poker mechanics.
    """

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        speed: float,
        microbe_id: int | None = None,
    ) -> None:
        """Initialize a petri microbe agent.

        Args:
            environment: The world the microbe lives in
            x: Initial x position
            y: Initial y position
            speed: Base speed
            microbe_id: Unique identifier
        """
        super().__init__(environment, x, y, speed)

        self.microbe_id = microbe_id if microbe_id is not None else 0

        # Initialize shared components
        self._memory_system = FishMemorySystem(
            max_memories_per_type=50,
            decay_rate=0.02,
            learning_rate=0.2,
        )
        self._perception = PerceptionComponent(self._memory_system)
        self._locomotion = LocomotionComponent()
        self._feeding = FeedingComponent(bite_size_multiplier=10.0)

        # Simple energy tracking (no complex metabolism)
        self._energy: float = 50.0
        self._max_energy: float = 100.0
        self._age: int = 0

    @property
    def energy(self) -> float:
        """Current energy level."""
        return self._energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level, clamped to [0, max_energy]."""
        self._energy = max(0.0, min(self._max_energy, value))

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity."""
        return self._max_energy

    @property
    def size(self) -> float:
        """Agent size multiplier (constant for microbes)."""
        return 1.0

    def is_dead(self) -> bool:
        """Check if microbe should die."""
        return self._energy <= 0

    def get_remembered_food_locations(self):
        """Get remembered food locations using perception component."""
        return self._perception.get_food_locations()

    def update(self, frame_count: int, time_modifier: float = 1.0, time_of_day=None):
        """Update the microbe state.

        Args:
            frame_count: Current frame number
            time_modifier: Time-based modifier
            time_of_day: Normalized time of day (unused for microbes)

        Returns:
            EntityUpdateResult (empty for now)
        """
        from core.entities.base import EntityUpdateResult

        super().update(frame_count, time_modifier, time_of_day)

        self._age += 1

        # Update perception/memory every 10 frames
        if self._age % 10 == 0:
            self._perception.update(self._age)

        # Basic metabolism
        self._energy -= 0.05 * time_modifier

        # Track direction for potential turn costs
        self._locomotion.update_direction(self.vel)

        return EntityUpdateResult()

    def eat(self, food) -> None:
        """Consume food and gain energy.

        Args:
            food: The food entity to consume
        """
        if not self._feeding.can_eat(self._energy, self._max_energy):
            return

        bite_size = self._feeding.calculate_effective_bite(
            self.size, self._energy, self._max_energy
        )
        gained = self._feeding.consume_food(food, bite_size)
        self._energy += gained

        # Record in memory
        self._perception.record_food_discovery(food.pos)
