"""Entity collection wrapper for simulation entities.

This module provides a wrapper class that manages entity collections,
supporting both raw lists (for testing) and engine-aware management
that keeps spatial grids and caches in sync.
"""

from typing import Any, Iterator, List


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

    def __init__(self, entities_or_engine: Any) -> None:
        """Initialize the wrapper.

        Args:
            entities_or_engine: Either a list of entities (for testing)
                or a SimulationEngine instance (for production use)
        """
        # Support both legacy list usage and engine-aware management
        # Check for _entity_manager to detect SimulationEngine
        if hasattr(entities_or_engine, "_entity_manager") and hasattr(
            entities_or_engine, "entities_list"
        ):
            self._engine = entities_or_engine
            self._entities: List[Any] = entities_or_engine.entities_list
        else:
            self._engine = None
            self._entities = entities_or_engine

    def add(self, *entities: Any) -> None:
        """Add entities to the list or engine-aware collection.

        When connected to an engine, this delegates to the EntityManager
        which will enforce the mutation lock during the update loop.
        Use engine.request_spawn() instead if you need to add entities
        during system updates.
        """
        for entity in entities:
            if entity in self._entities:
                if hasattr(entity, "add_internal"):
                    entity.add_internal(self)
                continue

            if self._engine is not None:
                # EntityManager.add() will check mutation lock
                self._engine._entity_manager.add(entity)
            else:
                self._entities.append(entity)
            if hasattr(entity, "add_internal"):
                entity.add_internal(self)

    def remove(self, *entities: Any) -> None:
        """Remove entities from the list or engine-aware collection.

        When connected to an engine, this delegates to the EntityManager
        which will enforce the mutation lock during the update loop.
        Use engine.request_remove() instead if you need to remove entities
        during system updates.
        """
        for entity in entities:
            if entity not in self._entities:
                continue
            if self._engine is not None:
                # EntityManager.remove() will check mutation lock
                self._engine._entity_manager.remove(entity)
            else:
                self._entities.remove(entity)

    def empty(self) -> None:
        """Remove all entities from the collection."""
        for entity in list(self._entities):
            self.remove(entity)

    def __contains__(self, entity: Any) -> bool:
        """Check if entity is in the collection."""
        return entity in self._entities

    def __iter__(self) -> Iterator[Any]:
        """Iterate over entities."""
        return iter(self._entities)

    def __len__(self) -> int:
        """Get number of entities."""
        return len(self._entities)
