"""Tests for the entity-backed tank-object substrate."""

from core.tank_objects import OBJECT_DEFINITIONS, TankObject, TankObjectLayout


def test_object_ids_are_world_scoped_and_deterministic(simulation_env):
    environment = simulation_env[0]
    first = TankObject(environment, 10, 20, object_kind="decorative_rock")
    second = TankObject(environment, 30, 40, object_kind="decorative_rock")

    assert (first.object_id, second.object_id) == (1, 2)
    assert [first.object_id, second.object_id] == sorted([first.object_id, second.object_id])


def test_explicit_object_id_is_preserved_and_advances_allocator(simulation_env):
    environment = simulation_env[0]
    placed = TankObject(environment, 10, 20, object_kind="castle", object_id=218)
    next_object = TankObject(environment, 30, 40, object_kind="decorative_rock")

    assert placed.get_entity_id() == 218
    assert next_object.object_id == 219


def test_object_state_round_trips_without_catalog_placement_metadata(simulation_env):
    environment = simulation_env[0]
    original = TankObject(
        environment,
        12,
        34,
        object_kind="decorative_rock",
        object_id=7,
        width=80,
        height=55,
        rotation=15,
        capability_config=({"capability_id": "shelter-main"},),
    )

    state = original.to_object_state()
    restored = TankObject(
        environment,
        state["x"],
        state["y"],
        object_kind=state["type"],
        object_id=state["object_id"],
        width=state["width"],
        height=state["height"],
        rotation=state["rotation"],
        capability_config=state["capability_config"],
    )

    assert restored.to_object_state() == state
    assert "x" not in OBJECT_DEFINITIONS["decorative_rock"].__dict__


def test_default_layout_is_separate_from_object_definitions():
    layout = TankObjectLayout("castle", 585, 418)

    assert layout.x == 585
    assert layout.y == 418
    assert "default_x" not in OBJECT_DEFINITIONS["castle"].__dict__


def test_default_layout_objects_stay_inside_tank_and_leave_central_corridor_open():
    from core.tank_objects import DEFAULT_TANK_HEIGHT, DEFAULT_TANK_LAYOUT, DEFAULT_TANK_WIDTH

    for layout in DEFAULT_TANK_LAYOUT:
        assert layout.x >= 0
        assert layout.y >= 0
        assert layout.x + (layout.width or 0) <= DEFAULT_TANK_WIDTH
        assert layout.y + (layout.height or 0) <= DEFAULT_TANK_HEIGHT

    castle = next(layout for layout in DEFAULT_TANK_LAYOUT if layout.kind == "castle")
    grotto = next(layout for layout in DEFAULT_TANK_LAYOUT if layout.kind == "protein_grotto")
    assert castle.x > DEFAULT_TANK_WIDTH * 0.55
    assert grotto.x + (grotto.width or 0) < 1000
    assert grotto.x > DEFAULT_TANK_WIDTH * 0.7

    # Major landmarks leave the middle open for ordinary movement and soccer.
    major = [layout for layout in DEFAULT_TANK_LAYOUT if layout.kind != "decorative_rock"]
    assert all(layout.x + (layout.width or 0) <= 300 or layout.x >= 600 for layout in major)


def test_default_tank_seeds_composed_objects_without_legacy_patches():
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42)
    runner.world.step({})
    kinds = {
        snapshot.type
        for snapshot in runner.get_entities_snapshot()
        if snapshot.type in {"castle", "algae_reef", "protein_grotto", "decorative_rock"}
    }

    assert kinds == {"castle", "algae_reef", "protein_grotto", "decorative_rock"}
    assert (
        sum(snapshot.type == "decorative_rock" for snapshot in runner.get_entities_snapshot()) == 3
    )
    assert "resource_patch" not in {snapshot.type for snapshot in runner.get_entities_snapshot()}
