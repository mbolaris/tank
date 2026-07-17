"""Entity collection wrapper for simulation entities.

This module provides a wrapper class that manages entity collections,
supporting both raw lists (for testing) and engine-aware management
that keeps spatial grids and caches in sync.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableSequence
from typing import TYPE_CHECKING, Protocol, TypeGuard

if TYPE_CHECKING:
    from core.entities.base import Entity


class _EntityBackedEngine(Protocol):
    """Minimal engine surface needed for entity collection management."""

    @property
    def entities_list(self) -> list[Entity]: ...

    def add_entity(self, entity: Entity) -> None: ...

    def remove_entity(self, entity: Entity) -> None: ...


def _is_entity_backed_engine(value: object) -> TypeGuard[_EntityBackedEngine]:
    return hasattr(value, "_entity_manager") and hasattr(value, "entities_list")


def _is_entity_sequence(value: object) -> TypeGuard[MutableSequence[Entity]]:
    return isinstance(value, MutableSequence)


class AgentsWrapper:
    """Wrapper to provide a group-like API for managing entities.

    The wrapper can be initialized with either a raw list of entities
    (for simple, isolated tests) or a SimulationEngine instance to
    ensure adds/removals stay in sync with spatial grids and caches.

    Architecture Note:
        This class abstracts entity collection management, allowing
        test code to use simple lists while production code maintains
        spatial indexing consistency.
    """

    def __init__(self, entities_or_engine: object) -> None:
        """Initialize the wrapper.

        Args:
            entities_or_engine: Either a list of entities (for testing)
                or a SimulationEngine instance (for production use)
        """
        # Support both list usage (for tests) and engine-aware management
        # Check for _entity_manager to detect SimulationEngine
        self._engine: _EntityBackedEngine | None
        if _is_entity_backed_engine(entities_or_engine):
            self._engine = entities_or_engine
            self._entities: MutableSequence[Entity] = entities_or_engine.entities_list
        elif _is_entity_sequence(entities_or_engine):
            self._engine = None
            self._entities = entities_or_engine
        else:
            raise TypeError("AgentsWrapper requires an entity list or SimulationEngine")

    def add(self, *entities: Entity) -> None:
        """Add entities to the list or engine-aware collection.

        When backed by an engine, uses the public add_entity() API which
        enforces phase safety (will raise if called during update phases).
        """
        for entity in entities:
            if entity in self._entities:
                entity.add_internal(self)
                continue

            if self._engine is not None:
                self._engine.add_entity(entity)
            else:
                self._entities.append(entity)
            entity.add_internal(self)

    def remove(self, *entities: Entity) -> None:
        """Remove entities from the list or engine-aware collection.

        When backed by an engine, uses the public remove_entity() API which
        enforces phase safety (will raise if called during update phases).
        """
        for entity in entities:
            if entity not in self._entities:
                continue
            if self._engine is not None:
                self._engine.remove_entity(entity)
            else:
                self._entities.remove(entity)

    def empty(self) -> None:
        """Remove all entities from the collection."""
        for entity in list(self._entities):
            self.remove(entity)

    def __contains__(self, entity: object) -> bool:
        """Check if entity is in the collection."""
        return entity in self._entities

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over entities."""
        return iter(self._entities)

    def __len__(self) -> int:
        """Get number of entities."""
        return len(self._entities)
