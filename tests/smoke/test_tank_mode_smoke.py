"""Smoke test for Tank mode backend integration."""

from backend.world_registry import create_world


def test_tank_mode_smoke() -> None:
    """Smoke test verifying Tank mode works end-to-end.

    This test ensures:
    - Tank world backend can be created
    - World can be reset with a seed
    - World can step for multiple frames without errors
    - Snapshot builder produces valid snapshots
    """
    world, snapshot_builder = create_world("tank", seed=123, headless=True)

    result = world.reset(seed=123)
    assert result.snapshot.get("world_type") == "tank"

    for _ in range(100):
        result = world.step()

    snapshots = snapshot_builder.build(result, world)
    assert isinstance(snapshots, list)
    # Tank mode should produce at least one snapshot
    assert len(snapshots) >= 1
