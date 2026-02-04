from __future__ import annotations

from typing import cast

from backend.world_persistence import restore_world_from_snapshot
from core.entities import Fish, Plant, PlantNectar
from core.genetics import PlantGenome
from core.movement_strategy import AlgorithmicMovement
from core.world import World
from core.worlds import WorldRegistry


def test_persistence_round_trip():
    """Test that saving and restoring a world preserves entity state and references."""
    # Setup Source World via canonical WorldRegistry path
    config = {
        "headless": True,
        "screen_width": 1000,
        "screen_height": 1000,
        "max_population": 100,
        "auto_food_enabled": False,
    }
    adapter = WorldRegistry.create_world("tank", seed=42, config=config)
    adapter.reset(seed=42, config=config)
    world = adapter
    assert world.environment is not None
    environment = cast(World, world.environment)

    # Add a Fish with specific properties we can verify
    test_fish = Fish(
        environment=environment,
        movement_strategy=AlgorithmicMovement(),
        species="test-roundtrip-species",
        x=100,
        y=100,
        speed=5.0,
        initial_energy=75.0,
        fish_id=None,  # Let it get assigned
    )
    world.add_entity(test_fish)
    test_fish_energy = test_fish.energy

    # Add Plant with specific ID we can track
    assert world.engine.root_spot_manager is not None
    spot = world.engine.root_spot_manager.get_spot_by_id(0)
    assert spot is not None

    # If spot is occupied, release it first
    if spot.occupied:
        spot.release()

    test_plant = Plant(
        environment=environment,
        genome=PlantGenome.create_random(rng=world.rng),
        root_spot=spot,
        plant_id=999,
        initial_energy=42.0,
    )
    spot.claim(test_plant)
    world.add_entity(test_plant)

    # Add Nectar linked to our test Plant
    test_nectar = PlantNectar(x=200, y=200, source_plant=test_plant, environment=environment)
    test_nectar.energy = 7.5
    world.add_entity(test_nectar)

    # Capture State
    snapshot = adapter.capture_state_for_save()

    # Verify Snapshot Structure
    assert snapshot is not None
    assert "schema_version" in snapshot, "Snapshot should have schema_version"
    assert "entities" in snapshot, "Snapshot should have entities"
    assert (
        len(snapshot["entities"]) >= 3
    ), f"Expected at least 3 entities, got {len(snapshot['entities'])}"

    # Setup Destination World (Fresh)
    dest_adapter = WorldRegistry.create_world("tank", seed=43, config=config)
    dest_adapter.reset(seed=43, config=config)

    # Restore
    success = restore_world_from_snapshot(snapshot, dest_adapter)
    assert success, "Restore should succeed"

    # Verify Restoration
    dest_entities = dest_adapter.entities_list

    # Verify our specific Plant (ID 999) was restored
    restored_test_plant = next(
        (e for e in dest_entities if isinstance(e, Plant) and e.plant_id == 999), None
    )
    assert restored_test_plant is not None, "Test plant with ID 999 should be restored"
    assert (
        abs(restored_test_plant.energy - 42.0) < 0.01
    ), f"Plant energy mismatch: {restored_test_plant.energy}"

    # Verify Nectar is restored and linked to the correct plant
    restored_nectars = [e for e in dest_entities if isinstance(e, PlantNectar)]
    # Find nectar that was linked to our test plant
    test_nectar_restored = next(
        (n for n in restored_nectars if n.source_plant and n.source_plant.plant_id == 999), None
    )
    assert test_nectar_restored is not None, "Test nectar should be restored with link to plant 999"
    assert (
        abs(test_nectar_restored.energy - 7.5) < 0.01
    ), f"Nectar energy mismatch: {test_nectar_restored.energy}"
    # Most importantly: verify the reference integrity
    assert (
        test_nectar_restored.source_plant is restored_test_plant
    ), "Nectar.source_plant should reference the restored plant object"

    # Verify Fish with our test species was restored
    restored_test_fish = next(
        (e for e in dest_entities if isinstance(e, Fish) and e.species == "test-roundtrip-species"),
        None,
    )
    assert restored_test_fish is not None, "Test fish should be restored"
    assert (
        abs(restored_test_fish.energy - test_fish_energy) < 0.01
    ), f"Fish energy mismatch: {restored_test_fish.energy}"
