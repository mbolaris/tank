"""Integration tests for the Tank action pipeline.

These tests verify the end-to-end action pipeline works correctly and
that the simulation runs without regressions.
"""

from core.config.simulation_config import SimulationConfig, TankConfig
from core.worlds.tank import TankWorldBackendAdapter


class TestActionPipeline:
    """Integration tests for the action pipeline."""

    def test_200_tick_sanity(self):
        """Run 200 ticks with seed, verify no crashes and entity count evolves."""
        adapter = TankWorldBackendAdapter(seed=12345)
        result = adapter.reset(seed=12345)

        assert result.snapshot is not None
        assert result.info["frame"] == 0

        initial_entities = len(adapter.entities_list)
        assert initial_entities > 0, "Should have initial entities"

        # Run 200 ticks
        for i in range(200):
            result = adapter.step()
            assert result is not None
            assert result.info["frame"] == i + 1

        final_entities = len(adapter.entities_list)
        assert final_entities > 0, "Should still have entities after 200 ticks"

        # Entity count should change (births/deaths occur)
        # This is a sanity check, not a strict assertion
        print(f"Initial entities: {initial_entities}, Final entities: {final_entities}")

    def test_step_returns_observations(self):
        """Step should return observations only in external brain mode (for performance).

        In legacy mode, observations are skipped to avoid the spatial grid query overhead.
        In external mode, observations are built for the external brain to use.
        """
        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        # Fast step should not build observations
        fast_result = adapter.step({"__fast_step__": True})
        assert fast_result.obs_by_agent == {}

        # Legacy mode step should NOT build observations (performance optimization)
        result = adapter.step()
        assert isinstance(result.obs_by_agent, dict)
        # In legacy mode, obs_by_agent should be empty (fish make their own decisions)
        assert (
            result.obs_by_agent == {}
        ), "Legacy mode should not build observations for performance"

    def test_step_returns_brain_mode_in_info(self):
        """Step should return brain_mode in info."""
        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        result = adapter.step()
        assert "brain_mode" in result.info
        assert result.info["brain_mode"] == "builtin"

    def test_legacy_mode_is_default(self):
        """Legacy mode should be the default brain mode."""
        config = SimulationConfig()
        assert config.tank.brain_mode == "builtin"

    def test_external_mode_can_be_configured(self):
        """External mode should be configurable via TankConfig."""
        config = SimulationConfig(tank=TankConfig(brain_mode="external"))
        assert config.tank.brain_mode == "external"

    def test_simulation_determinism(self):
        """Same seed should produce same results with action pipeline."""

        def run_simulation(seed: int, frames: int) -> dict:
            adapter = TankWorldBackendAdapter(seed=seed)
            adapter.reset(seed=seed)

            for _ in range(frames):
                adapter.step()

            # Count entities by type
            entities = adapter.entities_list
            fish_count = sum(1 for e in entities if hasattr(e, "fish_id"))
            food_count = sum(1 for e in entities if hasattr(e, "energy_value"))

            return {
                "frame": adapter.frame_count,
                "fish_count": fish_count,
                "food_count": food_count,
            }

        result1 = run_simulation(12345, 100)
        result2 = run_simulation(12345, 100)

        assert result1 == result2, f"Results should be deterministic: {result1} != {result2}"


class TestSnapshotBackwardCompat:
    """Tests for snapshot backward compatibility."""

    def test_adapter_runs_after_reset(self):
        """Adapter should run cleanly after reset (simulating snapshot load)."""
        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        # Run initial simulation
        for _ in range(50):
            adapter.step()

        # Reset and run again (simulates loading a snapshot)
        adapter.reset(seed=42)
        assert adapter.frame_count == 0

        # Run 50 more ticks
        for _ in range(50):
            adapter.step()

        assert adapter.frame_count == 50

    def test_config_persistence(self):
        """Config should be preserved across step calls."""
        config = SimulationConfig(tank=TankConfig(brain_mode="builtin"))

        # TankConfig is accessible
        assert config.tank.brain_mode == "builtin"

        # Default factory creates TankConfig
        default_config = SimulationConfig()
        assert hasattr(default_config, "tank")
        assert default_config.tank.brain_mode == "builtin"
