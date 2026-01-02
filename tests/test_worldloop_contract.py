"""Tests for world loop contract compliance.

These tests verify that all world backends conform to the world loop contract:
- reset() and step() return StepResult with required fields
- render_hint is always present in snapshots
- Entity mutations only occur at designated commit points
- Determinism under fixed seed
"""

from __future__ import annotations

import pytest

from core.worlds.contracts import (
    ALL_WORLD_TYPES,
    RenderHint,
    WorldType,
    get_default_render_hint,
    is_valid_world_type,
)
from core.worlds.interfaces import StepResult


class TestWorldTypeDefinitions:
    """Tests for WorldType and related helpers."""

    def test_all_world_types_contains_expected(self) -> None:
        """ALL_WORLD_TYPES contains the canonical world types."""
        assert "tank" in ALL_WORLD_TYPES
        assert "petri" in ALL_WORLD_TYPES
        assert "soccer" in ALL_WORLD_TYPES
        assert "soccer_training" in ALL_WORLD_TYPES

    def test_is_valid_world_type_valid(self) -> None:
        """is_valid_world_type returns True for valid types."""
        assert is_valid_world_type("tank") is True
        assert is_valid_world_type("petri") is True
        assert is_valid_world_type("soccer") is True

    def test_is_valid_world_type_invalid(self) -> None:
        """is_valid_world_type returns False for invalid types."""
        assert is_valid_world_type("invalid") is False
        assert is_valid_world_type("") is False
        assert is_valid_world_type("TANK") is False  # Case sensitive


class TestRenderHint:
    """Tests for RenderHint dataclass."""

    def test_default_render_hint(self) -> None:
        """Default RenderHint has expected values."""
        hint = RenderHint()
        assert hint.style == "side"
        assert hint.entity_style is None
        assert hint.camera == {}
        assert hint.extra == {}

    def test_render_hint_to_dict(self) -> None:
        """RenderHint.to_dict() produces serializable dict."""
        hint = RenderHint(style="topdown", entity_style="microbe")
        result = hint.to_dict()
        assert result["style"] == "topdown"
        assert result["entity_style"] == "microbe"

    def test_get_default_render_hint_tank(self) -> None:
        """get_default_render_hint returns correct hint for tank."""
        hint = get_default_render_hint("tank")
        assert hint.style == "side"
        assert hint.entity_style == "fish"

    def test_get_default_render_hint_petri(self) -> None:
        """get_default_render_hint returns correct hint for petri."""
        hint = get_default_render_hint("petri")
        assert hint.style == "topdown"
        assert hint.entity_style == "microbe"

    def test_get_default_render_hint_unknown(self) -> None:
        """get_default_render_hint falls back to tank for unknown types."""
        hint = get_default_render_hint("unknown")
        assert hint.style == "side"
        assert hint.entity_style == "fish"


class TestStepResultExtendedFields:
    """Tests for extended StepResult fields."""

    def test_step_result_has_extended_fields(self) -> None:
        """StepResult has spawns, removals, energy_deltas, render_hint."""
        result = StepResult()
        assert hasattr(result, "spawns")
        assert hasattr(result, "removals")
        assert hasattr(result, "energy_deltas")
        assert hasattr(result, "render_hint")

    def test_step_result_extended_fields_default_empty(self) -> None:
        """Extended fields default to empty lists/None."""
        result = StepResult()
        assert result.spawns == []
        assert result.removals == []
        assert result.energy_deltas == []
        assert result.render_hint is None

    def test_step_result_with_extended_fields(self) -> None:
        """StepResult can be created with extended fields populated."""
        result = StepResult(
            spawns=[{"entity_type": "fish", "entity_id": "1"}],
            removals=[{"entity_id": "2", "reason": "death"}],
            energy_deltas=[{"entity_id": "1", "delta": -10.0}],
            render_hint={"style": "side", "entity_style": "fish"},
        )
        assert len(result.spawns) == 1
        assert len(result.removals) == 1
        assert len(result.energy_deltas) == 1
        assert result.render_hint["style"] == "side"


