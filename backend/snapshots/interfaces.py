"""Snapshot builder protocol for world-agnostic entity serialization.

This module defines the SnapshotBuilder protocol that all world-specific
snapshot builders must implement. The protocol ensures consistent entity
serialization across different world types (Tank, Petri, Soccer, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from backend.state_payloads import EntitySnapshot
    from core.worlds.interfaces import StepResult


@runtime_checkable
class SnapshotBuilder(Protocol):
    """Protocol for building frontend entity snapshots from world entities.

    Each world type (Tank, Petri, Soccer) provides its own implementation
    that knows how to convert its specific entity types to EntitySnapshot DTOs.

    The protocol ensures:
    - Consistent interface for entity serialization
    - Stable ID assignment across frames
    - Proper z-ordering for rendering

    Example:
        class PetriSnapshotBuilder:
            def collect(self, entities: Iterable[Any]) -> List[EntitySnapshot]:
                return [self.to_snapshot(e) for e in entities if e is not None]

            def to_snapshot(self, entity: Any) -> Optional[EntitySnapshot]:
                # Convert Petri-specific entities (bacteria, nutrients, etc.)
                ...
    """

    def collect(self, live_entities: Iterable[Any]) -> List["EntitySnapshot"]:
        """Collect and sort snapshots for all live entities.

        Args:
            live_entities: Iterable of entities currently in the world

        Returns:
            List of EntitySnapshot DTOs sorted by z-order for rendering
        """
        ...

    def to_snapshot(self, entity: Any) -> Optional["EntitySnapshot"]:
        """Convert a single entity to an EntitySnapshot.

        Args:
            entity: The entity to convert

        Returns:
            EntitySnapshot if conversion successful, None if entity type
            is not supported or conversion fails
        """
        ...

    def build(
        self,
        step_result: "StepResult",
        world: Any,
    ) -> List["EntitySnapshot"]:
        """Build entity snapshots from a StepResult.

        This is the preferred method for StepResult-driven worlds. It allows
        snapshot builders to access both the StepResult and the world backend.

        Args:
            step_result: The result from world.reset() or world.step()
            world: The world backend (for accessing entities_list if needed)

        Returns:
            List of EntitySnapshot DTOs sorted by z-order for rendering
        """
        ...
