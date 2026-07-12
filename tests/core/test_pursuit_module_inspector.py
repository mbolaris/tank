"""Contracts for the fish inspector's pursuit-module ("Modules") payload."""

from __future__ import annotations

from backend.simulation_runner import SimulationRunner
from core.entities import Fish


def _fish_and_snapshot(runner: SimulationRunner):
    snapshot = next(e for e in runner._collect_entities() if e.type == "fish")
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    return fish, snapshot


def test_modules_is_none_without_the_opt_in_flags() -> None:
    runner = SimulationRunner(seed=42)
    _, snapshot = _fish_and_snapshot(runner)
    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})

    assert result["success"] is True
    assert result["details"]["modules"] is None


def test_modules_reports_parameters_and_current_food_target() -> None:
    runner = SimulationRunner(
        seed=42,
        config={"graph_behavior_enabled": True, "target_pursuit_module_enabled": True},
    )
    fish, snapshot = _fish_and_snapshot(runner)
    assert fish.genome.behavioral.target_pursuit_module is not None

    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    modules = result["details"]["modules"]

    assert modules is not None
    assert modules["name"] == "Target Pursuit v1"
    assert modules["used_for"] == ["Food", "Soccer"]
    assert set(modules["parameters"]) == {
        "assumed_speed",
        "prediction_strength",
        "max_prediction_horizon",
        "pursuit_commitment",
    }
    assert modules["inherited_from"] == getattr(fish, "parent_id", None)
    # This fish is a founder with food nearby (seed 42's standard population).
    if modules["current_target"] is not None:
        assert modules["current_target"] in {"Food", "Soccer Ball"}
        assert len(modules["target_vector"]) == 2
        assert len(modules["aim_vector"]) == 2


def test_modules_details_do_not_consume_rng_or_mutate_state() -> None:
    """Telemetry purity, matching the general get_entity_details contract."""
    runner = SimulationRunner(
        seed=42,
        config={"graph_behavior_enabled": True, "target_pursuit_module_enabled": True},
    )
    _, snapshot = _fish_and_snapshot(runner)
    rng_state_before = runner.world.rng.getstate()

    runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    runner.handle_command("get_entity_details", {"entity_id": snapshot.id})

    assert runner.world.rng.getstate() == rng_state_before
