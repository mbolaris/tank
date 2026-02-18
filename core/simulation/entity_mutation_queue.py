"""Queue for entity spawn/removal requests during a simulation tick.

This queue centralizes mutation requests so systems never mutate the
entity collection mid-phase. The engine decides when to apply mutations.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from core.entities import Agent


@dataclass(frozen=True)
class EntityMutation:
    """Record a requested entity mutation."""

    entity: "Agent"
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class EntityMutationQueue:
    """Collects entity spawn/removal requests for deferred application."""

    def __init__(self) -> None:
        self._pending_spawns: list[EntityMutation] = []
        self._pending_removals: list[EntityMutation] = []
        self._spawn_ids: set[int] = set()
        self._removal_ids: set[int] = set()

    def request_spawn(
        self,
        entity: "Agent",
        *,
        reason: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Queue an entity spawn request.

        Returns False if the entity is already queued for spawn or removal.
        """
        entity_id = id(entity)
        if entity_id in self._removal_ids or entity_id in self._spawn_ids:
            return False
        self._spawn_ids.add(entity_id)
        self._pending_spawns.append(
            EntityMutation(entity=entity, reason=reason, metadata=metadata or {})
        )
        return True

    def request_remove(
        self,
        entity: "Agent",
        *,
        reason: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Queue an entity removal request.

        If the entity is already queued to spawn, the spawn is dropped.
        """
        entity_id = id(entity)
        if entity_id in self._removal_ids:
            return False

        if entity_id in self._spawn_ids:
            self._drop_spawn(entity_id)

        self._removal_ids.add(entity_id)
        self._pending_removals.append(
            EntityMutation(entity=entity, reason=reason, metadata=metadata or {})
        )
        return True

    def _drop_spawn(self, entity_id: int) -> None:
        """Remove a pending spawn entry by entity id."""
        self._spawn_ids.discard(entity_id)
        self._pending_spawns = [
            mutation for mutation in self._pending_spawns if id(mutation.entity) != entity_id
        ]

    def drain_spawns(self) -> list[EntityMutation]:
        """Return and clear pending spawns."""
        spawns = self._pending_spawns
        self._pending_spawns = []
        self._spawn_ids.clear()
        return spawns

    def drain_removals(self) -> list[EntityMutation]:
        """Return and clear pending removals."""
        removals = self._pending_removals
        self._pending_removals = []
        self._removal_ids.clear()
        return removals

    def is_pending_removal(self, entity: "Agent") -> bool:
        """Check if entity is queued for removal."""
        return id(entity) in self._removal_ids

    def pending_spawn_count(self) -> int:
        """Get count of pending spawn requests."""
        return len(self._pending_spawns)

    def pending_removal_count(self) -> int:
        """Get count of pending removal requests."""
        return len(self._pending_removals)
