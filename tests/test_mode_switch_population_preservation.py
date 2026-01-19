"""Tests for tank↔petri mode switching with population preservation.

These tests verify that:
1. Entities (fish/plants) survive mode switches without being replaced
2. Entity state (energy, generation, age) is preserved across switches
3. Petri dish physics are correctly applied/removed during switching
4. Rendering switches between tank and petri styles appropriately
"""

import pytest

from backend.simulation_runner import SimulationRunner
from core.entities import Fish, Plant


class TestModeSwitchPopulationPreservation:
    """Tests verifying population is preserved during mode switches."""

    def test_tank_to_petri_preserves_entity_instances(self):
        """After tank→petri switch, the same entity instances should exist."""
        runner = SimulationRunner(world_type="tank", seed=42)

        # Step a few frames to let the population stabilize
        for _ in range(10):
            runner.world.step()

        # Record entity identities before switch
        entities_before = list(runner.world.entities_list)
        entity_ids_before = {id(e) for e in entities_before}
        fish_before = [e for e in entities_before if isinstance(e, Fish)]

        assert len(fish_before) > 0, "Should have fish before switch"

        # Switch to petri mode
        runner.switch_world_type("petri")

        # Verify entity instances are preserved
        entities_after = list(runner.world.entities_list)
        entity_ids_after = {id(e) for e in entities_after}

        # The same Python object instances should exist
        assert entity_ids_before == entity_ids_after, (
            f"Entity instances changed after switch. "
            f"Before: {len(entity_ids_before)}, After: {len(entity_ids_after)}"
        )

    def test_tank_to_petri_preserves_fish_state(self):
        """Fish should retain their state (energy, generation, age) after switch."""
        runner = SimulationRunner(world_type="tank", seed=42)

        # Step frames
        for _ in range(20):
            runner.world.step()

        # Record fish states
        fish_before = [e for e in runner.world.entities_list if isinstance(e, Fish)]
        assert len(fish_before) > 0, "Should have fish"

        fish_states_before = {
            id(fish): {
                "energy": fish.energy,
                "generation": fish.generation,
                "age": fish._lifecycle_component.age,
                "fish_id": fish.fish_id,
            }
            for fish in fish_before
        }

        # Switch mode
        runner.switch_world_type("petri")

        # Verify states are preserved
        fish_after = [e for e in runner.world.entities_list if isinstance(e, Fish)]

        for fish in fish_after:
            fish_id = id(fish)
            if fish_id in fish_states_before:
                before = fish_states_before[fish_id]
                assert fish.energy == before["energy"], f"Energy changed for fish {fish.fish_id}"
                assert fish.generation == before["generation"], f"Generation changed for fish {fish.fish_id}"
                assert fish._lifecycle_component.age == before["age"], f"Age changed for fish {fish.fish_id}"

    def test_round_trip_preserves_population(self):
        """After tank→petri→tank, entities should still be the same instances."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        entities_original = list(runner.world.entities_list)
        entity_ids_original = {id(e) for e in entities_original}

        # Round trip
        runner.switch_world_type("petri")
        runner.switch_world_type("tank")

        entities_final = list(runner.world.entities_list)
        entity_ids_final = {id(e) for e in entities_final}

        # Should be identical (excluding any natural births/deaths)
        assert entity_ids_original == entity_ids_final, (
            "Entity instances changed after round-trip switch"
        )


class TestModeSwitchPhysics:
    """Tests verifying physics constraints work correctly after switching."""

    def test_petri_dish_physics_active_after_switch(self):
        """After tank→petri switch, circular boundary physics should be active."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        runner.switch_world_type("petri")

        # The environment should have the dish and boundary resolver
        env = runner.engine.environment
        assert hasattr(env, "dish") and env.dish is not None, (
            "Petri dish should be set on environment after switch"
        )
        assert hasattr(env, "resolve_boundary_collision") and callable(
            getattr(env, "resolve_boundary_collision", None)
        ), "resolve_boundary_collision should be installed on environment after switch"

    def test_tank_physics_restored_after_switch_back(self):
        """After petri→tank switch, circular boundary physics should be removed."""
        runner = SimulationRunner(world_type="petri", seed=42)

        for _ in range(10):
            runner.world.step()

        runner.switch_world_type("tank")

        # The environment should not have dish or should be None
        env = runner.engine.environment
        dish = getattr(env, "dish", None)
        assert dish is None, "Dish should be removed after switching back to tank"

        # resolve_boundary_collision should be None or not present
        resolver = getattr(env, "resolve_boundary_collision", None)
        assert resolver is None, (
            "resolve_boundary_collision should be removed after switching to tank"
        )

    def test_entities_respect_dish_boundary_after_switch(self):
        """After switch to petri, mobile entities should be clamped to dish boundary."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        runner.switch_world_type("petri")

        env = runner.engine.environment
        dish = env.dish

        # Mobile entities (Fish, Food, Crab) should be inside the dish
        # Plants are intentionally relocated to perimeter spots (they grow from edge)
        for entity in runner.world.entities_list:
            if not hasattr(entity, "pos"):
                continue

            # Skip plants (they're relocated to perimeter spots intentionally)
            if isinstance(entity, Plant):
                continue

            # Calculate center of entity
            cx = entity.pos.x + entity.width / 2
            cy = entity.pos.y + getattr(entity, "height", entity.width) / 2

            # Distance from dish center
            dx = cx - dish.cx
            dy = cy - dish.cy
            dist = (dx * dx + dy * dy) ** 0.5

            # Entity center should be within dish (with some margin for entity radius)
            entity_r = max(entity.width, getattr(entity, "height", entity.width)) / 2
            assert dist <= dish.r + entity_r, (
                f"Entity {type(entity).__name__} at ({cx}, {cy}) is outside dish boundary (dist={dist}, r={dish.r})"
            )


class TestModeSwitchRendering:
    """Tests verifying rendering switches correctly between modes."""

    def test_petri_snapshot_builder_after_switch(self):
        """After tank→petri switch, snapshot builder should produce petri hints."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        runner.switch_world_type("petri")

        # Get snapshots
        snapshots = runner._entity_snapshot_builder.collect(runner.world.entities_list)

        # Fish should have petri-style render hints
        fish_snapshots = [s for s in snapshots if s.type == "fish"]
        if fish_snapshots:
            for snapshot in fish_snapshots:
                hint = snapshot.render_hint
                assert hint is not None, "Fish should have render hint"
                assert hint.get("style") == "petri", (
                    f"Fish render hint should be 'petri' style, got {hint.get('style')}"
                )

    def test_tank_snapshot_builder_after_switch_back(self):
        """After petri→tank switch, snapshot builder should produce tank hints."""
        runner = SimulationRunner(world_type="petri", seed=42)

        for _ in range(10):
            runner.world.step()

        runner.switch_world_type("tank")

        # Get snapshots
        snapshots = runner._entity_snapshot_builder.collect(runner.world.entities_list)

        # Fish should have tank-style (pixel) render hints
        fish_snapshots = [s for s in snapshots if s.type == "fish"]
        if fish_snapshots:
            for snapshot in fish_snapshots:
                hint = snapshot.render_hint
                assert hint is not None, "Fish should have render hint"
                # Tank uses "pixel" style
                assert hint.get("style") == "pixel", (
                    f"Fish render hint should be 'pixel' style, got {hint.get('style')}"
                )


