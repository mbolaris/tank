"""Tests for the opt-in local resource-patch experiment."""

from __future__ import annotations

from core.entities import ResourcePatch


def test_resource_patch_depletes_without_disappearing_and_regrows(simulation_env):
    env, _ = simulation_env
    patch = ResourcePatch(
        env,
        100,
        120,
        patch_id=1,
        food_type="algae",
        stock=10,
        regrowth_rate=2,
    )

    assert patch.take_bite(6) == 6
    assert patch.energy == 4
    assert patch.is_fully_consumed() is False
    assert patch.regrow() == 2
    assert patch.energy == 6


def test_resource_patch_is_stationary_and_has_stable_snapshot_identity(simulation_env):
    env, _ = simulation_env
    patch = ResourcePatch(
        env,
        100,
        120,
        patch_id=7,
        food_type="protein",
        stock=20,
        regrowth_rate=0,
    )
    original = patch.pos.copy()

    patch.update(1)

    assert patch.snapshot_type == "resource_patch"
    assert patch.get_entity_id() == 7
    assert patch.pos == original
    assert patch.get_patch_state()["max_stock"] == 20.0


def test_resource_patch_experiment_is_off_by_default():
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42)
    runner.world.step({})

    assert not any(isinstance(entity, ResourcePatch) for entity in runner.world.entities_list)


def test_resource_patch_experiment_exposes_two_renderable_patches():
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42, config={"local_resource_patches_enabled": True})
    runner.world.step({})
    patches = [
        snapshot.to_full_dict()
        for snapshot in runner.get_entities_snapshot()
        if snapshot.type == "resource_patch"
    ]

    assert [
        (patch["render_hint"]["kind"], patch["render_hint"]["stock_ratio"]) for patch in patches
    ] == [
        ("algae", 1.0),
        ("protein", 1.0),
    ]
    assert all(patch["render_hint"]["style"] == "resource_patch" for patch in patches)
