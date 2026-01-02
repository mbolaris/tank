"""Tests for the filter_mutually_proximate utility function.

This function is used by CollisionSystem and PokerSystem to ensure
poker game participants are all within mutual proximity (no chain connections).
"""

from types import SimpleNamespace

from core.poker_interaction import filter_mutually_proximate


class MockEntity:
    """Mock entity with pos, width, height for testing proximity filtering."""

    def __init__(self, x: float, y: float, size: float = 20.0):
        self.pos = SimpleNamespace(x=x, y=y)
        self.width = size
        self.height = size


class TestFilterMutuallyProximate:
    """Tests for the filter_mutually_proximate function."""

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        result = filter_mutually_proximate([], 100.0)
        assert result == []

    def test_single_entity_returns_same(self):
        """Single entity is returned unchanged."""
        entity = MockEntity(0, 0)
        result = filter_mutually_proximate([entity], 100.0)
        assert result == [entity]

    def test_two_entities_within_distance_returns_both(self):
        """Two entities within max_distance are both returned."""
        e1 = MockEntity(0, 0)
        e2 = MockEntity(30, 0)  # 30 units apart (center to center = 30)
        result = filter_mutually_proximate([e1, e2], 50.0)
        assert len(result) == 2
        assert e1 in result
        assert e2 in result

    def test_two_entities_returns_both_regardless_of_distance(self):
        """Two entities are returned unchanged (assumes pre-verified).

        The filter_mutually_proximate function is designed to be called after
        initial proximity verification. For <= 2 entities, it returns them
        unchanged since there's no "chain connection" issue possible.
        """
        e1 = MockEntity(0, 0)
        e2 = MockEntity(100, 0)  # Distance doesn't matter for n <= 2
        result = filter_mutually_proximate([e1, e2], 50.0)
        # Returns both - caller is responsible for initial proximity check
        assert len(result) == 2

    def test_chain_connection_filters_outlier(self):
        """Chain-connected entities (A-B-C where A far from C) exclude outlier.

        This is the key scenario: A is near B, B is near C, but A is far from C.
        The algorithm should exclude one end of the chain.
        """
        # A at (0,0), B at (40,0), C at (80,0)
        # Distance A-B = 40, B-C = 40, but A-C = 80
        # With max_distance = 50, A-B and B-C are OK, but A-C is not
        a = MockEntity(0, 0)
        b = MockEntity(40, 0)
        c = MockEntity(80, 0)

        result = filter_mutually_proximate([a, b, c], 50.0)

        # Should return at most 2 entities (the largest mutually proximate subset)
        assert len(result) <= 2

        # If B is in result, at most one of A or C should be included
        if b in result:
            a_in_result = a in result
            c_in_result = c in result
            assert not (a_in_result and c_in_result), "A and C should not both be in result"

    def test_all_mutually_proximate_returns_all(self):
        """When all entities are mutually within distance, all are returned."""
        # Triangle formation, all within 50 of each other
        e1 = MockEntity(0, 0)
        e2 = MockEntity(30, 0)
        e3 = MockEntity(15, 26)  # Equilateral-ish triangle

        result = filter_mutually_proximate([e1, e2, e3], 50.0)
        assert len(result) == 3

    def test_finds_largest_mutually_proximate_subset(self):
        """Algorithm finds the largest valid subset."""
        # Create 4 entities: 3 clustered together, 1 far away
        cluster = [MockEntity(0, 0), MockEntity(20, 0), MockEntity(10, 17)]
        outlier = MockEntity(200, 200)

        all_entities = cluster + [outlier]
        result = filter_mutually_proximate(all_entities, 50.0)

        # Should return the 3 clustered entities
        assert len(result) == 3
        for e in cluster:
            assert e in result
        assert outlier not in result

    def test_preserves_order_when_possible(self):
        """Result preserves relative order of input entities."""
        e1 = MockEntity(0, 0)
        e2 = MockEntity(10, 0)
        e3 = MockEntity(20, 0)

        result = filter_mutually_proximate([e1, e2, e3], 100.0)

        # All within distance, should preserve order
        assert result == [e1, e2, e3]
