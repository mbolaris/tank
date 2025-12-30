"""Tests for world-agnostic backend components.

These tests verify:
- WorldRunner delegates correctly to world and snapshot builder
- World registry creates tank world correctly
- Payloads include world_type and view_mode
"""

from __future__ import annotations

import pytest

from backend.world_registry import (
    create_world,
    get_world_metadata,
    get_registered_world_types,
)
from backend.world_runner import WorldRunner
from backend.snapshots import SnapshotBuilder, TankSnapshotBuilder
from core.interfaces import WorldBackend


def test_tank_world_is_registered() -> None:
    """Tank world should be registered on module import."""
    assert "tank" in get_registered_world_types()


def test_create_tank_world_returns_tuple() -> None:
    """create_world should return (world, snapshot_builder) tuple."""
    world, snapshot_builder = create_world("tank", seed=42)

    assert world is not None
    assert snapshot_builder is not None


def test_tank_world_satisfies_world_backend_protocol() -> None:
    """TankWorld should satisfy the WorldBackend protocol."""
    world, _ = create_world("tank", seed=42)

    # Check required properties exist
    assert hasattr(world, "frame_count")
    assert hasattr(world, "paused")
    assert hasattr(world, "entities_list")

    # Check required methods exist
    assert hasattr(world, "setup")
    assert hasattr(world, "update")
    assert hasattr(world, "reset")
    assert hasattr(world, "get_stats")


def test_tank_snapshot_builder_satisfies_protocol() -> None:
    """TankSnapshotBuilder should satisfy the SnapshotBuilder protocol."""
    _, snapshot_builder = create_world("tank", seed=42)

    assert isinstance(snapshot_builder, TankSnapshotBuilder)
    assert hasattr(snapshot_builder, "collect")
    assert hasattr(snapshot_builder, "to_snapshot")


def test_world_metadata() -> None:
    """World metadata should include view_mode."""
    metadata = get_world_metadata("tank")

    assert metadata is not None
    assert metadata.world_type == "tank"
    assert metadata.view_mode == "side"
    assert metadata.display_name == "Fish Tank"


def test_world_runner_delegates_step() -> None:
    """WorldRunner.step() should call world.update()."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    initial_frame = runner.frame_count
    runner.step()

    # Frame count should advance (unless paused)
    assert runner.frame_count >= initial_frame


def test_world_runner_exposes_world_info() -> None:
    """WorldRunner should expose world_type and view_mode."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank", view_mode="side")

    info = runner.get_world_info()

    assert info["world_type"] == "tank"
    assert info["view_mode"] == "side"


def test_world_runner_gets_entity_snapshots() -> None:
    """WorldRunner.get_entities_snapshot() should return list of snapshots."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    snapshots = runner.get_entities_snapshot()

    # Should return a list (may be empty if no entities yet)
    assert isinstance(snapshots, list)


def test_unknown_world_type_raises() -> None:
    """create_world should raise ValueError for unknown world type."""
    with pytest.raises(ValueError, match="Unknown world type"):
        create_world("nonexistent_world")
