"""Tank-specific entity identity provider.

This module provides stable entity identities for Tank world entities,
using the same ID offset scheme as TankSnapshotBuilder for consistency.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class TankEntityIdentityProvider:
    """Identity provider for Tank entities using stable ID offsets.

    Uses the same ID scheme as TankSnapshotBuilder:
    - Fish: fish_id + FISH_ID_OFFSET
    - Plant: plant_id + PLANT_ID_OFFSET
    - Food: stable counter + FOOD_ID_OFFSET
    - PlantNectar: stable counter + NECTAR_ID_OFFSET
    - Other: stable counter + 5_000_000

    Also provides reverse-lookup for mode-agnostic delta application.
    """

    def __init__(self) -> None:
        # Stable ID generation for entities without intrinsic IDs
        self._entity_stable_ids: Dict[int, int] = {}
        self._next_food_id: int = 0
        self._next_nectar_id: int = 0
        self._next_other_id: int = 0
        
        # Reverse mapping for entity lookup by stable ID
        self._stable_id_to_entity: Dict[str, Any] = {}
        # Legacy ID lookup (fish_id, plant_id) for backward compatibility
        self._legacy_id_to_entity: Dict[str, Any] = {}

    def stable_id(self, entity: Any) -> str:
        """Return the stable ID for an entity."""
        return self.get_identity(entity)[1]

    def type_name(self, entity: Any) -> str:
        """Return the stable type name for an entity."""
        return self.get_identity(entity)[0]

    def get_identity(self, entity: Any) -> Tuple[str, str]:
        """Return (entity_type, entity_id) for any Tank entity.

        Args:
            entity: Any entity instance from the Tank simulation

        Returns:
            Tuple of (entity_type, entity_id) with stable IDs
        """
        from core.config.entities import (
            FISH_ID_OFFSET,
            FOOD_ID_OFFSET,
            NECTAR_ID_OFFSET,
            PLANT_ID_OFFSET,
        )
        from core.entities import Fish, Food
        from core.entities.plant import Plant, PlantNectar

        python_id = id(entity)
        entity_type = entity.__class__.__name__.lower()

        if isinstance(entity, Fish) and hasattr(entity, "fish_id"):
            stable_id = entity.fish_id + FISH_ID_OFFSET
            stable_id_str = str(stable_id)
            self._stable_id_to_entity[stable_id_str] = entity
            self._legacy_id_to_entity[str(entity.fish_id)] = entity
            return "fish", stable_id_str

        if isinstance(entity, Plant) and hasattr(entity, "plant_id"):
            stable_id = entity.plant_id + PLANT_ID_OFFSET
            stable_id_str = str(stable_id)
            self._stable_id_to_entity[stable_id_str] = entity
            self._legacy_id_to_entity[str(entity.plant_id)] = entity
            return "plant", stable_id_str

        if isinstance(entity, PlantNectar):
            if python_id not in self._entity_stable_ids:
                self._entity_stable_ids[python_id] = self._next_nectar_id + NECTAR_ID_OFFSET
                self._next_nectar_id += 1
            stable_id_str = str(self._entity_stable_ids[python_id])
            self._stable_id_to_entity[stable_id_str] = entity
            return "plant_nectar", stable_id_str

        if isinstance(entity, Food):
            if python_id not in self._entity_stable_ids:
                self._entity_stable_ids[python_id] = self._next_food_id + FOOD_ID_OFFSET
                self._next_food_id += 1
            stable_id_str = str(self._entity_stable_ids[python_id])
            self._stable_id_to_entity[stable_id_str] = entity
            return "food", stable_id_str

        # Fallback for other entity types (Crab, Castle, etc.)
        if python_id not in self._entity_stable_ids:
            self._entity_stable_ids[python_id] = self._next_other_id + 5_000_000
            self._next_other_id += 1
        stable_id_str = str(self._entity_stable_ids[python_id])
        self._stable_id_to_entity[stable_id_str] = entity
        return entity_type, stable_id_str

    def get_entity_by_id(self, entity_id: str) -> Any | None:
        """Lookup an entity by its stable ID.

        Args:
            entity_id: Stable entity ID (as returned by get_identity)

        Returns:
            The entity instance, or None if not found
        """
        entity = self._stable_id_to_entity.get(entity_id)
        if entity is not None:
            return entity
        return self._legacy_id_to_entity.get(entity_id)

    def sync_entities(self, entities: List[Any]) -> None:
        """Synchronize the reverse-lookup mapping with the entity list.

        This rebuilds the stable_id_to_entity mapping by calling get_identity
        on each entity. Should be called before batch operations that need
        reverse lookup.

        Args:
            entities: Current list of all entities in the simulation
        """
        # Clear stale mappings (entities may have been removed)
        self._stable_id_to_entity.clear()
        self._legacy_id_to_entity.clear()
        
        # Rebuild by getting identity for each entity
        # This also updates the reverse mapping as a side effect
        for entity in entities:
            self.get_identity(entity)

    def prune_stale_ids(self, current_entity_ids: set[int]) -> None:
        """Remove mappings for entities no longer present.

        This should be called periodically to prevent memory leaks.
        """
        stale_ids = set(self._entity_stable_ids.keys()) - current_entity_ids
        for stale_id in stale_ids:
            del self._entity_stable_ids[stale_id]

