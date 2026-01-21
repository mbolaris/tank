"""Protocol-based entity identity provider for Tank-like worlds.

This module provides stable entity identities for simulation entities
using capability-based resolution via the Identifiable protocol and
snapshot_type property, WITHOUT importing concrete entity classes.

This provider is shared between Tank and Petri modes. It lives in the shared
namespace to avoid coupling Petri to Tank or any other specific world type.
"""

from __future__ import annotations

from typing import Any

# Entity type to ID offset mapping
# Keeps offsets centralized and avoids circular imports
_TYPE_OFFSETS: dict[str, int] = {
    "fish": 0,  # Uses FISH_ID_OFFSET (loaded lazily)
    "plant": 0,  # Uses PLANT_ID_OFFSET (loaded lazily)
    "food": 0,  # Uses FOOD_ID_OFFSET (loaded lazily)
    "plant_nectar": 0,  # Uses NECTAR_ID_OFFSET (loaded lazily)
}

_OFFSETS_LOADED = False


def _load_offsets() -> None:
    """Lazily load ID offsets from config to avoid circular imports."""
    global _OFFSETS_LOADED
    if _OFFSETS_LOADED:
        return

    from core.config.entities import (
        FISH_ID_OFFSET,
        FOOD_ID_OFFSET,
        NECTAR_ID_OFFSET,
        PLANT_ID_OFFSET,
    )

    _TYPE_OFFSETS["fish"] = FISH_ID_OFFSET
    _TYPE_OFFSETS["plant"] = PLANT_ID_OFFSET
    _TYPE_OFFSETS["food"] = FOOD_ID_OFFSET
    _TYPE_OFFSETS["plant_nectar"] = NECTAR_ID_OFFSET
    _OFFSETS_LOADED = True


class TankLikeEntityIdentityProvider:
    """Protocol-based identity provider for Tank-like entities.

    Uses capability checks instead of isinstance to determine entity identity:
    - Checks for `snapshot_type` property to determine entity type
    - Checks for `get_entity_id()` method for entities with intrinsic IDs
    - Falls back to python-id-based stable IDs for entities without intrinsic IDs

    ID offset scheme (same as legacy TankSnapshotBuilder):
    - Fish: fish_id + FISH_ID_OFFSET
    - Plant: plant_id + PLANT_ID_OFFSET
    - Food: stable counter + FOOD_ID_OFFSET
    - PlantNectar: stable counter + NECTAR_ID_OFFSET
    - Other: stable counter + 5_000_000

    Also provides reverse-lookup for mode-agnostic delta application.
    """

    # Fallback offset for unknown entity types
    OTHER_OFFSET = 5_000_000

    def __init__(self) -> None:
        # Stable ID generation for entities without intrinsic IDs
        self._entity_stable_ids: dict[int, int] = {}
        self._next_food_id: int = 0
        self._next_nectar_id: int = 0
        self._next_other_id: int = 0

        # Reverse mapping for entity lookup by stable ID
        self._stable_id_to_entity: dict[str, Any] = {}

    def stable_id(self, entity: Any) -> str:
        """Return the stable ID for an entity."""
        return self.get_identity(entity)[1]

    def type_name(self, entity: Any) -> str:
        """Return the stable type name for an entity."""
        return self.get_identity(entity)[0]

    def get_identity(self, entity: Any) -> tuple[str, str]:
        """Return (entity_type, entity_id) for any simulation entity.

        Uses protocol-based resolution:
        1. Check for `snapshot_type` property to get entity type
        2. Check for `get_entity_id()` method for intrinsic IDs
        3. Fall back to python-id-based stable IDs if no intrinsic ID

        Args:
            entity: Any entity instance from the simulation

        Returns:
            Tuple of (entity_type, entity_id) with stable IDs
        """
        _load_offsets()

        python_id = id(entity)

        # Determine entity type via protocol
        if hasattr(entity, "snapshot_type"):
            entity_type = entity.snapshot_type
        else:
            entity_type = entity.__class__.__name__.lower()

        # Try to get intrinsic ID via Identifiable protocol
        intrinsic_id: int | None = None
        if hasattr(entity, "get_entity_id"):
            intrinsic_id = entity.get_entity_id()

        # Entities with intrinsic IDs use offset scheme
        if intrinsic_id is not None:
            offset = _TYPE_OFFSETS.get(entity_type, self.OTHER_OFFSET)
            stable_id = intrinsic_id + offset
            stable_id_str = str(stable_id)
            self._stable_id_to_entity[stable_id_str] = entity
            return entity_type, stable_id_str

        # Entities without intrinsic IDs use counter-based stable IDs
        if python_id not in self._entity_stable_ids:
            if entity_type == "plant_nectar":
                offset = _TYPE_OFFSETS.get("plant_nectar", self.OTHER_OFFSET)
                self._entity_stable_ids[python_id] = self._next_nectar_id + offset
                self._next_nectar_id += 1
            elif entity_type == "food":
                offset = _TYPE_OFFSETS.get("food", self.OTHER_OFFSET)
                self._entity_stable_ids[python_id] = self._next_food_id + offset
                self._next_food_id += 1
            else:
                self._entity_stable_ids[python_id] = self._next_other_id + self.OTHER_OFFSET
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
        return self._stable_id_to_entity.get(entity_id)

    def sync_entities(self, entities: list[Any]) -> None:
        """Synchronize the reverse-lookup mapping with the entity list.

        This rebuilds the stable_id_to_entity mapping by calling get_identity
        on each entity. Should be called before batch operations that need
        reverse lookup.

        Args:
            entities: Current list of all entities in the simulation
        """
        # Clear stale mappings (entities may have been removed)
        self._stable_id_to_entity.clear()

        # Rebuild by getting identity for each entity
        # This also updates the reverse mapping as a side effect
        for entity in entities:
            self.get_identity(entity)

    def prune_stale_ids(self, current_entity_ids: set[int]) -> None:
        """Remove mappings for entities no longer present.

        This should be called periodically to prevent memory leaks
        and avoid python id() reuse corruption.

        Args:
            current_entity_ids: Set of python id() values for currently
                active entities
        """
        stale_ids = set(self._entity_stable_ids.keys()) - current_entity_ids
        for stale_id in stale_ids:
            del self._entity_stable_ids[stale_id]


# Alias for backward compatibility
TankEntityIdentityProvider = TankLikeEntityIdentityProvider
