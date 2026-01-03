"""Tank-specific entity identity provider.

This module provides stable entity identities for Tank world entities,
using the same ID offset scheme as TankSnapshotBuilder for consistency.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


class TankEntityIdentityProvider:
    """Identity provider for Tank entities using stable ID offsets.

    Uses the same ID scheme as TankSnapshotBuilder:
    - Fish: fish_id + FISH_ID_OFFSET
    - Plant: plant_id + PLANT_ID_OFFSET
    - Food: stable counter + FOOD_ID_OFFSET
    - PlantNectar: stable counter + NECTAR_ID_OFFSET
    - Other: stable counter + 5_000_000
    """

    def __init__(self) -> None:
        # Stable ID generation for entities without intrinsic IDs
        self._entity_stable_ids: Dict[int, int] = {}
        self._next_food_id: int = 0
        self._next_nectar_id: int = 0
        self._next_other_id: int = 0

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
            return "fish", str(stable_id)

        if isinstance(entity, Plant) and hasattr(entity, "plant_id"):
            stable_id = entity.plant_id + PLANT_ID_OFFSET
            return "plant", str(stable_id)

        if isinstance(entity, PlantNectar):
            if python_id not in self._entity_stable_ids:
                self._entity_stable_ids[python_id] = self._next_nectar_id + NECTAR_ID_OFFSET
                self._next_nectar_id += 1
            return "plant_nectar", str(self._entity_stable_ids[python_id])

        if isinstance(entity, Food):
            if python_id not in self._entity_stable_ids:
                self._entity_stable_ids[python_id] = self._next_food_id + FOOD_ID_OFFSET
                self._next_food_id += 1
            return "food", str(self._entity_stable_ids[python_id])

        # Fallback for other entity types (Crab, Castle, etc.)
        if python_id not in self._entity_stable_ids:
            self._entity_stable_ids[python_id] = self._next_other_id + 5_000_000
            self._next_other_id += 1
        return entity_type, str(self._entity_stable_ids[python_id])

    def prune_stale_ids(self, current_entity_ids: set[int]) -> None:
        """Remove mappings for entities no longer present.

        This should be called periodically to prevent memory leaks.
        """
        stale_ids = set(self._entity_stable_ids.keys()) - current_entity_ids
        for stale_id in stale_ids:
            del self._entity_stable_ids[stale_id]