class TestModeSwitchHookSequencing:
    """Tests verifying correct hook sequencing during mode switches."""

    def test_old_type_passed_correctly_to_hooks(self):
        """on_world_type_switch should receive correct old/new type values."""
        from backend.runner.hooks.petri_hooks import PetriWorldHooks

        runner = SimulationRunner(world_type="tank", seed=42)

        # Track what gets passed to on_world_type_switch
        # We need to patch the class method since hooks are replaced during switch
        calls = []
        original_switch = PetriWorldHooks.on_world_type_switch

        def tracking_switch(self, runner_arg, old_type, new_type):
            calls.append((old_type, new_type))
            return original_switch(self, runner_arg, old_type, new_type)

        PetriWorldHooks.on_world_type_switch = tracking_switch

        try:
            runner.switch_world_type("petri")

            # Should be called with correct values (old=tank, new=petri)
            assert len(calls) >= 1, "on_world_type_switch should be called"
            old_type, new_type = calls[-1]
            assert old_type == "tank", f"Old type should be 'tank', got '{old_type}'"
            assert new_type == "petri", f"New type should be 'petri', got '{new_type}'"
        finally:
            # Restore original method
            PetriWorldHooks.on_world_type_switch = original_switch


class TestModeSwitchIdempotency:
    """Tests verifying mode switching is idempotent and stable."""

    def test_switching_to_same_mode_is_noop(self):
        """Switching to the current mode should be a no-op."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        entities_before = list(runner.world.entities_list)

        # Switch to same mode
        runner.switch_world_type("tank")

        entities_after = list(runner.world.entities_list)

        assert {id(e) for e in entities_before} == {id(e) for e in entities_after}

    def test_multiple_switches_preserve_population(self):
        """Multiple rapid switches should preserve the population."""
        runner = SimulationRunner(world_type="tank", seed=42)

        for _ in range(10):
            runner.world.step()

        entities_original = list(runner.world.entities_list)

        # Multiple switches
        for _ in range(5):
            runner.switch_world_type("petri")
            runner.switch_world_type("tank")

        entities_final = list(runner.world.entities_list)

        assert {id(e) for e in entities_original} == {id(e) for e in entities_final}
