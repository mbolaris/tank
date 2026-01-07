"""Tests for world registry and multi-agent world backends.

This module tests the domain-agnostic world abstraction layer,
including the WorldRegistry and TankWorldBackendAdapter.
"""

import pytest

from core.config.display import FRAME_RATE, SCREEN_WIDTH
from core.worlds import MultiAgentWorldBackend, StepResult, WorldRegistry
from core.worlds.petri.backend import PetriWorldBackendAdapter
from core.worlds.tank.backend import TankWorldBackendAdapter


class TestWorldRegistry:
    """Tests for WorldRegistry factory."""

    def test_create_tank_world(self):
        """Test creating a tank world through the registry."""
        world = WorldRegistry.create_world("tank", seed=42)
        assert isinstance(world, MultiAgentWorldBackend)
        assert isinstance(world, TankWorldBackendAdapter)

    def test_create_world_from_mode_pack(self):
        """WorldRegistry should create a world from a mode pack."""
        mode_pack = WorldRegistry.get_mode_pack("tank")
        assert mode_pack is not None
        world = WorldRegistry.create_world(mode_pack.mode_id, seed=42)
        assert isinstance(world, TankWorldBackendAdapter)

    def test_create_tank_world_with_config(self):
        """Test creating tank world with custom configuration."""
        world = WorldRegistry.create_world(
            "tank", seed=42, max_population=50, screen_width=800, screen_height=600
        )
        assert isinstance(world, TankWorldBackendAdapter)

    def test_create_petri_world(self):
        """Test creating a petri world through the registry."""
        world = WorldRegistry.create_world("petri", seed=42)
        assert isinstance(world, MultiAgentWorldBackend)
        assert isinstance(world, PetriWorldBackendAdapter)

    def test_create_soccer_world(self):
        """Test creating a soccer world through the registry."""
        world = WorldRegistry.create_world("soccer", seed=42, team_size=3)
        assert isinstance(world, MultiAgentWorldBackend)
        from core.worlds.soccer.backend import SoccerWorldBackendAdapter

        assert isinstance(world, SoccerWorldBackendAdapter)

    def test_create_unknown_world(self):
        """Test that unknown world type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown mode 'unknown'"):
            WorldRegistry.create_world("unknown")

    def test_list_world_types(self):
        """Test listing available world types."""
        types = WorldRegistry.list_world_types()
        assert types["tank"] == "implemented"
        assert types["petri"] == "implemented"
        assert types["soccer"] == "implemented"

    def test_tank_mode_pack_config_normalization(self):
        """Mode pack should normalize legacy keys and fill defaults."""
        mode_pack = WorldRegistry.get_mode_pack("tank")
        assert mode_pack is not None

        # Normalized to use canonical keys since legacy aliases were removed
        normalized = mode_pack.configure(
            {"screen_width": 900, "screen_height": 500, "frame_rate": 40}
        )
        assert normalized["screen_width"] == 900
        assert normalized["screen_height"] == 500
        assert normalized["frame_rate"] == 40
        # headless default is implicitly handled or not in defaults list,
        # but TANK_MODE_DEFAULTS doesn't have 'headless'. check logic.

        defaults_only = mode_pack.configure({})
        assert defaults_only["screen_width"] == SCREEN_WIDTH
        assert defaults_only["frame_rate"] == FRAME_RATE


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
        assert "entities" not in result.snapshot
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
        assert "entities" not in result.snapshot
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
        assert "entities" not in snapshot

    def test_get_current_metrics(self):
        """Test get_current_metrics() returns valid metrics."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.reset(seed=42)

        metrics = adapter.get_current_metrics()
        assert isinstance(metrics, dict)
        # Should have some stats from the simulation
        assert len(metrics) > 0

    def test_snapshot_has_stable_structure(self):
        """Test that snapshot has a stable structure."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        result = adapter.reset(seed=42)

        snapshot = result.snapshot
        assert snapshot["frame"] == 0
        assert snapshot["paused"] is False
        assert snapshot["width"] > 0
        assert snapshot["height"] > 0
        assert "entities" not in snapshot

        # Check debug snapshot for full data
        debug_snapshot = adapter.get_debug_snapshot()
        assert "entities" in debug_snapshot
        assert isinstance(debug_snapshot["entities"], list)

        if debug_snapshot["entities"]:
            entity = debug_snapshot["entities"][0]
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

        # Should have same number of initial entities (check via debug snapshot)
        debug_snap1 = adapter1.get_debug_snapshot()
        debug_snap2 = adapter2.get_debug_snapshot()
        assert len(debug_snap1["entities"]) == len(debug_snap2["entities"])

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


class TestTankWorldBackendAdapterCompatibility:
    """Tests for TankWorldBackendAdapter compatibility layer.

    These tests verify that the adapter can act as a drop-in replacement
    for TankWorld in existing backend code.
    """

    def test_entities_list_property(self):
        """Test entities_list compatibility property."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.entities_list

        # After reset, should delegate to underlying world
        adapter.reset(seed=42)
        assert isinstance(adapter.entities_list, list)
        assert len(adapter.entities_list) > 0

    def test_frame_count_property(self):
        """Test frame_count compatibility property."""
        adapter = TankWorldBackendAdapter(seed=42)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.frame_count

        # After reset, should start at 0
        adapter.reset(seed=42)
        assert adapter.frame_count == 0

        # Should increment after step
        adapter.step()
        assert adapter.frame_count == 1

    def test_paused_property_get_set(self):
        """Test paused compatibility property (get and set)."""
        adapter = TankWorldBackendAdapter(seed=42)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.paused

        with pytest.raises(RuntimeError, match="World not initialized"):
            adapter.paused = True

        # After reset, should be able to get and set
        adapter.reset(seed=42)
        assert adapter.paused is False

        adapter.paused = True
        assert adapter.paused is True

        adapter.paused = False
        assert adapter.paused is False

    def test_engine_property(self):
        """Test engine compatibility property."""
        adapter = TankWorldBackendAdapter(seed=42)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.engine

        # After reset, should delegate to underlying world
        adapter.reset(seed=42)
        assert adapter.engine is not None
        assert hasattr(adapter.engine, "update")
        assert hasattr(adapter.engine, "entities_list")

    def test_ecosystem_property(self):
        """Test ecosystem compatibility property."""
        adapter = TankWorldBackendAdapter(seed=42)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.ecosystem

        # After reset, should delegate to underlying world
        adapter.reset(seed=42)
        assert adapter.ecosystem is not None

    def test_config_property(self):
        """Test config compatibility property."""
        adapter = TankWorldBackendAdapter(
            seed=42, max_population=50, screen_width=800, screen_height=600
        )

        # Should be accessible before initialization
        config = adapter.config
        assert config.ecosystem.max_population == 50
        assert config.display.screen_width == 800
        assert config.display.screen_height == 600

    def test_rng_property(self):
        """Test rng compatibility property."""
        adapter = TankWorldBackendAdapter(seed=42)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            _ = adapter.rng

        # After reset, should delegate to underlying world
        adapter.reset(seed=42)
        assert adapter.rng is not None
        # Check that it behaves like a random.Random instance
        assert hasattr(adapter.rng, "random")
        assert hasattr(adapter.rng, "randint")

    def test_setup_method(self):
        """Test setup() compatibility method."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)

        # setup() should create and initialize the world
        adapter.setup()
        assert adapter._world is not None
        assert adapter._world.frame_count == 0
        assert len(adapter._world.entities_list) > 0

    def test_update_method(self):
        """Test update() compatibility method."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.setup()

        initial_frame = adapter.frame_count
        adapter.update()

        # Frame should advance
        assert adapter.frame_count == initial_frame + 1

        # Last step result should be stored
        assert adapter.get_last_step_result() is not None

    def test_get_stats_method(self):
        """Test get_stats() compatibility method."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)

        # Should raise error before initialization
        with pytest.raises(RuntimeError, match="World not initialized"):
            adapter.get_stats()

        # After setup, should return stats
        adapter.setup()
        stats = adapter.get_stats()
        assert isinstance(stats, dict)
        assert len(stats) > 0

    def test_get_last_step_result(self):
        """Test get_last_step_result() helper method."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)

        # Before any steps, should be None
        assert adapter.get_last_step_result() is None

        # After reset, should have a result
        adapter.reset(seed=42)
        result = adapter.get_last_step_result()
        assert result is not None
        assert isinstance(result, StepResult)
        assert result.info["frame"] == 0
        assert result.info["seed"] == 42

        # After step, should have updated result
        adapter.step()
        result = adapter.get_last_step_result()
        assert result is not None
        assert result.info["frame"] == 1

    def test_adapter_satisfies_legacy_interface(self):
        """Test that adapter satisfies the legacy TankWorld interface."""
        adapter = TankWorldBackendAdapter(seed=42, max_population=10)
        adapter.setup()

        # Check all required properties exist and work
        assert hasattr(adapter, "entities_list")
        assert hasattr(adapter, "frame_count")
        assert hasattr(adapter, "paused")
        assert hasattr(adapter, "engine")
        assert hasattr(adapter, "ecosystem")
        assert hasattr(adapter, "config")

        # Check all required methods exist and work
        assert hasattr(adapter, "setup")
        assert hasattr(adapter, "update")
        assert hasattr(adapter, "get_stats")

        # Verify they actually work
        entities = adapter.entities_list
        frame = adapter.frame_count
        paused = adapter.paused
        engine = adapter.engine
        ecosystem = adapter.ecosystem
        config = adapter.config
        stats = adapter.get_stats()

        assert isinstance(entities, list)
        assert isinstance(frame, int)
        assert isinstance(paused, bool)
        assert engine is not None
        assert ecosystem is not None
        assert config is not None
        assert isinstance(stats, dict)

    def test_reset_info_contains_frame_and_seed(self):
        """Test that reset() returns StepResult with frame and seed in info."""
        adapter = TankWorldBackendAdapter(seed=42)
        result = adapter.reset(seed=99)

        assert "frame" in result.info
        assert "seed" in result.info
        assert result.info["frame"] == 0
        assert result.info["seed"] == 99


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


