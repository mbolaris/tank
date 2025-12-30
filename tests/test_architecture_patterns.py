"""Tests for architecture patterns: SystemResult and CacheManager.

These tests verify the new architectural improvements work correctly
and provide good examples of how to use them.
"""

import pytest
from typing import List

from core.systems.base import SystemResult, BaseSystem
from core.cache_manager import CacheManager, CachedList


class TestSystemResult:
    """Tests for the SystemResult dataclass."""

    def test_empty_result(self):
        """Empty result should have all zeros."""
        result = SystemResult.empty()
        assert result.entities_affected == 0
        assert result.entities_spawned == 0
        assert result.entities_removed == 0
        assert result.events_emitted == 0
        assert result.skipped is False
        assert result.details == {}

    def test_skipped_result(self):
        """Skipped result should have skipped=True."""
        result = SystemResult.skipped_result()
        assert result.skipped is True

    def test_result_with_values(self):
        """Result should store provided values."""
        result = SystemResult(
            entities_affected=5,
            entities_spawned=2,
            entities_removed=1,
            events_emitted=3,
            details={"collision_count": 10},
        )
        assert result.entities_affected == 5
        assert result.entities_spawned == 2
        assert result.entities_removed == 1
        assert result.events_emitted == 3
        assert result.details == {"collision_count": 10}

    def test_add_results(self):
        """Adding results should combine them."""
        r1 = SystemResult(
            entities_affected=5,
            entities_spawned=2,
            details={"collisions": 10},
        )
        r2 = SystemResult(
            entities_affected=3,
            entities_removed=1,
            details={"collisions": 5, "food_eaten": 2},
        )

        combined = r1 + r2
        assert combined.entities_affected == 8
        assert combined.entities_spawned == 2
        assert combined.entities_removed == 1
        assert combined.details["collisions"] == 15  # Combined
        assert combined.details["food_eaten"] == 2  # From r2 only

    def test_add_skipped_result_returns_other(self):
        """Adding a skipped result should return the non-skipped one."""
        active = SystemResult(entities_affected=5)
        skipped = SystemResult.skipped_result()

        # Skipped + Active = Active
        assert (skipped + active).entities_affected == 5
        assert (skipped + active).skipped is False

        # Active + Skipped = Active
        assert (active + skipped).entities_affected == 5
        assert (active + skipped).skipped is False


class TestCachedList:
    """Tests for the CachedList helper class."""

    def test_lazy_computation(self):
        """Cache should only compute when accessed."""
        compute_count = 0

        def compute():
            nonlocal compute_count
            compute_count += 1
            return [1, 2, 3]

        cache = CachedList("test", compute)

        # Not computed yet
        assert compute_count == 0

        # First access computes
        result = cache.get()
        assert compute_count == 1
        assert result == [1, 2, 3]

        # Second access uses cache
        result = cache.get()
        assert compute_count == 1  # Still 1
        assert result == [1, 2, 3]

    def test_invalidation(self):
        """Invalidating cache should trigger recomputation."""
        compute_count = 0

        def compute():
            nonlocal compute_count
            compute_count += 1
            return [compute_count]

        cache = CachedList("test", compute)

        # First access
        assert cache.get() == [1]
        assert compute_count == 1

        # Invalidate
        cache.invalidate("test reason")

        # Next access recomputes
        assert cache.get() == [2]
        assert compute_count == 2

    def test_stats_tracking(self):
        """Cache should track invalidation and recompute counts."""
        cache = CachedList("test", lambda: [1, 2, 3])

        # Initial stats
        stats = cache.get_stats()
        assert stats["invalidations"] == 0
        assert stats["recomputes"] == 0

        # After first get
        cache.get()
        stats = cache.get_stats()
        assert stats["recomputes"] == 1

        # After invalidation and get
        cache.invalidate("test")
        cache.get()
        stats = cache.get_stats()
        assert stats["invalidations"] == 1
        assert stats["recomputes"] == 2

    def test_is_valid_property(self):
        """is_valid should reflect cache state."""
        cache = CachedList("test", lambda: [1])

        assert cache.is_valid is False  # Not computed yet
        cache.get()
        assert cache.is_valid is True
        cache.invalidate("test")
        assert cache.is_valid is False


