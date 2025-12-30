"""Centralized cache management for the simulation.

This module provides the CacheManager class which handles all entity caching
with explicit invalidation. Centralizing cache logic:
- Prevents bugs from forgetting to invalidate caches
- Makes debugging easier by logging invalidation reasons
- Provides a single point to add new caches
- Enables cache statistics for performance monitoring

Design Principles:
- Single Responsibility: Only manages caches, nothing else
- Explicit Invalidation: Caches are invalidated with a reason string
- Lazy Rebuilding: Caches are rebuilt on-demand, not eagerly
- Observable: Logs invalidations for debugging
"""

import logging
from typing import TYPE_CHECKING, Callable, Dict, Generic, List, Optional, TypeVar

if TYPE_CHECKING:
    from core import entities

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CachedList(Generic[T]):
    """A lazily-computed, invalidatable cached list.

    Wraps a list that is computed on-demand and cached until invalidated.
    Useful for expensive filtering operations like getting all fish from entities.

    Example:
        fish_cache = CachedList(
            name="fish",
            compute_fn=lambda: [e for e in entities if isinstance(e, Fish)]
        )
        fish = fish_cache.get()  # Computes and caches
        fish = fish_cache.get()  # Returns cached value
        fish_cache.invalidate("entity added")  # Clears cache
        fish = fish_cache.get()  # Recomputes
    """

    def __init__(self, name: str, compute_fn: Callable[[], List[T]]) -> None:
        """Initialize the cached list.

        Args:
            name: Human-readable name for logging
            compute_fn: Function to compute the list when cache is invalid
        """
        self._name = name
        self._compute_fn = compute_fn
        self._cached_value: Optional[List[T]] = None
        self._is_valid = False
        self._invalidation_count = 0
        self._recompute_count = 0

    def get(self) -> List[T]:
        """Get the cached list, recomputing if necessary.

        Returns:
            The cached list
        """
        if not self._is_valid or self._cached_value is None:
            self._cached_value = self._compute_fn()
            self._is_valid = True
            self._recompute_count += 1
        return self._cached_value

    def invalidate(self, reason: str = "") -> None:
        """Invalidate the cache.

        Args:
            reason: Why the cache was invalidated (for logging)
        """
        if self._is_valid:
            self._is_valid = False
            self._invalidation_count += 1
            logger.debug("Cache '%s' invalidated: %s", self._name, reason or "no reason given")

    @property
    def is_valid(self) -> bool:
        """Check if the cache is currently valid."""
        return self._is_valid

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with invalidation and recompute counts
        """
        return {
            "invalidations": self._invalidation_count,
            "recomputes": self._recompute_count,
        }


class CacheManager:
    """Centralized manager for all simulation caches.

    This class provides a single point for cache management, making it easy to:
    - Add new caches
    - Invalidate all caches at once
    - Track cache statistics
    - Debug cache-related issues

    Usage:
        cache_manager = CacheManager(entities_list)
        fish = cache_manager.get_fish()  # Cached
        cache_manager.invalidate_entity_caches("fish added")
        fish = cache_manager.get_fish()  # Recomputed
    """

    def __init__(self, get_entities_fn: Callable[[], List["entities.Agent"]]) -> None:
        """Initialize the cache manager.

        Args:
            get_entities_fn: Function to get the current entities list
        """
        self._get_entities = get_entities_fn

        # Entity type caches
        self._fish_cache: CachedList["entities.Fish"] = CachedList(
            name="fish_list",
            compute_fn=self._compute_fish_list,
        )
        self._food_cache: CachedList["entities.Food"] = CachedList(
            name="food_list",
            compute_fn=self._compute_food_list,
        )

        # Track overall invalidation count
        self._total_invalidations = 0

    def _compute_fish_list(self) -> List["entities.Fish"]:
        """Compute the fish list from entities."""
        from core import entities as entity_module

        return [e for e in self._get_entities() if isinstance(e, entity_module.Fish)]

    def _compute_food_list(self) -> List["entities.Food"]:
        """Compute the food list from entities."""
        from core import entities as entity_module

        return [e for e in self._get_entities() if isinstance(e, entity_module.Food)]

    def get_fish(self) -> List["entities.Fish"]:
        """Get cached list of fish entities.

        Returns:
            List of Fish entities
        """
        return self._fish_cache.get()

    def get_food(self) -> List["entities.Food"]:
        """Get cached list of food entities.

        Returns:
            List of Food entities
        """
        return self._food_cache.get()

    def invalidate_entity_caches(self, reason: str) -> None:
        """Invalidate all entity-type caches.

        Call this when entities are added or removed.

        Args:
            reason: Why the caches are being invalidated
        """
        self._fish_cache.invalidate(reason)
        self._food_cache.invalidate(reason)
        self._total_invalidations += 1
        logger.debug("All entity caches invalidated: %s", reason)

    def rebuild_if_needed(self) -> bool:
        """Rebuild all invalid caches.

        Call this at the end of a frame to ensure caches are warm.

        Returns:
            True if any cache was rebuilt
        """
        rebuilt = False
        if not self._fish_cache.is_valid:
            self._fish_cache.get()
            rebuilt = True
        if not self._food_cache.is_valid:
            self._food_cache.get()
            rebuilt = True
        return rebuilt

    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics for debugging.

        Returns:
            Dictionary with statistics for all caches
        """
        return {
            "total_invalidations": self._total_invalidations,
            "fish_cache": self._fish_cache.get_stats(),
            "food_cache": self._food_cache.get_stats(),
        }

    @property
    def is_dirty(self) -> bool:
        """Check if any cache needs rebuilding.

        Returns:
            True if any cache is invalid
        """
        return not self._fish_cache.is_valid or not self._food_cache.is_valid
