"""Tests for authoritative Build Mode commands."""

from backend.simulation_runner import SimulationRunner


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
