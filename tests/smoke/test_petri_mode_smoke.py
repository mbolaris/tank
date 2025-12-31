"""Smoke test for Petri mode backend integration."""

from backend.world_registry import create_world


def test_petri_mode_smoke() -> None:
    world, snapshot_builder = create_world("petri", seed=123, headless=True)

    result = world.reset(seed=123)
    assert result.snapshot.get("world_type") == "petri"

    for _ in range(100):
        result = world.step()

    snapshots = snapshot_builder.build(result, world)
    assert isinstance(snapshots, list)
    if snapshots:
        assert any(
            getattr(snapshot, "render_hint", {}).get("style") == "petri"
            for snapshot in snapshots
        )
