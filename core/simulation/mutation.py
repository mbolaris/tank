"""Mutation transaction management."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from core.entities import Agent
from core.simulation.entity_manager import EntityManager
from core.simulation.entity_mutation_queue import EntityMutationQueue

if TYPE_CHECKING:
    from core.worlds.contracts import RemovalRequest, SpawnRequest


class MutationTransaction:
    """Queues spawns/removals and commits them to the entity manager."""

    def __init__(self):
        self._queue = EntityMutationQueue()

    def request_spawn(
        self,
        entity: Agent,
        *,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Queue a spawn request."""
        return self._queue.request_spawn(entity, reason=reason, metadata=metadata)

    def request_remove(
        self,
        entity: Agent,
        *,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Queue a removal request."""
        return self._queue.request_remove(entity, reason=reason, metadata=metadata)

    def is_pending_removal(self, entity: Agent) -> bool:
        """Check if entity is queued for removal."""
        return self._queue.is_pending_removal(entity)

    def pending_spawn_count(self) -> int:
        """Get count of pending spawn requests."""
        return self._queue.pending_spawn_count()

    def pending_removal_count(self) -> int:
        """Get count of pending removal requests."""
        return self._queue.pending_removal_count()

    def commit(
        self,
        entity_manager: EntityManager,
        frame_spawns: Optional[List["SpawnRequest"]] = None,
        frame_removals: Optional[List["RemovalRequest"]] = None,
        identity_provider: Optional[Any] = None,
        pre_add_callback: Optional[Any] = None,
    ) -> None:
        """Apply pending mutations to the entity manager and record outputs.

        Args:
            entity_manager: The manager to apply changes to
            frame_spawns: Optional list to record SpawnRequests to
            frame_removals: Optional list to record RemovalRequests to
            identity_provider: Provider for stable entity IDs
            pre_add_callback: Optional callback(entity) run before adding to manager
                              (used for legacy add_internal support)
        """
        # Lazy import to avoid circular dependency
        from core.worlds.contracts import RemovalRequest, SpawnRequest

        # Process removals
        removals = self._queue.drain_removals()
        for mutation in removals:
            entity = mutation.entity
            if frame_removals is not None:
                entity_type, entity_id = self._get_id(entity, identity_provider)
                frame_removals.append(
                    RemovalRequest(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        reason=mutation.reason,
                        metadata=mutation.metadata,
                    )
                )
            entity_manager.remove(entity)

        # Process spawns
        spawns = self._queue.drain_spawns()
        for mutation in spawns:
            entity = mutation.entity
            if frame_spawns is not None:
                entity_type, entity_id = self._get_id(entity, identity_provider)
                frame_spawns.append(
                    SpawnRequest(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        reason=mutation.reason,
                        metadata=mutation.metadata,
                    )
                )

            if pre_add_callback:
                pre_add_callback(entity)

            entity_manager.add(entity)

    def _get_id(self, entity: Any, provider: Optional[Any]) -> Tuple[str, str]:
        """Resolve entity identity."""
        if provider is None:
            return entity.__class__.__name__.lower(), str(id(entity))

        if hasattr(provider, "type_name") and hasattr(provider, "stable_id"):
            return str(provider.type_name(entity)), str(provider.stable_id(entity))

        identity = provider.get_identity(entity)
        return cast(Tuple[str, str], identity)
