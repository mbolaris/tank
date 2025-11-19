"""Enhanced memory system for fish.

This module provides advanced memory capabilities including:
- Spatial memory (locations of food, danger, etc.)
- Temporal memory (time-based recall)
- Associative memory (linking events)
- Learning from experience
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from core.math_utils import Vector2


class MemoryType(Enum):
    """Types of memories a fish can have."""

    FOOD_LOCATION = "food_location"
    DANGER_ZONE = "danger_zone"
    SAFE_ZONE = "safe_zone"
    MATE_LOCATION = "mate_location"
    SUCCESSFUL_PATH = "successful_path"


@dataclass
class Memory:
    """A single memory entry."""

    memory_type: MemoryType
    location: Vector2
    strength: float = 1.0  # 0.0 to 1.0, decays over time
    timestamp: int = 0  # Frame when memory was created
    success_count: int = 0  # How many times this memory led to success
    failure_count: int = 0  # How many times this memory led to failure
    metadata: Dict = field(default_factory=dict)  # Additional data

    def decay(self, decay_rate: float = 0.001):
        """Decay memory strength over time."""
        self.strength = max(0.0, self.strength - decay_rate)

    def reinforce(self, amount: float = 0.1):
        """Reinforce memory (increase strength)."""
        self.strength = min(1.0, self.strength + amount)

    def is_expired(self, max_age: int = 1800) -> bool:
        """Check if memory is too old (default 60 seconds at 30fps)."""
        return self.strength <= 0.0 or (
            max_age > 0 and self.timestamp > 0 and time.time() - self.timestamp > max_age
        )


@dataclass
class FishMemorySystem:
    """Advanced memory system for fish behavior.

    Attributes:
        memories: Dictionary of memories by type
        max_memories_per_type: Maximum memories to keep per type
        decay_rate: How fast memories decay
        learning_rate: How fast fish learn from experience
    """

    memories: Dict[MemoryType, List[Memory]] = field(default_factory=dict)
    max_memories_per_type: int = 10
    decay_rate: float = 0.001
    learning_rate: float = 0.05
    current_frame: int = 0

    def __post_init__(self):
        """Initialize memory storage for each type."""
        for memory_type in MemoryType:
            if memory_type not in self.memories:
                self.memories[memory_type] = []

    def add_memory(
        self,
        memory_type: MemoryType,
        location: Vector2,
        strength: float = 1.0,
        metadata: Optional[Dict] = None,
    ):
        """Add a new memory or reinforce existing one nearby.

        Args:
            memory_type: Type of memory
            location: Location associated with memory
            strength: Initial strength (0.0-1.0)
            metadata: Additional data
        """
        # Check if we have a similar memory nearby
        existing = self.find_nearest_memory(memory_type, location, max_distance=50.0)

        if existing:
            # Reinforce existing memory
            existing.reinforce(self.learning_rate)
            existing.location = (existing.location + location) / 2.0  # Average positions
            if metadata:
                existing.metadata.update(metadata)
        else:
            # Create new memory
            memory = Memory(
                memory_type=memory_type,
                location=location,
                strength=strength,
                timestamp=self.current_frame,
                metadata=metadata or {},
            )
            self.memories[memory_type].append(memory)

            # Limit memory count
            if len(self.memories[memory_type]) > self.max_memories_per_type:
                # Remove weakest memory (O(n) min search instead of O(n log n) sort)
                weakest = min(self.memories[memory_type], key=lambda m: m.strength)
                self.memories[memory_type].remove(weakest)

    def find_nearest_memory(
        self,
        memory_type: MemoryType,
        current_pos: Vector2,
        max_distance: float = float("inf"),
        min_strength: float = 0.1,
    ) -> Optional[Memory]:
        """Find nearest memory of given type.

        Args:
            memory_type: Type of memory to search
            current_pos: Current position
            max_distance: Maximum distance to consider
            min_strength: Minimum strength to consider

        Returns:
            Nearest memory or None
        """
        valid_memories = [
            m for m in self.memories.get(memory_type, []) if m.strength >= min_strength
        ]

        if not valid_memories:
            return None

        # Find nearest
        nearest = min(valid_memories, key=lambda m: (m.location - current_pos).length())
        distance = (nearest.location - current_pos).length()

        if distance <= max_distance:
            return nearest
        return None

    def get_all_memories(self, memory_type: MemoryType, min_strength: float = 0.1) -> List[Memory]:
        """Get all memories of a type above minimum strength.

        Args:
            memory_type: Type of memory
            min_strength: Minimum strength threshold

        Returns:
            List of valid memories
        """
        return [m for m in self.memories.get(memory_type, []) if m.strength >= min_strength]

    def remember_success(
        self, memory_type: MemoryType, location: Vector2, proximity_radius: float = 50.0
    ):
        """Mark memories near a location as successful.

        Args:
            memory_type: Type of memory
            location: Location of success
            proximity_radius: How close memories need to be
        """
        for memory in self.memories.get(memory_type, []):
            if (memory.location - location).length() <= proximity_radius:
                memory.success_count += 1
                memory.reinforce(self.learning_rate * 2.0)  # Double reinforcement for success

    def remember_failure(
        self, memory_type: MemoryType, location: Vector2, proximity_radius: float = 50.0
    ):
        """Mark memories near a location as failures.

        Args:
            memory_type: Type of memory
            location: Location of failure
            proximity_radius: How close memories need to be
        """
        for memory in self.memories.get(memory_type, []):
            if (memory.location - location).length() <= proximity_radius:
                memory.failure_count += 1
                memory.strength *= 0.5  # Weaken failed memories

    def get_best_memory(self, memory_type: MemoryType) -> Optional[Memory]:
        """Get the best memory based on success rate and strength.

        Args:
            memory_type: Type of memory

        Returns:
            Best memory or None
        """
        valid_memories = [m for m in self.memories.get(memory_type, []) if m.strength >= 0.1]

        if not valid_memories:
            return None

        # Score based on success rate and strength
        def score_memory(m: Memory) -> float:
            total_attempts = m.success_count + m.failure_count
            if total_attempts == 0:
                success_rate = 0.5  # Neutral for untested memories
            else:
                success_rate = m.success_count / total_attempts

            return m.strength * 0.5 + success_rate * 0.5

        return max(valid_memories, key=score_memory)

    def update(self, current_frame: int):
        """Update memory system (decay old memories).

        Args:
            current_frame: Current simulation frame
        """
        self.current_frame = current_frame

        # Decay and clean up all memories
        for memory_type in MemoryType:
            memories = self.memories[memory_type]

            # Decay all memories
            for memory in memories:
                memory.decay(self.decay_rate)

            # Remove expired memories
            self.memories[memory_type] = [
                m for m in memories if not m.is_expired(max_age=1800)  # 60 seconds at 30fps
            ]

    def clear_memories(self, memory_type: Optional[MemoryType] = None):
        """Clear all memories of a type, or all memories.

        Args:
            memory_type: Type to clear, or None to clear all
        """
        if memory_type:
            self.memories[memory_type] = []
        else:
            for mt in MemoryType:
                self.memories[mt] = []

    def get_memory_count(self, memory_type: MemoryType) -> int:
        """Get count of active memories of a type.

        Args:
            memory_type: Type of memory

        Returns:
            Count of memories with strength > 0.1
        """
        return len([m for m in self.memories.get(memory_type, []) if m.strength >= 0.1])

    def get_average_memory_strength(self, memory_type: MemoryType) -> float:
        """Get average strength of memories of a type.

        Args:
            memory_type: Type of memory

        Returns:
            Average strength (0.0-1.0)
        """
        valid_memories = [m for m in self.memories.get(memory_type, []) if m.strength >= 0.1]
        if not valid_memories:
            return 0.0
        return sum(m.strength for m in valid_memories) / len(valid_memories)
