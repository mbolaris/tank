from backend.simulation_runner import SimulationRunner


def test_snapshot_ids_stable_across_tank_petri_switches() -> None:
    runner = SimulationRunner(world_type="tank", seed=42)

    for _ in range(10):
        runner.world.step()

    with runner.lock:
        entities_before = list(runner.world.entities_list)
        provider = runner.engine._identity_provider

    assert provider is not None

    before_entity_ids = {id(e): int(provider.get_identity(e)[1]) for e in entities_before}
    assert before_entity_ids

    snapshots_before = runner.get_entities_snapshot()
    assert {s.id for s in snapshots_before} == set(before_entity_ids.values())

    runner.switch_world_type("petri")

    with runner.lock:
        entities_petri = list(runner.world.entities_list)
        provider_petri = runner.engine._identity_provider

    assert provider_petri is provider
    petri_entity_ids = {id(e): int(provider_petri.get_identity(e)[1]) for e in entities_petri}
    assert petri_entity_ids == before_entity_ids

    snapshots_petri = runner.get_entities_snapshot()
    assert {s.id for s in snapshots_petri} == set(before_entity_ids.values())

    fish_petri = [s for s in snapshots_petri if s.type == "fish"]
    if fish_petri:
        assert all(
            (s.render_hint or {}).get("style") == "petri"
            and (s.render_hint or {}).get("sprite") == "microbe"
            for s in fish_petri
        )

    runner.switch_world_type("tank")
    snapshots_after = runner.get_entities_snapshot()
    assert {s.id for s in snapshots_after} == set(before_entity_ids.values())

    fish_after = [s for s in snapshots_after if s.type == "fish"]
    if fish_after:
        assert all((s.render_hint or {}).get("style") == "pixel" for s in fish_after)