class TestTankWorldLoopContract:
    """Tests for Tank world loop contract compliance."""

    def test_tank_reset_returns_step_result(self) -> None:
        """Tank reset() returns StepResult with required fields."""
        from core.worlds.tank.backend import TankWorldBackendAdapter

        backend = TankWorldBackendAdapter(seed=42)
        result = backend.reset(seed=42)

        assert isinstance(result, StepResult)
        assert isinstance(result.snapshot, dict)
        assert isinstance(result.metrics, dict)
        assert isinstance(result.events, list)
        assert result.done is False

    def test_tank_step_returns_step_result(self) -> None:
        """Tank step() returns StepResult with required fields."""
        from core.worlds.tank.backend import TankWorldBackendAdapter

        backend = TankWorldBackendAdapter(seed=42)
        backend.reset(seed=42)
        result = backend.step()

        assert isinstance(result, StepResult)
        assert isinstance(result.snapshot, dict)

    def test_tank_has_world_type_property(self) -> None:
        """Tank backend has world_type property returning 'tank'."""
        from core.worlds.tank.backend import TankWorldBackendAdapter

        backend = TankWorldBackendAdapter(seed=42)
        assert backend.world_type == "tank"

    def test_tank_render_hint_present_in_snapshot(self) -> None:
        """Tank snapshot includes render_hint."""
        from core.worlds.tank.backend import TankWorldBackendAdapter

        backend = TankWorldBackendAdapter(seed=42)
        backend.reset(seed=42)

        snapshot = backend.get_current_snapshot()
        assert "render_hint" in snapshot
        assert snapshot["render_hint"]["style"] == "side"
        assert snapshot["render_hint"]["entity_style"] == "fish"

    def test_tank_determinism_fixed_seed(self) -> None:
        """Same seed produces identical results in Tank."""
        from core.worlds.tank.backend import TankWorldBackendAdapter

        # Run 1
        backend1 = TankWorldBackendAdapter(seed=12345)
        backend1.reset(seed=12345)
        for _ in range(10):
            backend1.step()
        snapshot1 = backend1.get_debug_snapshot()

        # Run 2
        backend2 = TankWorldBackendAdapter(seed=12345)
        backend2.reset(seed=12345)
        for _ in range(10):
            backend2.step()
        snapshot2 = backend2.get_debug_snapshot()

        # Compare frame counts (basic determinism check)
        assert snapshot1["frame"] == snapshot2["frame"]
        # Compare entity counts
        assert len(snapshot1.get("entities", [])) == len(snapshot2.get("entities", []))


class TestPetriWorldLoopContract:
    """Tests for Petri world loop contract compliance."""

    def test_petri_reset_returns_step_result(self) -> None:
        """Petri reset() returns StepResult with required fields."""
        from core.worlds.petri.backend import PetriWorldBackendAdapter

        backend = PetriWorldBackendAdapter(seed=42)
        result = backend.reset(seed=42)

        assert isinstance(result, StepResult)
        assert isinstance(result.snapshot, dict)
        assert result.snapshot.get("world_type") == "petri"

    def test_petri_has_world_type_property(self) -> None:
        """Petri backend has world_type property returning 'petri'."""
        from core.worlds.petri.backend import PetriWorldBackendAdapter

        backend = PetriWorldBackendAdapter(seed=42)
        assert backend.world_type == "petri"

    def test_petri_render_hint_present_in_snapshot(self) -> None:
        """Petri snapshot includes render_hint with topdown style."""
        from core.worlds.petri.backend import PetriWorldBackendAdapter

        backend = PetriWorldBackendAdapter(seed=42)
        backend.reset(seed=42)

        snapshot = backend.get_current_snapshot()
        assert "render_hint" in snapshot
        assert snapshot["render_hint"]["style"] == "topdown"
        assert snapshot["render_hint"]["entity_style"] == "microbe"

    def test_petri_step_result_has_render_hint(self) -> None:
        """Petri StepResult.render_hint is populated."""
        from core.worlds.petri.backend import PetriWorldBackendAdapter

        backend = PetriWorldBackendAdapter(seed=42)
        backend.reset(seed=42)
        result = backend.step()

        assert result.render_hint is not None
        assert result.render_hint["style"] == "topdown"