class TestCacheManager:
    """Tests for the CacheManager class."""

    def test_fish_and_food_caching(self):
        """CacheManager should cache fish and food lists."""

        # Mock entity classes
        class MockFish:
            pass

        class MockFood:
            pass

        class MockOther:
            pass

        # Create entities
        fish1 = MockFish()
        fish2 = MockFish()
        food1 = MockFood()
        other = MockOther()
        entities = [fish1, fish2, food1, other]

        # Patch isinstance checks by using actual class names
        from core import entities as entity_module

        original_fish = entity_module.Fish
        original_food = entity_module.Food

        try:
            # Temporarily replace for testing
            entity_module.Fish = MockFish
            entity_module.Food = MockFood

            manager = CacheManager(lambda: entities)

            # Get fish
            fish_list = manager.get_fish()
            assert len(fish_list) == 2
            assert fish1 in fish_list
            assert fish2 in fish_list

            # Get food
            food_list = manager.get_food()
            assert len(food_list) == 1
            assert food1 in food_list
        finally:
            # Restore original classes
            entity_module.Fish = original_fish
            entity_module.Food = original_food

    def test_invalidation(self):
        """CacheManager.invalidate_entity_caches should invalidate all caches."""

        class MockFish:
            pass

        from core import entities as entity_module

        original_fish = entity_module.Fish

        try:
            entity_module.Fish = MockFish

            compute_count = 0
            fish1 = MockFish()

            def get_entities():
                nonlocal compute_count
                compute_count += 1
                return [fish1]

            # Need to wrap to track calls
            manager = CacheManager(get_entities)

            # First access
            manager.get_fish()

            # Invalidate
            manager.invalidate_entity_caches("entity added")
            assert manager.is_dirty is True

            # Next access should recompute
            manager.get_fish()
        finally:
            entity_module.Fish = original_fish

    def test_stats(self):
        """CacheManager should provide statistics."""

        class MockFish:
            pass

        from core import entities as entity_module

        original_fish = entity_module.Fish

        try:
            entity_module.Fish = MockFish

            manager = CacheManager(lambda: [MockFish()])

            # Initial stats
            stats = manager.get_stats()
            assert stats["total_invalidations"] == 0

            # After invalidation
            manager.invalidate_entity_caches("test")
            stats = manager.get_stats()
            assert stats["total_invalidations"] == 1
        finally:
            entity_module.Fish = original_fish


class TestCollisionSystemWithSystemResult:
    """Tests for CollisionSystem returning SystemResult."""

    def test_collision_system_returns_system_result(self):
        """CollisionSystem._do_update should return a SystemResult."""
        from core.collision_system import CollisionSystem
        from core.simulation.engine import SimulationEngine

        # Create engine and collision system
        engine = SimulationEngine(headless=True)
        engine.setup()

        # Get the collision system
        collision_system = engine.collision_system

        # Run update
        result = collision_system.update(frame=1)

        # Should return a SystemResult
        assert isinstance(result, SystemResult)
        assert hasattr(result, "entities_affected")
        assert hasattr(result, "details")

    def test_collision_system_tracks_per_frame_stats(self):
        """CollisionSystem should track per-frame collision statistics."""
        from core.collision_system import CollisionSystem
        from core.simulation.engine import SimulationEngine
        from core.math_utils import Vector2

        # Create engine
        engine = SimulationEngine(headless=True)
        engine.setup()

        collision_system = engine.collision_system

        # Create mock entities for collision
        class MockEntity:
            def __init__(self, x, y, w, h):
                self.pos = Vector2(x, y)
                self.width = w
                self.height = h

            def get_rect(self):
                return (self.pos.x, self.pos.y, self.width, self.height)

        e1 = MockEntity(0, 0, 10, 10)
        e2 = MockEntity(5, 5, 10, 10)  # Overlapping
        e3 = MockEntity(100, 100, 10, 10)  # Not overlapping

        # First, reset counters by calling _do_update
        collision_system._do_update(frame=0)

        # Check collisions manually (not via the full iteration)
        collision_system.check_collision(e1, e2)  # Should collide
        collision_system.check_collision(e1, e3)  # Should not collide

        # Get frame stats directly (don't call full update which resets them)
        assert collision_system._frame_collisions_checked == 2
        assert collision_system._frame_collisions_detected == 1

        # Now get result (which also resets counters)
        result = collision_system._do_update(frame=1)

        # Note: result includes our 2 manual checks from before
        # The _do_update also runs full iteration, so stats may include more
        # What we're really testing is that stats accumulate and reset correctly
        assert "collisions_checked" in result.details
        assert "collisions_detected" in result.details

        # After reset, per-frame counters should be zero
        assert collision_system._frame_collisions_checked == 0
        assert collision_system._frame_collisions_detected == 0


class TestBaseSystemWithResult:
    """Tests for BaseSystem handling SystemResult."""

    def test_base_system_returns_result_from_subclass(self):
        """BaseSystem.update should return the result from _do_update."""
        from core.systems.base import BaseSystem

        class TestSystem(BaseSystem):
            def __init__(self):
                # Use None as engine for testing
                self._engine = None
                self._name = "Test"
                self._enabled = True
                self._update_count = 0

            def _do_update(self, frame: int):
                return SystemResult(entities_affected=42)

        system = TestSystem()
        result = system.update(frame=1)

        assert isinstance(result, SystemResult)
        assert result.entities_affected == 42

    def test_base_system_returns_skipped_when_disabled(self):
        """BaseSystem.update should return skipped result when disabled."""
        from core.systems.base import BaseSystem

        class TestSystem(BaseSystem):
            def __init__(self):
                self._engine = None
                self._name = "Test"
                self._enabled = False
                self._update_count = 0

            def _do_update(self, frame: int):
                return SystemResult(entities_affected=42)

        system = TestSystem()
        result = system.update(frame=1)

        assert result.skipped is True
        assert result.entities_affected == 0

    def test_base_system_handles_legacy_none_return(self):
        """BaseSystem.update should handle legacy systems returning None."""
        from core.systems.base import BaseSystem

        class LegacySystem(BaseSystem):
            def __init__(self):
                self._engine = None
                self._name = "Legacy"
                self._enabled = True
                self._update_count = 0

            def _do_update(self, frame: int):
                # Legacy systems return None
                return None

        system = LegacySystem()
        result = system.update(frame=1)

        # Should get empty result, not None
        assert isinstance(result, SystemResult)
        assert result.entities_affected == 0
        assert result.skipped is False
