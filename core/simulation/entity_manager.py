"""Entity lifecycle management for the simulation.

This module handles all entity operations: creation, deletion, caching,
and pool management. Extracted from SimulationEngine to follow SRP.

Design Decisions:
-----------------
1. EntityManager owns the entities list but engine still owns the environment/ecosystem
   for backward compatibility. The manager gets references to these via the engine.

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


class MutationLockError(RuntimeError):
    """Raised when attempting to mutate entities while mutations are locked.

    This error indicates a violation of the lifecycle invariant: all spawns
    and removals must go through the lifecycle queues (request_spawn/request_remove),
    not direct mutations to the entity collection.

    To fix this error:
    1. Use engine.request_spawn(entity, reason="...") instead of direct add
    2. Use engine.request_remove(entity, reason="...") instead of direct remove
    3. The engine will apply mutations at safe points between phases
    """

    pass


class EntityManager:
    """Manages entity creation, deletion, and caching.

    This class centralizes all entity lifecycle operations:
    - Adding entities (with population limit checks)
    - Removing entities (with pool returns)
    - Maintaining cached entity lists by type
    - Keeping entities within screen bounds

    LIFECYCLE INVARIANT:
    --------------------
    During system updates (when mutation_locked=True), no system may directly
    mutate the entity collection. All spawns/removals MUST go through the
    lifecycle queues via request_spawn()/request_remove(). The engine applies
    queued mutations at safe points between phases.

    This invariant ensures:
    - Entity collection remains stable during system iteration
    - Deterministic execution order
    - No iterator invalidation bugs
    - Future game modes can rely on predictable entity state

    Attributes:
        entities_list: The master list of all entities
        food_pool: Object pool for Food entity reuse
        mutation_locked: Whether direct mutations are currently forbidden

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
        self._entities: List[entities.Agent] = []
        self._cache_manager = CacheManager(lambda: self._entities)
        self._food_pool = FoodPool(rng=rng)

        # Deferred accessors for engine-owned resources
        self._get_environment = get_environment
        self._get_ecosystem = get_ecosystem
        self._get_root_spot_manager = get_root_spot_manager

        # Mutation lock: when True, direct add/remove calls will raise
        # The engine sets this during system update phases
        self._mutation_locked: bool = False
        self._mutation_lock_phase: str = ""

    @property
    def entities_list(self) -> List[entities.Agent]:
        """Get the master entities list.

        Note: This returns the actual list, not a copy. This is intentional
        for backward compatibility - many parts of the code mutate this list.
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

    @property
    def mutation_locked(self) -> bool:
        """Check if mutations are currently locked."""
        return self._mutation_locked

    def lock_mutations(self, phase: str) -> None:
        """Lock mutations during a system update phase.

        When locked, direct add/remove calls will raise MutationLockError.
        This enforces the lifecycle invariant that all spawns/removals
        must go through the lifecycle queues.

        Args:
            phase: Name of the phase for error messages
        """
        self._mutation_locked = True
        self._mutation_lock_phase = phase

    def unlock_mutations(self) -> None:
        """Unlock mutations, allowing direct add/remove calls.

        Called by the engine when applying queued mutations or
        outside the update loop.
        """
        self._mutation_locked = False
        self._mutation_lock_phase = ""

    def _check_mutation_lock(self, operation: str) -> None:
        """Check if mutations are locked and raise if so.

        Args:
            operation: 'add' or 'remove' for the error message

        Raises:
            MutationLockError: If mutations are currently locked
        """
        if self._mutation_locked:
            raise MutationLockError(
                f"Cannot {operation} entity during {self._mutation_lock_phase} phase. "
                f"Use engine.request_spawn() or engine.request_remove() instead. "
                f"The engine will apply mutations at safe points between phases."
            )

    def add(self, entity: entities.Agent, *, _internal: bool = False) -> bool:
        """Add an entity to the simulation.

        For Fish entities, this respects population limits (max_population).
        Babies are not added if the tank is at carrying capacity.

        Args:
            entity: The entity to add
            _internal: If True, bypass mutation lock (engine use only)

        Returns:
            True if entity was added, False if rejected (e.g., at capacity)

        Raises:
            MutationLockError: If mutations are locked and _internal is False
        """
        if not _internal:
            self._check_mutation_lock("add")

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

    def remove(self, entity: entities.Agent, *, _internal: bool = False) -> None:
        """Remove an entity from the simulation.

        Handles cleanup for different entity types:
        - Plants: releases root spots
        - Food: returns to object pool

        Args:
            entity: The entity to remove
            _internal: If True, bypass mutation lock (engine use only)

        Raises:
            MutationLockError: If mutations are locked and _internal is False
        """
        if not _internal:
            self._check_mutation_lock("remove")

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
