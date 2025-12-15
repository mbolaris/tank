"""Type-safe entity identifiers.

This module provides type-safe wrappers for entity IDs to prevent
accidentally mixing up IDs of different entity types.

Why Type-Safe IDs?
------------------
Before (raw integers):
    def record_poker(winner_id: int, loser_id: int, plant_id: int):
        # Bug: nothing prevents accidentally swapping winner_id and plant_id!
        db.save(winner_id, loser_id, plant_id)

After (typed IDs):
    def record_poker(winner: FishId, loser: FishId, plant: PlantId):
        # Type checker catches if you pass PlantId where FishId expected!
        db.save(winner, loser, plant)

Benefits:
- Type checker catches ID mix-ups at compile time
- Self-documenting function signatures
- Clear distinction in debugging output
- IDs remain comparable to raw ints when needed

Usage:
------
    # Create IDs
    fish_id = FishId(42)
    plant_id = PlantId(1)

    # Use in function signatures
    def feed_fish(fish: FishId, food: FoodId) -> None:
        ...

    # Access raw value when needed
    raw_id = fish_id.value  # 42

    # IDs are hashable and comparable
    fish_ids = {FishId(1), FishId(2)}
    if FishId(1) in fish_ids:
        ...

    # String representation includes type
    print(fish_id)  # "Fish#42"

Design Notes:
- IDs are immutable (frozen dataclass)
- IDs are hashable (can be used in sets/dicts)
- IDs of same type can be compared
- IDs can be compared to raw ints for compatibility
- Each ID type has a distinct prefix in string output
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union


# ============================================================================
# Base ID Type
# ============================================================================


@dataclass(frozen=True)
class EntityId:
    """Base class for all entity IDs.

    This provides common functionality for all ID types:
    - Immutable (frozen)
    - Hashable (usable in sets/dicts)
    - Comparable to same type and raw ints
    - Clear string representation
    """

    value: int
    _prefix: str = "Entity"  # Override in subclasses

    def __post_init__(self) -> None:
        """Validate the ID value."""
        if not isinstance(self.value, int):
            raise TypeError(f"ID value must be int, got {type(self.value).__name__}")
        if self.value < 0:
            raise ValueError(f"ID value must be non-negative, got {self.value}")

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self._prefix}#{self.value}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}({self.value})"

    def __eq__(self, other: Any) -> bool:
        """Compare to same type or raw int."""
        if isinstance(other, self.__class__):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Hash based on value (same as raw int)."""
        return hash(self.value)

    def __lt__(self, other: Any) -> bool:
        """Less than comparison."""
        if isinstance(other, self.__class__):
            return self.value < other.value
        if isinstance(other, int):
            return self.value < other
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        """Less than or equal comparison."""
        if isinstance(other, self.__class__):
            return self.value <= other.value
        if isinstance(other, int):
            return self.value <= other
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        """Greater than comparison."""
        if isinstance(other, self.__class__):
            return self.value > other.value
        if isinstance(other, int):
            return self.value > other
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, self.__class__):
            return self.value >= other.value
        if isinstance(other, int):
            return self.value >= other
        return NotImplemented

    def __int__(self) -> int:
        """Convert to raw int when needed."""
        return self.value


# ============================================================================
# Specific ID Types
# ============================================================================


@dataclass(frozen=True, eq=False)
class FishId(EntityId):
    """Type-safe identifier for Fish entities.

    Example:
        fish_id = FishId(42)
        print(fish_id)  # "Fish#42"
    """

    value: int
    _prefix: str = "Fish"


@dataclass(frozen=True, eq=False)
class PlantId(EntityId):
    """Type-safe identifier for Plant entities.

    Example:
        plant_id = PlantId(1)
        print(plant_id)  # "Plant#1"
    """

    value: int
    _prefix: str = "Plant"


@dataclass(frozen=True, eq=False)
class FoodId(EntityId):
    """Type-safe identifier for Food entities.

    Example:
        food_id = FoodId(100)
        print(food_id)  # "Food#100"
    """

    value: int
    _prefix: str = "Food"


@dataclass(frozen=True, eq=False)
class NectarId(EntityId):
    """Type-safe identifier for Nectar entities.

    Example:
        nectar_id = NectarId(50)
        print(nectar_id)  # "Nectar#50"
    """

    value: int
    _prefix: str = "Nectar"


@dataclass(frozen=True, eq=False)
class CrabId(EntityId):
    """Type-safe identifier for Crab entities.

    Example:
        crab_id = CrabId(3)
        print(crab_id)  # "Crab#3"
    """

    value: int
    _prefix: str = "Crab"


# ============================================================================
# ID Generation
# ============================================================================


class IdGenerator:
    """Generates unique IDs for entities.

    Each entity type has its own counter to avoid ID collisions and
    keep IDs small. IDs are never reused within a simulation run.

    Example:
        gen = IdGenerator()
        fish1 = gen.next_fish()  # FishId(1)
        fish2 = gen.next_fish()  # FishId(2)
        plant1 = gen.next_plant()  # PlantId(1)
    """

    def __init__(self, start_offset: int = 0) -> None:
        """Initialize the generator.

        Args:
            start_offset: Starting value for all counters (for testing)
        """
        self._fish_counter = start_offset
        self._plant_counter = start_offset
        self._food_counter = start_offset
        self._nectar_counter = start_offset
        self._crab_counter = start_offset

    def next_fish(self) -> FishId:
        """Generate the next Fish ID."""
        self._fish_counter += 1
        return FishId(self._fish_counter)

    def next_plant(self) -> PlantId:
        """Generate the next Plant ID."""
        self._plant_counter += 1
        return PlantId(self._plant_counter)

    def next_food(self) -> FoodId:
        """Generate the next Food ID."""
        self._food_counter += 1
        return FoodId(self._food_counter)

    def next_nectar(self) -> NectarId:
        """Generate the next Nectar ID."""
        self._nectar_counter += 1
        return NectarId(self._nectar_counter)

    def next_crab(self) -> CrabId:
        """Generate the next Crab ID."""
        self._crab_counter += 1
        return CrabId(self._crab_counter)

    def get_stats(self) -> dict:
        """Get current counter values for debugging."""
        return {
            "fish": self._fish_counter,
            "plant": self._plant_counter,
            "food": self._food_counter,
            "nectar": self._nectar_counter,
            "crab": self._crab_counter,
        }


# ============================================================================
# Type Aliases for Common Patterns
# ============================================================================

# Union type for "any entity ID"
AnyEntityId = Union[FishId, PlantId, FoodId, NectarId, CrabId]

# Type alias for poker participant (fish or plant)
PokerParticipantId = Union[FishId, PlantId]


# ============================================================================
# Conversion Helpers
# ============================================================================


def fish_id(value: int) -> FishId:
    """Convenience function to create a FishId."""
    return FishId(value)


def plant_id(value: int) -> PlantId:
    """Convenience function to create a PlantId."""
    return PlantId(value)


def food_id(value: int) -> FoodId:
    """Convenience function to create a FoodId."""
    return FoodId(value)


def nectar_id(value: int) -> NectarId:
    """Convenience function to create a NectarId."""
    return NectarId(value)


def crab_id(value: int) -> CrabId:
    """Convenience function to create a CrabId."""
    return CrabId(value)