class TestActionRegistry:
    """Tests for ActionRegistry."""

    def test_get_action_space_tank(self) -> None:
        """get_action_space returns Tank action space."""
        # Import to trigger registration
        import core.worlds.tank.tank_actions  # noqa: F401
        from core.actions.action_registry import get_action_space

        space = get_action_space("tank")
        assert space is not None
        assert "movement" in space
        assert space["movement"]["type"] == "continuous"

    def test_get_action_space_missing_returns_none(self) -> None:
        """get_action_space returns None for unregistered world type."""
        from core.actions.action_registry import get_action_space

        space = get_action_space("nonexistent_world_type_xyz")
        assert space is None

    def test_translate_action_tank(self) -> None:
        """translate_action works for Tank world."""
        import core.worlds.tank.tank_actions  # noqa: F401
        from core.actions.action_registry import translate_action
        from core.sim.contracts import Action

        action = translate_action("tank", "fish_1", {"velocity": (1.0, 2.0)})
        assert isinstance(action, Action)
        assert action.entity_id == "fish_1"
        assert action.target_velocity == (1.0, 2.0)

    def test_translate_action_missing_raises(self) -> None:
        """translate_action raises for unregistered world type."""
        from core.actions.action_registry import translate_action

        with pytest.raises(ValueError, match="No action translator"):
            translate_action("nonexistent_world_type_xyz", "agent_1", {})

    def test_translate_action_or_default(self) -> None:
        """translate_action_or_default falls back gracefully."""
        from core.actions.action_registry import translate_action_or_default
        from core.sim.contracts import Action

        action = translate_action_or_default("nonexistent", "agent_1", (1.0, 2.0))
        assert isinstance(action, Action)
        assert action.target_velocity == (1.0, 2.0)

    def test_list_registered_translators(self) -> None:
        """list_registered_translators returns world types."""
        import core.worlds.tank.tank_actions  # noqa: F401
        from core.actions.action_registry import list_registered_translators

        translators = list_registered_translators()
        assert "tank" in translators
        assert "petri" in translators  # Petri uses Tank translator


class TestNoMutationsOutsideCommit:
    """Tests verifying mutation ownership rules."""

    def test_add_entity_during_phase_raises(self) -> None:
        """Direct add_entity during phase raises RuntimeError."""
        from core.simulation.engine import SimulationEngine

        engine = SimulationEngine(seed=42)
        engine.setup()

        # Get an existing fish to use as a template
        fish_list = engine.get_fish_list()
        if not fish_list:
            pytest.skip("No fish available for test")

        fish = fish_list[0]

        # Simulate being in a phase
        from core.update_phases import UpdatePhase

        engine._current_phase = UpdatePhase.ENTITY_ACT

        # Attempting direct add should raise
        with pytest.raises(RuntimeError, match="Unsafe call to add_entity"):
            engine.add_entity(fish)

        # Cleanup
        engine._current_phase = None

    def test_remove_entity_during_phase_raises(self) -> None:
        """Direct remove_entity during phase raises RuntimeError."""
        from core.simulation.engine import SimulationEngine

        engine = SimulationEngine(seed=42)
        engine.setup()

        # Simulate being in a phase
        from core.update_phases import UpdatePhase

        engine._current_phase = UpdatePhase.ENTITY_ACT

        # Get an entity to attempt removal
        entities = engine.entities_list
        if entities:
            with pytest.raises(RuntimeError, match="Unsafe call to remove_entity"):
                engine.remove_entity(entities[0])

        # Cleanup
        engine._current_phase = None

    def test_request_spawn_during_phase_succeeds(self) -> None:
        """request_spawn during phase succeeds (proper mutation path)."""
        from core.simulation.engine import SimulationEngine

        engine = SimulationEngine(seed=42)
        engine.setup()

        # Get an existing fish to test spawn request
        fish_list = engine.get_fish_list()
        if not fish_list:
            pytest.skip("No fish available for test")

        fish = fish_list[0]

        # Simulate being in a phase
        from core.update_phases import UpdatePhase

        engine._current_phase = UpdatePhase.ENTITY_ACT

        # request_spawn should succeed (even if the entity is already in the list,
        # the request mechanism should accept it)
        result = engine.request_spawn(fish, reason="test")
        # Note: May return False if entity already exists, but should not raise
        assert result is True or result is False  # Just verify it doesn't raise

        # Cleanup
        engine._current_phase = None
