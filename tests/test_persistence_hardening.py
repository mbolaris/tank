from __future__ import annotations

from typing import cast

from backend.restore_spawn import spawn_restored_entity
from backend.world_persistence import (
    _bootstrap_static_elements,
    _bootstrap_transient_elements,
    restore_world_from_snapshot,
)
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


def test_persistence_preserves_fish_identity_and_lineage():
    config = {
        "headless": True,
        "screen_width": 1000,
        "screen_height": 1000,
        "max_population": 100,
        "auto_food_enabled": False,
    }
    adapter = WorldRegistry.create_world("tank", seed=42, config=config)
    adapter.reset(seed=42, config=config)
    assert adapter.environment is not None
    environment = cast(World, adapter.environment)

    adapter.engine._entity_manager.clear()
    adapter.engine.ecosystem.lineage.clear()
    adapter.engine.ecosystem.next_fish_id = 12

    parent = Fish(
        environment=environment,
        movement_strategy=AlgorithmicMovement(),
        species="parent-species",
        x=100,
        y=100,
        speed=5.0,
        fish_id=10,
        ecosystem=adapter.engine.ecosystem,
    )
    child = Fish(
        environment=environment,
        movement_strategy=AlgorithmicMovement(),
        species="child-species",
        x=120,
        y=120,
        speed=5.0,
        fish_id=11,
        ecosystem=adapter.engine.ecosystem,
        parent_id=10,
        generation=1,
    )
    adapter.add_entity(parent)
    adapter.add_entity(child)
    parent.register_birth()
    child.register_birth()

    snapshot = adapter.capture_state_for_save()
    assert "lineage_log" in snapshot
    assert any(
        record["id"] == "11" and record["parent_id"] == "10" for record in snapshot["lineage_log"]
    )

    dest_adapter = WorldRegistry.create_world("tank", seed=43, config=config)
    dest_adapter.reset(seed=43, config=config)

    assert restore_world_from_snapshot(snapshot, dest_adapter) is True

    restored_fish = {
        entity.fish_id: entity for entity in dest_adapter.entities_list if isinstance(entity, Fish)
    }
    assert {10, 11}.issubset(restored_fish)
    assert restored_fish[11].parent_id == 10
    assert dest_adapter.engine.ecosystem.next_fish_id >= 12

    lineage_data = dest_adapter.engine.ecosystem.get_lineage_data({10, 11})
    child_record = next(record for record in lineage_data if record["id"] == "11")
    assert child_record["parent_id"] == "10"
    assert "_original_parent_id" not in child_record


def test_legacy_snapshot_lineage_restore_adds_missing_parent_placeholder():
    config = {
        "headless": True,
        "screen_width": 1000,
        "screen_height": 1000,
        "max_population": 100,
        "auto_food_enabled": False,
    }
    adapter = WorldRegistry.create_world("tank", seed=42, config=config)
    adapter.reset(seed=42, config=config)
    assert adapter.environment is not None
    environment = cast(World, adapter.environment)

    adapter.engine._entity_manager.clear()
    adapter.engine.ecosystem.lineage.clear()

    child = Fish(
        environment=environment,
        movement_strategy=AlgorithmicMovement(),
        species="legacy-child-species",
        x=120,
        y=120,
        speed=5.0,
        fish_id=11,
        ecosystem=adapter.engine.ecosystem,
        parent_id=10,
        generation=3,
    )
    adapter.add_entity(child)

    snapshot = adapter.capture_state_for_save()
    snapshot.pop("lineage_log", None)

    dest_adapter = WorldRegistry.create_world("tank", seed=43, config=config)
    dest_adapter.reset(seed=43, config=config)

    assert restore_world_from_snapshot(snapshot, dest_adapter) is True

    lineage_data = dest_adapter.engine.ecosystem.get_lineage_data({11})
    parent_record = next(record for record in lineage_data if record["id"] == "10")
    child_record = next(record for record in lineage_data if record["id"] == "11")
    assert parent_record["is_placeholder"] is True
    assert child_record["parent_id"] == "10"
    assert "_original_parent_id" not in child_record


