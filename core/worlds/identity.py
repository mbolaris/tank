"""Entity identity provider protocol.

This module defines the EntityIdentityProvider protocol that allows different
world modes to provide stable entity identities for delta tracking without
coupling the SimulationEngine to specific entity types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Tuple


class EntityIdentityProvider(Protocol):
    """Provides stable identity for entities across frames.

    The SimulationEngine uses this protocol to obtain entity identity for
    delta tracking (spawns, removals, energy changes) without importing
    mode-specific entity types like Fish or Plant.

    Implementations must ensure:
    - entity_id is stable across frames (not Python id())
    - entity_type is a lowercase string identifying the entity kind
    """

    def get_identity(self, entity: Any) -> Tuple[str, str]:
        """Return (entity_type, entity_id) for any entity.

        Args:
            entity: Any entity instance from the simulation

        Returns:
            Tuple of (entity_type, entity_id) where:
            - entity_type: lowercase string like "fish", "plant", "food"
            - entity_id: stable string ID (not Python id())
        """
        ...
