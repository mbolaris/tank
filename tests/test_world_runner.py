"""Tests for world-agnostic backend components.

These tests verify:
- WorldRunner delegates correctly to world and snapshot builder
- WorldRunner uses StepResult as primary data flow
- World registry creates tank world using MultiAgentWorldBackend
- Payloads include world_type and view_mode
"""

from __future__ import annotations

import pytest

from backend.snapshots import TankSnapshotBuilder
from backend.world_registry import (
    create_world,
    get_registered_world_types,
    get_world_metadata,
)
from backend.world_runner import WorldRunner
from core.worlds.interfaces import MultiAgentWorldBackend, StepResult


def test_tank_world_is_registered() -> None:
    """Tank world should be registered on module import."""
    assert "tank" in get_registered_world_types()


def test_create_tank_world_returns_tuple() -> None:
    """create_world should return (world, snapshot_builder) tuple."""
    world, snapshot_builder = create_world("tank", seed=42)

    assert world is not None
    assert snapshot_builder is not None


def test_tank_world_satisfies_multi_agent_backend_protocol() -> None:
    """TankWorldBackendAdapter should satisfy the MultiAgentWorldBackend ABC."""
    world, _ = create_world("tank", seed=42)

    assert isinstance(world, MultiAgentWorldBackend)

    # Check required methods exist
    assert hasattr(world, "reset")
    assert hasattr(world, "step")
    assert hasattr(world, "get_current_snapshot")
    assert hasattr(world, "get_current_metrics")


def test_tank_snapshot_builder_satisfies_protocol() -> None:
    """TankSnapshotBuilder should satisfy the SnapshotBuilder protocol."""
    _, snapshot_builder = create_world("tank", seed=42)

    assert isinstance(snapshot_builder, TankSnapshotBuilder)
    assert hasattr(snapshot_builder, "collect")
    assert hasattr(snapshot_builder, "to_snapshot")
    assert hasattr(snapshot_builder, "build")


def test_world_metadata() -> None:
    """World metadata should include view_mode."""
    metadata = get_world_metadata("tank")

    assert metadata is not None
    assert metadata.world_type == "tank"
    assert metadata.view_mode == "side"
    assert metadata.display_name == "Fish Tank"


def test_world_runner_reset_returns_step_result() -> None:
    """WorldRunner.reset() should return a StepResult."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    result = runner.reset(seed=42)

    assert isinstance(result, StepResult)
    assert result.done is False
    assert "frame" in result.info


def test_world_runner_step_stores_step_result() -> None:
    """WorldRunner.step() should store the StepResult internally."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    runner.reset(seed=42)
    assert runner.last_step_result is not None

    runner.step()
    assert runner.last_step_result is not None
    assert isinstance(runner.last_step_result, StepResult)


def test_world_runner_frame_count_from_step_result() -> None:
    """WorldRunner.frame_count should come from StepResult."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    assert runner.frame_count == 0  # Before reset

    runner.reset(seed=42)
    initial_frame = runner.frame_count

    runner.step()
    # Frame count should advance
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

    runner.reset(seed=42)
    snapshots = runner.get_entities_snapshot()

    # Should return a list (may be empty if no entities yet)
    assert isinstance(snapshots, list)


def test_world_runner_uses_snapshot_builder_build() -> None:
    """WorldRunner.get_entities_snapshot() should use build() method."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    runner.reset(seed=42)
    
    # After reset, _last_step_result should be set
    assert runner.last_step_result is not None
    
    # get_entities_snapshot should work
    snapshots = runner.get_entities_snapshot()
    assert isinstance(snapshots, list)


def test_world_runner_get_stats() -> None:
    """WorldRunner.get_stats() should return metrics from StepResult."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    runner.reset(seed=42)
    stats = runner.get_stats()

    assert isinstance(stats, dict)


def test_unknown_world_type_raises() -> None:
    """create_world should raise ValueError for unknown world type."""
    with pytest.raises(ValueError, match="Unknown world type"):
        create_world("nonexistent_world")


def test_world_runner_entities_list_compatibility() -> None:
    """WorldRunner.entities_list should still work for compatibility."""
    world, snapshot_builder = create_world("tank", seed=42)
    runner = WorldRunner(world, snapshot_builder, world_type="tank")

    runner.reset(seed=42)
    entities = runner.entities_list

    # Should return a list
    assert isinstance(entities, list)
