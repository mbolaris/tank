"""Tests for world config overrides through WorldManager."""

from backend.world_manager import WorldManager


def test_world_manager_passes_config_overrides_to_tank_world() -> None:
    """WorldManager should apply CreateWorldRequest config to tank runtime."""
    manager = WorldManager()
    instance = manager.create_world(
        world_type="tank",
        name="Config Override Tank",
        config={"soccer_enabled": True, "soccer_match_every_frames": 10},
        persistent=False,
        seed=123,
        start_paused=True,
    )
    try:
        config = instance.runner.world.config
        assert config.soccer.enabled is True
        assert config.soccer.match_every_frames == 10
    finally:
        manager.delete_world(instance.world_id)
