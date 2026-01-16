"""Entity lifecycle management for the simulation.

This module handles all entity operations: creation, deletion, caching,
and pool management. Extracted from SimulationEngine to follow SRP.

Design Decisions:
-----------------
1. EntityManager owns the entities list but engine still owns the environment/ecosystem.
   The manager gets references to these via the engine.

2. Cache invalidation is automatic - the CacheManager tracks dirty state and rebuilds
   on next access.

3. Pool management (FoodPool) lives here since it's about entity lifecycle.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, List

from core import entities
from core.cache_manager import CacheManager
from core.entities.plant import Plant
from core.object_pool import FoodPool

if TYPE_CHECKING:
    import random


logger = logging.getLogger(__name__)


class EntityManager:
    """Manages entity creation, deletion, and caching.

    This class centralizes all entity lifecycle operations:
    - Adding entities (with population limit checks)
    - Removing entities (with pool returns)
    - Maintaining cached entity lists by type
    - Keeping entities within screen bounds

    Attributes:
        entities_list: The master list of all entities
        food_pool: Object pool for Food entity reuse

    Example:
        manager = EntityManager(engine)
        manager.add(new_fish)
        fish_list = manager.get_fish()
        manager.remove(dead_fish)
    """

    def __init__(
        self,
        rng: "random.Random",
        get_environment: Callable[[], Any],
        get_ecosystem: Callable[[], Any],
        get_root_spot_manager: Callable[[], Any],
    ) -> None:
        """Initialize the entity manager.

        Args:
            rng: Random number generator for deterministic behavior
            get_environment: Callable returning the Environment (deferred access)
            get_ecosystem: Callable returning the EcosystemManager (deferred access)
            get_root_spot_manager: Callable returning the RootSpotManager (deferred access)
        """
        self._entities: List[entities.Entity] = []
        self._cache_manager = CacheManager(lambda: self._entities)
        self._food_pool = FoodPool(rng=rng)

        # Deferred accessors for engine-owned resources
        self._get_environment = get_environment
        self._get_ecosystem = get_ecosystem
        self._get_root_spot_manager = get_root_spot_manager

    @property
    def entities_list(self) -> List[entities.Agent]:
        """Get the master entities list.

        Note: This returns the actual list, not a copy. This is intentional
        for valid mutation support.
        """
        return self._entities

    @property
    def food_pool(self) -> FoodPool:
        """Get the food object pool."""
        return self._food_pool

    @property
    def is_dirty(self) -> bool:
        """Check if caches need rebuilding."""
        return self._cache_manager.is_dirty

    def add(self, entity: entities.Entity) -> bool:
        """Add an entity to the simulation.

        For Fish entities, this respects population limits (max_population).
        Babies are not added if the tank is at carrying capacity.

        Args:
            entity: The entity to add

        Returns:
            True if entity was added, False if rejected (e.g., at capacity)
        """
        ecosystem = self._get_ecosystem()
        environment = self._get_environment()
        root_spot_manager = self._get_root_spot_manager()

        # Check population limit for fish
        if isinstance(entity, entities.Fish):
            fish_count = sum(1 for e in self._entities if isinstance(e, entities.Fish))
            if ecosystem and fish_count >= ecosystem.max_population:
                # At max population - reject this fish
                # The energy invested in this baby is lost (population pressure)
                return False

        # Add to internal data structures
        if hasattr(entity, "add_internal"):
            # Some entities need to register with the agents wrapper
            # This is handled by the engine's agents wrapper, not us
            pass

        self._entities.append(entity)

        # Add to spatial grid incrementally
        if environment:
            environment.add_agent_to_grid(entity)

        # Prevent future plants from spawning under blocking obstacles
        if root_spot_manager:
            root_spot_manager.block_spots_for_entity(entity, padding=10.0)

        # Invalidate cached lists
        self._cache_manager.invalidate_entity_caches("entity added")
        return True

    def remove(self, entity: entities.Agent) -> None:
        """Remove an entity from the simulation.

        Handles cleanup for different entity types:
        - Plants: releases root spots
        - Food: returns to object pool

        Args:
            entity: The entity to remove
        """
        if entity not in self._entities:
            return

        environment = self._get_environment()

        # Ensure fractal plant root spots are released even when removed externally
        if isinstance(entity, Plant):
            entity.die()

        self._entities.remove(entity)

        # Remove from spatial grid incrementally
        if environment:
            environment.remove_agent_from_grid(entity)

        # Return Food to pool for reuse
        if isinstance(entity, entities.Food):
            self._food_pool.release(entity)

        # Invalidate cached lists
        self._cache_manager.invalidate_entity_caches("entity removed")

    def get_fish(self) -> List[entities.Fish]:
        """Get cached list of all fish in the simulation.

        Returns:
            List of Fish entities, cached to avoid repeated filtering
        """
        return self._cache_manager.get_fish()

    def get_food(self) -> List[entities.Food]:
        """Get cached list of all food in the simulation.

        Returns:
            List of Food entities, cached to avoid repeated filtering
        """
        return self._cache_manager.get_food()

    def rebuild_caches_if_needed(self) -> None:
        """Rebuild all cached entity lists if they are dirty."""
        self._cache_manager.rebuild_if_needed()

    def invalidate_caches(self, reason: str = "manual") -> None:
        """Force cache invalidation.

        Args:
            reason: Description of why caches were invalidated (for debugging)
        """
        self._cache_manager.invalidate_entity_caches(reason)

    def get_all(self) -> List[entities.Agent]:
        """Get all entities in the simulation.

        Returns:
            The master entities list
        """
        return self._entities

    def clear(self) -> None:
        """Remove all entities from the simulation."""
        self._entities.clear()
        self._cache_manager.invalidate_entity_caches("cleared all")
