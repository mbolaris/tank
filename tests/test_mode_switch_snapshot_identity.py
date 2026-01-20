from backend.simulation_runner import SimulationRunner


def _snapshots_by_pyid(runner: SimulationRunner):
    snapshots = {}
    with runner.lock:
        entities = list(runner.world.entities_list)
    for entity in entities:
        snapshot = runner._entity_snapshot_builder.to_snapshot(entity)
        if snapshot is not None:
            snapshots[id(entity)] = snapshot
    return snapshots


def test_snapshot_ids_stable_across_tank_petri_switches():
    runner = SimulationRunner(world_type="tank", seed=42)

    # Step a bit to ensure we have some entities that rely on the identity provider
    # (e.g. Food / PlantNectar with no intrinsic IDs).
    for _ in range(50):
        runner.world.step()

    before = _snapshots_by_pyid(runner)
    assert before, "Expected at least one snapshot before switch"

    runner.switch_world_type("petri")
    during = _snapshots_by_pyid(runner)
    assert before.keys() == during.keys(), "Entity snapshot coverage changed across switch"
    assert {k: v.id for k, v in before.items()} == {k: v.id for k, v in during.items()}

    fish_during = [s for s in during.values() if s.type == "fish"]
    if fish_during:
        assert all(
            (s.render_hint or {}).get("style") == "petri"
            and (s.render_hint or {}).get("sprite") == "microbe"
            for s in fish_during
        )

    runner.switch_world_type("tank")
    after = _snapshots_by_pyid(runner)
    assert before.keys() == after.keys(), "Entity snapshot coverage changed after round-trip"
    assert {k: v.id for k, v in before.items()} == {k: v.id for k, v in after.items()}

    fish_after = [s for s in after.values() if s.type == "fish"]
    if fish_after:
        assert all((s.render_hint or {}).get("style") == "pixel" for s in fish_after)
