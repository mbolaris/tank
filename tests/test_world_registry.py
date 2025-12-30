"""Tests for world registry and multi-agent world backends.

This module tests the domain-agnostic world abstraction layer,
including the WorldRegistry and TankWorldBackendAdapter.
"""

import pytest

from core.worlds import MultiAgentWorldBackend, StepResult, WorldRegistry
from core.worlds.tank.backend import TankWorldBackendAdapter


class TestWorldRegistry:
    """Tests for WorldRegistry factory."""

    def test_create_tank_world(self):
        """Test creating a tank world through the registry."""
        world = WorldRegistry.create_world("tank", seed=42)
        assert isinstance(world, MultiAgentWorldBackend)
        assert isinstance(world, TankWorldBackendAdapter)

    def test_create_tank_world_with_config(self):
        """Test creating tank world with custom configuration."""
        world = WorldRegistry.create_world(
            "tank", seed=42, max_population=50, screen_width=800, screen_height=600
        )
        assert isinstance(world, TankWorldBackendAdapter)

    def test_create_petri_world_not_implemented(self):
        """Test that petri world raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Petri world backend not yet implemented"):
            WorldRegistry.create_world("petri")

    def test_create_soccer_world_not_implemented(self):
        """Test that soccer world raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Soccer world backend not yet implemented"):
            WorldRegistry.create_world("soccer")

    def test_create_unknown_world(self):
        """Test that unknown world type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown world type: unknown"):
            WorldRegistry.create_world("unknown")

    def test_list_world_types(self):
        """Test listing available world types."""
        types = WorldRegistry.list_world_types()
        assert types["tank"] == "implemented"
        assert types["petri"] == "not_implemented"
        assert types["soccer"] == "not_implemented"


class TestTankWorldBackendAdapter:
    """Tests for TankWorldBackendAdapter."""

    def test_adapter_initialization(self):
        """Test basic adapter initialization."""
        adapter = TankWorldBackendAdapter(seed=42)
        assert adapter._seed == 42
        assert adapter._world is None
        assert adapter._current_frame == 0

    def test_reset_returns_step_result(self):
        """Test that reset() returns a valid StepResult."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        result = adapter.reset(seed=42)

        assert isinstance(result, StepResult)
        assert result.obs_by_agent == {}  # No observations yet
        assert result.done is False
        assert "frame" in result.snapshot
        assert "entities" in result.snapshot
        assert "metrics" in result.__dict__

    def test_reset_creates_world(self):
        """Test that reset() creates and initializes TankWorld."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)

        assert adapter._world is not None
        assert adapter._world.frame_count == 0
        assert len(adapter._world.entities_list) > 0  # Should have initial entities

    def test_reset_with_seed_override(self):
        """Test that reset() can override constructor seed."""
        adapter = TankWorldBackendAdapter(seed=42)
        result1 = adapter.reset(seed=100)
        assert result1.info["seed"] == 100

        result2 = adapter.reset(seed=200)
        assert result2.info["seed"] == 200

    def test_step_without_reset_raises_error(self):
        """Test that step() before reset() raises RuntimeError."""
        adapter = TankWorldBackendAdapter(seed=42)
        with pytest.raises(RuntimeError, match="World not initialized"):
            adapter.step()

    def test_step_returns_step_result(self):
        """Test that step() returns a valid StepResult."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)
        result = adapter.step()

        assert isinstance(result, StepResult)
        assert result.obs_by_agent == {}
        assert result.done is False
        assert "frame" in result.snapshot
        assert "entities" in result.snapshot
        assert result.info["frame"] == 1  # Should be frame 1 after one step

    def test_step_advances_simulation(self):
        """Test that step() advances the simulation."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)

        initial_frame = adapter._world.frame_count
        adapter.step()
        assert adapter._world.frame_count == initial_frame + 1

        adapter.step()
        assert adapter._world.frame_count == initial_frame + 2

    def test_get_current_snapshot(self):
        """Test get_current_snapshot() returns valid snapshot."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)

        snapshot = adapter.get_current_snapshot()
        assert "frame" in snapshot
        assert "paused" in snapshot
        assert "width" in snapshot
        assert "height" in snapshot
        assert "entities" in snapshot
        assert isinstance(snapshot["entities"], list)

    def test_get_current_metrics(self):
        """Test get_current_metrics() returns valid metrics."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)

        metrics = adapter.get_current_metrics()
        assert isinstance(metrics, dict)
        # Should have some stats from the simulation
        assert len(metrics) > 0

    def test_snapshot_has_stable_structure(self):
        """Test that snapshot has a stable structure for UI rendering."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        result = adapter.reset(seed=42)

        snapshot = result.snapshot
        assert snapshot["frame"] == 0
        assert snapshot["paused"] is False
        assert snapshot["width"] > 0
        assert snapshot["height"] > 0
        assert isinstance(snapshot["entities"], list)

        # Each entity should have essential attributes
        if snapshot["entities"]:
            entity = snapshot["entities"][0]
            assert "type" in entity
            assert "x" in entity
            assert "y" in entity

    def test_multiple_steps_produce_events(self):
        """Test that stepping produces events over time."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=20)
        adapter.reset(seed=42)

        all_events = []
        for _ in range(100):
            result = adapter.step()
            all_events.extend(result.events)

        # With enough steps and entities, we should see some events
        # (though not guaranteed - depends on simulation dynamics)
        # Just verify the events structure is valid
        for event in all_events:
            assert "type" in event
            assert "frame" in event

    def test_reset_clears_previous_state(self):
        """Test that reset() clears previous simulation state."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)

        # First run
        adapter.reset(seed=42)
        adapter.step()
        adapter.step()
        frame_after_steps = adapter._world.frame_count
        assert frame_after_steps > 0

        # Reset and verify state is cleared
        adapter.reset(seed=42)
        assert adapter._world.frame_count == 0
        assert adapter._current_frame == 0

    def test_deterministic_reset_with_same_seed(self):
        """Test that reset with same seed produces consistent results."""
        adapter1 = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter2 = TankWorldBackendAdapter(seed=42, max_population=10)

        result1 = adapter1.reset(seed=42)
        result2 = adapter2.reset(seed=42)

        # Should have same number of initial entities
        assert len(result1.snapshot["entities"]) == len(result2.snapshot["entities"])

        # Frame and dimensions should match
        assert result1.snapshot["frame"] == result2.snapshot["frame"]
        assert result1.snapshot["width"] == result2.snapshot["width"]
        assert result1.snapshot["height"] == result2.snapshot["height"]

    def test_world_property_access(self):
        """Test that world property provides access to underlying TankWorld."""
        adapter = TankWorldBackendAdapter(seed=42)
        assert adapter.world is None

        adapter.reset(seed=42)
        assert adapter.world is not None
        assert hasattr(adapter.world, "engine")
        assert hasattr(adapter.world, "entities_list")


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_step_result_default_values(self):
        """Test StepResult with default values."""
        result = StepResult()
        assert result.obs_by_agent == {}
        assert result.snapshot == {}
        assert result.events == []
        assert result.metrics == {}
        assert result.done is False
        assert result.info == {}

    def test_step_result_with_values(self):
        """Test StepResult with custom values."""
        result = StepResult(
            obs_by_agent={"agent1": {"pos": [0, 0]}},
            snapshot={"frame": 10},
            events=[{"type": "test"}],
            metrics={"count": 5},
            done=True,
            info={"custom": "value"},
        )

        assert result.obs_by_agent == {"agent1": {"pos": [0, 0]}}
        assert result.snapshot == {"frame": 10}
        assert result.events == [{"type": "test"}]
        assert result.metrics == {"count": 5}
        assert result.done is True
        assert result.info == {"custom": "value"}
