"""Tests for protocol-based identity resolution in TankLikeEntityIdentityProvider.

This test verifies that the identity provider works correctly using
capability-based resolution (snapshot_type and get_entity_id) without
importing concrete entity classes like Fish, Plant, etc.
"""

from __future__ import annotations

from core.config.entities import FISH_ID_OFFSET, FOOD_ID_OFFSET, PLANT_ID_OFFSET
from core.worlds.shared.identity import TankLikeEntityIdentityProvider


class MockGenericAgent:
    """Mock agent with Identifiable protocol (get_entity_id + snapshot_type)."""

    def __init__(self, agent_id: int, snapshot_type: str = "mock_agent"):
        self._agent_id = agent_id
        self._snapshot_type = snapshot_type

    def get_entity_id(self) -> int | None:
        return self._agent_id if self._agent_id != 0 else None

    @property
    def snapshot_type(self) -> str:
        return self._snapshot_type


class MockEntityNoId:
    """Mock entity without intrinsic ID (like Food)."""

    @property
    def snapshot_type(self) -> str:
        return "food"

    def get_entity_id(self) -> int | None:
        return None


class MockEntityNoIdOrType:
    """Mock entity with snapshot_type but no get_entity_id at all (like Ball)."""

    def __init__(self, snapshot_type: str):
        self._snapshot_type = snapshot_type

    @property
    def snapshot_type(self) -> str:
        return self._snapshot_type


class MockEntityNoProtocol:
    """Mock entity with neither get_entity_id nor snapshot_type."""

    pass


def test_identity_provider_uses_get_entity_id():
    """Verify identity provider uses get_entity_id for stable IDs."""
    provider = TankLikeEntityIdentityProvider()

    agent = MockGenericAgent(agent_id=42, snapshot_type="fish")
    entity_type, entity_id = provider.get_identity(agent)

    # Should use fish type and fish_id + offset
    assert entity_type == "fish"
    assert entity_id == str(42 + FISH_ID_OFFSET)


def test_identity_provider_uses_snapshot_type():
    """Verify identity provider uses snapshot_type property."""
    provider = TankLikeEntityIdentityProvider()

    agent = MockGenericAgent(agent_id=7, snapshot_type="plant")
    entity_type, entity_id = provider.get_identity(agent)

    assert entity_type == "plant"
    assert entity_id == str(7 + PLANT_ID_OFFSET)


def test_identity_provider_falls_back_to_counter_for_no_id():
    """Verify entities without intrinsic IDs get stable counter-based IDs."""
    provider = TankLikeEntityIdentityProvider()

    food1 = MockEntityNoId()
    food2 = MockEntityNoId()

    type1, id1 = provider.get_identity(food1)
    type2, id2 = provider.get_identity(food2)

    # Should use food type
    assert type1 == "food"
    assert type2 == "food"

    # Should use counter-based IDs with FOOD_ID_OFFSET
    assert int(id1) >= FOOD_ID_OFFSET
    assert int(id2) >= FOOD_ID_OFFSET
    assert id1 != id2  # Different entities get different IDs


def test_identity_provider_stable_across_calls():
    """Verify the same entity gets the same ID on repeated calls."""
    provider = TankLikeEntityIdentityProvider()

    food = MockEntityNoId()

    _, id1 = provider.get_identity(food)
    _, id2 = provider.get_identity(food)
    _, id3 = provider.get_identity(food)

    assert id1 == id2 == id3


def test_identity_provider_falls_back_to_classname():
    """Verify entities without snapshot_type use class name."""
    provider = TankLikeEntityIdentityProvider()

    entity = MockEntityNoProtocol()
    entity_type, _ = provider.get_identity(entity)

    # Should fall back to lowercase class name
    assert entity_type == "mockentitynoprotocol"


def test_identity_provider_reverse_lookup():
    """Verify get_entity_by_id returns correct entity."""
    provider = TankLikeEntityIdentityProvider()

    agent = MockGenericAgent(agent_id=99, snapshot_type="fish")
    _, entity_id = provider.get_identity(agent)

    # Reverse lookup should return the same entity
    found = provider.get_entity_by_id(entity_id)
    assert found is agent


def test_tank_objects_and_soccer_objects_never_share_an_id():
    """Regression: intrinsic-id and counter-based entities used one 5M range.

    ``algae_reef`` (object_id 1) and the ball both resolved to 5_000_001, so the
    reef rendered wherever the ball was.  The two allocators must not overlap.
    """
    provider = TankLikeEntityIdentityProvider()

    # Tank objects carry an intrinsic object_id starting at 1.
    tank_object_ids = {
        provider.get_identity(MockGenericAgent(agent_id=i, snapshot_type=kind))[1]
        for i, kind in enumerate(("algae_reef", "decorative_rock", "castle"), start=1)
    }
    # Ball / goal zones have no intrinsic id and are numbered by arrival order.
    soccer_ids = {
        provider.get_identity(MockEntityNoIdOrType(kind))[1]
        for kind in ("ball", "goal_zone", "goal_zone")
    }

    assert len(tank_object_ids) == 3
    assert not tank_object_ids & soccer_ids


def test_anonymous_entities_use_their_own_offset():
    """Counter-based 'other' entities live above ANON_OFFSET, not OTHER_OFFSET."""
    provider = TankLikeEntityIdentityProvider()

    _, entity_id = provider.get_identity(MockEntityNoIdOrType("ball"))

    assert int(entity_id) >= TankLikeEntityIdentityProvider.ANON_OFFSET


def test_identity_provider_no_fish_import():
    """Verify identity provider works without importing Fish class."""
    # This test verifies the core design goal: identity resolution
    # should work purely through protocols without concrete type imports

    # Inspect the module's imports
    import core.worlds.shared.identity as identity_module

    # Should not have Fish, Plant, Food, PlantNectar in module namespace
    module_names = dir(identity_module)
    assert "Fish" not in module_names
    assert "Plant" not in module_names
    assert "Food" not in module_names
    assert "PlantNectar" not in module_names
