"""Test crab save/restore persistence.

Verifies that the crab entity is correctly serialized and deserialized
during snapshot save/restore operations.
"""

from __future__ import annotations

import pytest

from backend.world_persistence import restore_world_from_snapshot
from core.entities.predators import Crab
from core.tank_world import TankWorld, TankWorldConfig


def _make_world(seed: int) -> TankWorld:
    """Create a headless TankWorld for testing."""
    world = TankWorld(config=TankWorldConfig(headless=True), seed=seed)
    world.setup()
    return world


def test_crab_persistence_preserves_state() -> None:
    """Test that crab energy and cooldown are preserved across save/restore."""
    # Create source world
    source = _make_world(seed=200)

    # Clear default entities to start fresh
    source.engine.entities_list.clear()

    # Create a crab with modified state
    crab = Crab(
        environment=source.engine.environment,
        x=150,
        y=500,
    )
    # Mutate state to non-default values
    crab.energy = 50.0  # Non-default energy
    crab.hunt_cooldown = 15  # Non-zero cooldown
    source.engine.add_entity(crab)

    # Build snapshot using the transfer codec
    from core.transfer.entity_transfer import serialize_entity_for_transfer

    crab_data = serialize_entity_for_transfer(crab)

    assert crab_data is not None, "Crab should be serializable"
    assert crab_data["type"] == "crab"
    assert crab_data["energy"] == 50.0
    assert crab_data["hunt_cooldown"] == 15
    assert "genome_data" in crab_data, "Should include full genome_data"
    assert "motion" in crab_data, "Should include motion state"

    # Now test restore
    snapshot = {
        "tank_id": "test-crab-tank",
        "frame": 100,
        "entities": [crab_data],
    }

    dest = _make_world(seed=201)
    # Clear default entities
    dest.engine.entities_list.clear()

    assert restore_world_from_snapshot(snapshot, dest) is True

    # Find restored crab
    restored_crabs = [e for e in dest.engine.entities_list if isinstance(e, Crab)]
    assert len(restored_crabs) == 1, "Should restore exactly 1 crab"

    restored = restored_crabs[0]
    # Energy should be preserved (potentially clamped to max_energy)
    assert restored.energy <= restored.max_energy
    assert restored.energy == pytest.approx(50.0, rel=0.1) or restored.energy == restored.max_energy
    assert restored.hunt_cooldown == 15


def test_crab_restore_from_legacy_format() -> None:
    """Test backward compatibility with legacy crab snapshots (minimal genome)."""
    # Simulate legacy format (no genome_data, only minimal genome dict)
    legacy_crab_data = {
        "type": "crab",
        "x": 100,
        "y": 450,
        "energy": 80.0,
        "max_energy": 100.0,
        "hunt_cooldown": 5,
        "genome": {
            "size_modifier": 1.2,
            "color_hue": 0.7,
        },
    }

    snapshot = {
        "tank_id": "legacy-crab-tank",
        "frame": 50,
        "entities": [legacy_crab_data],
    }

    dest = _make_world(seed=202)
    dest.engine.entities_list.clear()

    assert restore_world_from_snapshot(snapshot, dest) is True

    restored_crabs = [e for e in dest.engine.entities_list if isinstance(e, Crab)]
    assert len(restored_crabs) == 1, "Should restore crab from legacy format"

    restored = restored_crabs[0]
    assert restored.pos.x == pytest.approx(100, abs=1)
    assert restored.hunt_cooldown == 5
    # Legacy genome values should be applied
    assert restored.genome.physical.size_modifier.value == pytest.approx(1.2, rel=0.01)
    assert restored.genome.physical.color_hue.value == pytest.approx(0.7, rel=0.01)
