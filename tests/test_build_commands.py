"""Tests for authoritative Build Mode commands."""

from backend.simulation_runner import SimulationRunner
from core.tank_objects import TankObject


def test_build_commands_place_move_and_delete_generic_object():
    runner = SimulationRunner(seed=42)
    placed = runner.handle_command(
        "place_tank_object",
        {"object_kind": "decorative_rock", "x": 300, "y": 300, "width": 86, "height": 54},
    )

    assert placed["success"] is True
    object_id = placed["object"]["object_id"]
    runner.world.step({})

    moved = runner.handle_command("move_tank_object", {"object_id": object_id, "x": 340, "y": 320})
    assert moved["success"] is True
    assert moved["object"]["x"] == 340

    deleted = runner.handle_command("delete_tank_object", {"object_id": object_id})
    assert deleted["success"] is True


def test_build_placement_uses_curated_feeder_capability_defaults():
    runner = SimulationRunner(seed=42)
    placed = runner.handle_command(
        "place_tank_object", {"object_kind": "algae_reef", "x": 300, "y": 300}
    )

    assert placed["success"] is True
    assert placed["object"]["capability_config"][0]["resource_type"] == "algae"


def test_build_commands_reject_out_of_bounds_objects():
    runner = SimulationRunner(seed=42)
    result = runner.handle_command(
        "place_tank_object", {"object_kind": "protein_grotto", "x": 1000, "y": 540}
    )

    assert result["success"] is False
    assert "inside the tank" in result["error"]


def test_move_and_delete_require_the_raw_object_id_not_the_wire_id():
    """Regression test for the BuildMode Keep-here/Delete id-namespace bug.

    TankObject.get_entity_id() returns the raw object_id (small integers),
    but the snapshot-facing EntitySnapshot.id sent to the frontend carries a
    +5,000,000 offset (core/worlds/shared/identity.py's OTHER_OFFSET).
    _get_object() in backend/runner/commands/build.py matches on the raw id,
    so a command payload built from EntitySnapshot.id must fail, and the raw
    id exposed via render_hint["object_id"] must be what actually works.
    """
    runner = SimulationRunner(seed=42)
    placed = runner.handle_command(
        "place_tank_object",
        {"object_kind": "decorative_rock", "x": 300, "y": 300, "width": 86, "height": 54},
    )
    assert placed["success"] is True
    raw_object_id = placed["object"]["object_id"]
    runner.world.step({})
    runner.get_state(force_full=True)  # wires up the snapshot builder's identity provider

    entity = next(
        e
        for e in runner.world.entities_list
        if isinstance(e, TankObject) and e.object_id == raw_object_id
    )
    snapshot = runner._entity_to_data(entity)
    wire_id = snapshot.id
    assert wire_id != raw_object_id
    assert snapshot.render_hint["object_id"] == raw_object_id

    wrong_id_result = runner.handle_command("delete_tank_object", {"object_id": wire_id})
    assert wrong_id_result["success"] is False

    right_id_result = runner.handle_command("delete_tank_object", {"object_id": raw_object_id})
    assert right_id_result["success"] is True


def test_castle_snapshot_exposes_render_hint_object_id():
    """Regression test: castle TankObjects fell into a dead
    ``elif entity_type == "castle": pass`` branch in TankSnapshotBuilder that
    pre-empted the isinstance(entity, TankObject) enrichment branch (Castle()
    just constructs a TankObject(object_kind="castle"), not a distinct entity
    class -- see core/tank_objects.py's _CastleCompatibilityMeta). That left
    castles alone without render_hint at all, so BuildMode's Keep-here/Delete
    had no raw object_id to fall back on even after fixing the general
    wire-id/raw-id mismatch.
    """
    runner = SimulationRunner(seed=42)
    placed = runner.handle_command(
        "place_tank_object", {"object_kind": "castle", "x": 300, "y": 300}
    )
    assert placed["success"] is True
    raw_object_id = placed["object"]["object_id"]
    runner.world.step({})
    runner.get_state(force_full=True)  # wires up the snapshot builder's identity provider

    entity = next(
        e
        for e in runner.world.entities_list
        if isinstance(e, TankObject) and e.object_id == raw_object_id
    )
    snapshot = runner._entity_to_data(entity)
    assert snapshot.render_hint is not None
    assert snapshot.render_hint["object_id"] == raw_object_id
