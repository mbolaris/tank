"""Perception component for agent sensory and memory systems.

This component manages an agent's sensory data processing and memory queries,
providing a reusable abstraction for different agent types (Fish, PetriMicrobe, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agent_memory import AgentMemorySystem as FishMemorySystem
    from core.math_utils import Vector2


class PerceptionComponent:
    """Perception and sensory processing for agents.

    This component encapsulates:
    - Memory system queries (food locations, predator encounters, etc.)
    - Sensor data aggregation
    - Perception filtering based on time of day or other factors

    The component is stateless except for its reference to the memory system,
    making it easy to compose into different agent types.
    """

    def __init__(self, memory_system: FishMemorySystem) -> None:
        """Initialize perception component.

        Args:
            memory_system: The memory system to query for remembered locations
        """
        self._memory_system = memory_system

    @property
    def memory_system(self) -> FishMemorySystem:
        """Get the underlying memory system."""
        return self._memory_system

    def get_food_locations(self, min_strength: float = 0.1) -> list[Vector2]:
        """Get remembered food locations above minimum strength threshold.

        Args:
            min_strength: Minimum memory strength to include (0.0-1.0)

        Returns:
            List of Vector2 positions where food was previously found
        """
        from core.agent_memory import MemoryType

        memories = self._memory_system.get_all_memories(
            MemoryType.FOOD_LOCATION, min_strength=min_strength
        )
        return [m.location for m in memories]

    def record_food_discovery(self, location: Vector2) -> None:
        """Record a food discovery in memory.

        Args:
            location: Position where food was found
        """
        from core.agent_memory import MemoryType

        self._memory_system.add_memory(MemoryType.FOOD_LOCATION, location)

    def get_danger_locations(self, min_strength: float = 0.1) -> list[Vector2]:
        """Get remembered danger zone locations (predator encounters, etc.).

        Args:
            min_strength: Minimum memory strength to include (0.0-1.0)

        Returns:
            List of Vector2 positions marked as dangerous
        """
        from core.agent_memory import MemoryType

        memories = self._memory_system.get_all_memories(
            MemoryType.DANGER_ZONE, min_strength=min_strength
        )
        return [m.location for m in memories]

    def record_danger(self, location: Vector2) -> None:
        """Record a dangerous location in memory (predator encounter, etc.).

        Args:
            location: Position where danger was encountered
        """
        from core.agent_memory import MemoryType

        self._memory_system.add_memory(MemoryType.DANGER_ZONE, location)

    def update(self, age: int) -> None:
        """Update the memory system (decay old memories).

        Args:
            age: Current age of the agent (for time-based decay)
        """
        self._memory_system.update(age)

    def get_danger_zones(self, min_strength: float = 0.3) -> list[Vector2]:
        """Get locations to avoid based on negative experiences.

        Combines predator encounters and other danger memories.

        Args:
            min_strength: Minimum memory strength to include

        Returns:
            List of positions to avoid
        """
        return self.get_danger_locations(min_strength)