class TestWorldTypeRegistryCanonical:
    """Tests for the canonical world type registry.

    These tests verify that there is exactly one registry and that
    backend and core agree on available world types.
    """

    def test_all_world_types_registered_exactly_once(self):
        """Each world type appears exactly once in the registry."""
        mode_packs = WorldRegistry.list_mode_packs()
        world_types = [mp.world_type for mp in mode_packs.values()]
        # No duplicates - each world_type should appear exactly once
        assert len(world_types) == len(
            set(world_types)
        ), f"Duplicate world types found: {world_types}"

    def test_factories_build_in_headless_mode(self):
        """All factories create valid backends in headless mode."""
        for mode_id in WorldRegistry.list_mode_packs():
            world = WorldRegistry.create_world(mode_id, seed=42, headless=True)
            assert isinstance(
                world, MultiAgentWorldBackend
            ), f"Mode '{mode_id}' did not return a MultiAgentWorldBackend"

    def test_capability_flags_match_expectations(self):
        """Capability flags are correctly set for each world type."""
        # Tank: persistent ecosystem, no actions required
        tank = WorldRegistry.get_mode_pack("tank")
        assert tank is not None
        assert tank.supports_persistence is True
        assert tank.supports_actions is False
        assert tank.supports_transfer is True
        assert tank.has_fish is True

        # Soccer: ephemeral match, requires actions
        soccer = WorldRegistry.get_mode_pack("soccer")
        assert soccer is not None
        assert soccer.supports_persistence is False
        assert soccer.supports_actions is True
        assert soccer.supports_transfer is False
        assert soccer.has_fish is False

        # Petri: similar to tank
        petri = WorldRegistry.get_mode_pack("petri")
        assert petri is not None
        assert petri.supports_persistence is True
        assert petri.supports_actions is False
        assert petri.has_fish is True

    def test_backend_and_core_registries_agree(self):
        """Backend and core return same world types."""
        from backend.world_registry import get_all_world_metadata

        backend_types = {m.mode_id for m in get_all_world_metadata()}
        core_types = set(WorldRegistry.list_mode_packs().keys())
        assert (
            backend_types == core_types
        ), f"Registry mismatch: backend={backend_types}, core={core_types}"

    def test_backend_metadata_matches_core_mode_pack(self):
        """Backend metadata mirrors core mode pack definitions."""
        from backend.world_registry import get_all_world_metadata

        for meta in get_all_world_metadata():
            mode_pack = WorldRegistry.get_mode_pack(meta.mode_id)
            assert mode_pack is not None
            assert meta.world_type == mode_pack.world_type
            assert meta.view_mode == mode_pack.default_view_mode
            assert meta.display_name == mode_pack.display_name
            assert meta.supports_persistence == mode_pack.supports_persistence
            assert meta.supports_actions == mode_pack.supports_actions
            assert meta.supports_websocket == mode_pack.supports_websocket
            assert meta.supports_transfer == mode_pack.supports_transfer
            assert meta.has_fish == mode_pack.has_fish

    def test_mode_packs_have_all_required_fields(self):
        """All mode packs have required capability fields."""
        for mode_id, mode_pack in WorldRegistry.list_mode_packs().items():
            # Check required base fields
            assert hasattr(mode_pack, "mode_id")
            assert hasattr(mode_pack, "world_type")
            assert hasattr(mode_pack, "default_view_mode")
            assert hasattr(mode_pack, "display_name")

            # Check capability fields
            assert hasattr(
                mode_pack, "supports_persistence"
            ), f"Mode '{mode_id}' missing supports_persistence"
            assert hasattr(
                mode_pack, "supports_actions"
            ), f"Mode '{mode_id}' missing supports_actions"
            assert hasattr(
                mode_pack, "supports_websocket"
            ), f"Mode '{mode_id}' missing supports_websocket"
            assert hasattr(
                mode_pack, "supports_transfer"
            ), f"Mode '{mode_id}' missing supports_transfer"
            assert hasattr(mode_pack, "has_fish"), f"Mode '{mode_id}' missing has_fish"

    def test_config_normalization_works(self):
        """Config normalization helper works for all modes."""
        from core.worlds.config_utils import normalize_config

        for mode_id in WorldRegistry.list_mode_packs():
            # Normalizing empty config should not raise
            normalized = normalize_config(mode_id, {})
            assert isinstance(normalized, dict)
            # Should have at least screen_width set (from defaults)
            if mode_id == "tank":
                assert "screen_width" in normalized