def _soccer_entity_counts(engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in engine.entities_list:
        kind = getattr(entity, "snapshot_type", None)
        if kind in ("ball", "goal_zone"):
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def _fresh_tank_engine():
    config = {"headless": True, "auto_food_enabled": False}
    adapter = WorldRegistry.create_world("tank", seed=42, config=config)
    adapter.reset(seed=42, config=config)
    return adapter, adapter.engine


def _strip_soccer_entities(adapter, engine) -> None:
    """Leave the engine in the state a restored world arrives in: no soccer."""
    for entity in list(engine.entities_list):
        if getattr(entity, "snapshot_type", None) in ("ball", "goal_zone"):
            engine.remove_entity(entity)
    engine.environment.ball = None
    engine.environment.goal_manager = None
    adapter.step()
    assert _soccer_entity_counts(engine) == {}


def test_restore_bootstraps_soccer_objects_while_a_phase_is_running():
    """A restore that lands mid-frame must still get its ball and goals.

    `engine.add_entity` refuses to run inside a phase, and restoration does not
    run in lockstep with the simulation loop. The refusal used to be swallowed
    as a warning, so a restored tank came back with every other entity intact
    and no ball and no goal zones for the life of the world - which no amount of
    flipping the ball/goals toggle brought back.
    """
    from core.update_phases import UpdatePhase

    adapter, engine = _fresh_tank_engine()
    _strip_soccer_entities(adapter, engine)

    # Stand exactly where the failure happened: mid-frame.
    engine._current_phase = UpdatePhase.ENTITY_ACT
    try:
        _bootstrap_transient_elements(engine)
    finally:
        engine._current_phase = None

    adapter.step()
    assert _soccer_entity_counts(engine) == {"ball": 1, "goal_zone": 2}


def test_restore_bootstraps_soccer_objects_between_frames():
    """The ordinary, not-in-a-phase path must keep working unchanged."""
    adapter, engine = _fresh_tank_engine()
    _strip_soccer_entities(adapter, engine)

    _bootstrap_transient_elements(engine)

    adapter.step()
    assert _soccer_entity_counts(engine) == {"ball": 1, "goal_zone": 2}


def test_restored_goals_carry_the_side_the_ui_reads():
    """The renderer resolves which end is which from goal_id and team.

    `frontend/src/utils/goalZoneAppearance.ts` keys the goal palette on these
    exact values, so a change here would silently make both ends look alike.
    """
    adapter, engine = _fresh_tank_engine()
    _strip_soccer_entities(adapter, engine)
    _bootstrap_transient_elements(engine)
    adapter.step()

    goals = {
        entity.goal_id: entity.team
        for entity in engine.entities_list
        if getattr(entity, "snapshot_type", None) == "goal_zone"
    }
    assert goals == {"goal_left": "A", "goal_right": "B"}


def test_static_castle_bootstrap_survives_a_running_phase():
    """The castle bootstrap had the same hazard, and it is not even guarded.

    Mid-phase it raised straight out of `restore_world_from_snapshot`, failing
    the whole restore rather than losing one entity.
    """
    from core.update_phases import UpdatePhase

    adapter, engine = _fresh_tank_engine()
    for entity in list(engine.entities_list):
        if getattr(entity, "snapshot_type", None) == "castle":
            engine.remove_entity(entity)
    adapter.step()

    engine._current_phase = UpdatePhase.ENTITY_ACT
    try:
        _bootstrap_static_elements(engine)
    finally:
        engine._current_phase = None

    adapter.step()
    castles = [e for e in engine.entities_list if getattr(e, "snapshot_type", None) == "castle"]
    assert len(castles) == 1


def test_spawn_restored_entity_prefers_the_immediate_path():
    """Immediate is the default: a deferred castle would fail restore validation."""
    calls: list[str] = []

    class Engine:
        def add_entity(self, entity):
            calls.append("add_entity")

        def request_spawn(self, entity, reason=""):
            calls.append("request_spawn")

    spawn_restored_entity(Engine(), object())
    assert calls == ["add_entity"]


def test_spawn_restored_entity_queues_when_the_engine_is_mid_frame():
    calls: list[str] = []

    class Engine:
        def add_entity(self, entity):
            calls.append("add_entity")
            raise RuntimeError(
                "Unsafe call to add_entity during phase UpdatePhase.ENTITY_ACT. "
                "Use request_spawn() instead."
            )

        def request_spawn(self, entity, reason=""):
            calls.append(f"request_spawn:{reason}")
            return True

    spawn_restored_entity(Engine(), object())
    assert calls == ["add_entity", "request_spawn:world_restore"]


def test_spawn_restored_entity_reraises_when_there_is_no_queue():
    """An engine with no request_spawn must surface the refusal, not swallow it."""

    class Engine:
        def add_entity(self, entity):
            raise RuntimeError("Unsafe call to add_entity during phase X.")

    import pytest

    with pytest.raises(RuntimeError, match="Unsafe call"):
        spawn_restored_entity(Engine(), object())
