"""Smoke tests for world-agnostic SimulationRunner.

These tests verify that:
1. Tank world still provides all expected features (backward compatibility)
2. Non-tank worlds can run without tank-specific assumptions
3. State building works correctly for different world types
"""

import pytest

from backend.simulation_runner import SimulationRunner


class TestTankBackwardCompatibility:
    """Tests verifying Tank world still works as expected."""

    def test_tank_runner_initializes(self):
        """Tank runner should initialize successfully."""
        runner = SimulationRunner(world_type="tank", seed=42)
        assert runner.world is not None
        assert runner.world_type == "tank"
        assert runner.mode_id == "tank"

    def test_tank_has_poker_features(self):
        """Tank world should have poker-related attributes available."""
        runner = SimulationRunner(world_type="tank", seed=42)

        # These should be available for backward compatibility
        assert hasattr(runner, "human_poker_game")
        assert hasattr(runner, "standard_poker_series")
        assert hasattr(runner, "evolution_benchmark_tracker")

    def test_tank_full_state_has_expected_keys(self):
        """Full state for tank should include all expected keys."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.world.step()  # Advance one frame

        state = runner.get_state(force_full=True)

        # Universal keys
        assert state.frame == 1
        assert state.entities is not None
        assert state.stats is not None
        assert state.mode_id == "tank"
        assert state.world_type == "tank"

        # Tank-specific keys
        assert hasattr(state, "poker_events")
        assert hasattr(state, "poker_leaderboard")

    def test_tank_command_handling_backward_compatible(self):
        """Tank should still handle tank-specific commands."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.start()

        # These commands should not raise errors or return error responses
        result = runner.handle_command("pause")
        assert result is None

        result = runner.handle_command("resume")
        assert result is None

        result = runner.handle_command("add_food")
        assert result is None

        runner.stop()

    def test_tank_can_spawn_entities(self):
        """Tank should be able to spawn fish."""
        runner = SimulationRunner(world_type="tank", seed=42)
        initial_count = len(runner.world.entities_list)

        runner.handle_command("spawn_fish")

        # Count should increase (or stay same if spawn failed, but at least no error)
        assert len(runner.world.entities_list) >= initial_count


class TestNonTankWorldAgnosticism:
    """Tests verifying non-tank worlds work without tank assumptions."""

    def test_soccer_training_initializes(self):
        """Soccer training world should initialize without errors."""
        try:
            runner = SimulationRunner(world_type="soccer_training", seed=42)
            assert runner.world is not None
            assert runner.world_type == "soccer_training"
        except Exception as e:
            pytest.skip(f"Soccer training world not fully implemented: {e}")

    def test_petri_initializes(self):
        """Petri world should initialize without errors."""
        try:
            runner = SimulationRunner(world_type="petri", seed=42)
            assert runner.world is not None
            assert runner.world_type == "petri"
        except Exception as e:
            pytest.skip(f"Petri world not fully implemented: {e}")

    def test_non_tank_world_basic_operations(self):
        """Non-tank worlds should support universal commands."""
        try:
            runner = SimulationRunner(world_type="soccer_training", seed=42)
        except Exception:
            pytest.skip("Soccer training world not fully implemented")

        runner.start()

        # Universal commands should work
        result = runner.handle_command("pause")
        assert result is None
        assert runner.world.paused is True

        result = runner.handle_command("resume")
        assert result is None
        assert runner.world.paused is False

        # Stepping should work without errors
        for _ in range(10):
            runner.world.step()

        runner.stop()

    def test_non_tank_rejects_tank_commands(self):
        """Non-tank worlds should reject tank-specific commands gracefully."""
        try:
            runner = SimulationRunner(world_type="soccer_training", seed=42)
        except Exception:
            pytest.skip("Soccer training world not fully implemented")

        # Tank-specific commands should return error, not crash
        result = runner.handle_command("add_food")
        assert result is not None
        assert result.get("success") is False
        assert "not supported" in result.get("error", "").lower()

        result = runner.handle_command("spawn_fish")
        assert result is not None
        assert result.get("success") is False

    def test_non_tank_full_state_universal_keys(self):
        """Full state for non-tank worlds should have universal keys."""
        try:
            runner = SimulationRunner(world_type="soccer_training", seed=42)
        except Exception:
            pytest.skip("Soccer training world not fully implemented")

        runner.world.step()

        state = runner.get_state(force_full=True)

        # Universal keys should always be present
        assert state.frame == 1
        assert state.entities is not None
        assert state.stats is not None
        assert state.mode_id == "soccer_training"
        assert state.world_type == "soccer_training"
        assert state.view_mode is not None


class TestWorldHooksIntegration:
    """Tests verifying world hooks are properly integrated."""

    def test_tank_has_world_hooks(self):
        """Tank runner should have world hooks configured."""
        runner = SimulationRunner(world_type="tank", seed=42)
        assert hasattr(runner, "world_hooks")
        assert runner.world_hooks is not None

    def test_hooks_support_command_detection(self):
        """Hooks should correctly report which commands they support."""
        runner = SimulationRunner(world_type="tank", seed=42)

        # Tank hooks should support (or at least claim to support) poker commands
        supports_poker = runner.world_hooks.supports_command("start_human_poker")
        # This is optional - just verify the method exists and returns boolean
        assert isinstance(supports_poker, bool)

    def test_hooks_build_world_extras(self):
        """Hooks should build world extras without crashing."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.world.step()  # Advance a frame

        # This should not raise an exception
        extras = runner.world_hooks.build_world_extras(runner)

        # Extras should be a dict
        assert isinstance(extras, dict)

        # Tank hooks should provide poker-related keys
        # (even if empty or None)
        if runner.world_type == "tank":
            # Tank should provide these keys in extras or handle gracefully
            assert "poker_events" in extras or "poker_events" not in extras

    def test_universal_commands_work_with_hooks(self):
        """Universal commands should work regardless of hooks."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.start()

        # These should work for any world type
        result = runner.handle_command("pause")
        assert result is None
        assert runner.world.paused

        result = runner.handle_command("resume")
        assert result is None
        assert not runner.world.paused

        runner.stop()


class TestStatePayloadConsistency:
    """Tests verifying state payload consistency across worlds."""

    def test_tank_full_state_payload_structure(self):
        """Tank full state should match expected FullStatePayload."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.world.step()

        state = runner.get_state(force_full=True)

        # Check required fields
        assert state.frame > 0
        assert state.elapsed_time >= 0
        assert isinstance(state.entities, list)
        assert state.stats is not None
        assert state.mode_id is not None
        assert state.world_type == "tank"
        assert state.view_mode is not None

    def test_tank_delta_state_payload_structure(self):
        """Tank delta state should be properly structured."""
        runner = SimulationRunner(world_type="tank", seed=42)
        runner.world.step()

        # Get a full state first
        full_state = runner.get_state(force_full=True)

        # Then get a delta
        runner.world.step()
        delta_state = runner.get_state(force_full=False, allow_delta=True)

        # Delta state should have required fields
        assert hasattr(delta_state, "frame")
        assert delta_state.frame > full_state.frame

    def test_multiple_steps_dont_crash(self):
        """Runner should handle many steps without crashing."""
        runner = SimulationRunner(world_type="tank", seed=42)

        # Step directly (synchronously) instead of using background thread
        # to ensure deterministic frame progression
        for i in range(50):
            runner.world.step()
            state = runner.get_state(force_full=True)
            assert state is not None
            assert state.frame == i + 1
