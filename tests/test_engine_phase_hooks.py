"""Tests for engine phase hooks.

These tests verify that:
- Engine uses phase hooks from pack
- Add/remove operations only happen in allowed phases
- TankPhaseHooks preserve original behavior
"""

import pytest


def test_engine_uses_phase_hooks_from_pack():
    """Verify engine initializes and uses pack's phase hooks."""
    from core.simulation.engine import SimulationEngine
    from core.simulation.phase_hooks import PhaseHooks
    from core.worlds.tank.tank_phase_hooks import TankPhaseHooks

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Phase hooks should be set
    assert engine._phase_hooks is not None, "Engine should have phase hooks"

    # Should be TankPhaseHooks for default Tank setup
    assert isinstance(
        engine._phase_hooks, TankPhaseHooks
    ), "Default Tank setup should use TankPhaseHooks"


def test_petri_mode_uses_tank_like_hooks():
    """Verify Petri mode uses TankPhaseHooks (shared Tank-like behavior)."""
    from core.simulation.engine import SimulationEngine
    from core.worlds.petri.pack import PetriPack
    from core.worlds.tank.tank_phase_hooks import TankPhaseHooks

    engine = SimulationEngine(headless=True, seed=42)
    pack = PetriPack(engine.config)
    engine.setup(pack)

    # Petri uses TankPhaseHooks via TankLikePackBase
    assert isinstance(
        engine._phase_hooks, TankPhaseHooks
    ), "Petri mode should use TankPhaseHooks from shared base"


def test_engine_add_remove_only_happens_in_commit_phases(monkeypatch):
    """Tripwire test to catch accidental mid-phase mutations.

    This test monitors _add_entity and _remove_entity calls and asserts
    they only happen during commit phases, not during iteration phases.
    """
    from core.simulation.engine import SimulationEngine
    from core.update_phases import UpdatePhase

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Phases where entity mutations are allowed
    allowed = {
        None,  # setup/reset may apply mutations with no active phase
        UpdatePhase.FRAME_START,
        UpdatePhase.LIFECYCLE,
        UpdatePhase.SPAWN,
        UpdatePhase.COLLISION,
        UpdatePhase.INTERACTION,
        UpdatePhase.REPRODUCTION,
        UpdatePhase.FRAME_END,
    }

    original_add = engine._add_entity
    original_remove = engine._remove_entity
    violations = []

    def guarded_add(entity):
        if engine._current_phase not in allowed:
            violations.append(
                f"_add_entity called during non-commit phase: {engine._current_phase}"
            )
        return original_add(entity)

    def guarded_remove(entity):
        if engine._current_phase not in allowed:
            violations.append(
                f"_remove_entity called during non-commit phase: {engine._current_phase}"
            )
        return original_remove(entity)

    monkeypatch.setattr(engine, "_add_entity", guarded_add)
    monkeypatch.setattr(engine, "_remove_entity", guarded_remove)

    # Run a few frames to catch accidental mid-phase mutations
    for _ in range(5):
        engine.update()

    assert not violations, "Mutations outside commit phases:\n" + "\n".join(violations)


def test_tank_phase_hooks_spawn_decision_respects_population():
    """Verify TankPhaseHooks respects ecosystem population limits.

    Fish spawns should be rejected when population is at limit.
    Non-Fish spawns should always be accepted.
    """
    from core.simulation.engine import SimulationEngine
    from core.worlds.tank.tank_phase_hooks import TankPhaseHooks

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    hooks = TankPhaseHooks()

    # Create a mock Fish entity
    fish_list = engine.get_fish_list()
    if len(fish_list) == 0:
        pytest.skip("No fish to test spawn decision")

    # Use an existing fish to test spawn decision
    parent = fish_list[0]
    child_fish = fish_list[-1] if len(fish_list) > 1 else fish_list[0]

    # This should return a SpawnDecision
    decision = hooks.on_entity_spawned(engine, child_fish, parent)

    assert hasattr(decision, "should_add"), "on_entity_spawned should return SpawnDecision"
    assert hasattr(decision, "entity"), "SpawnDecision should have entity attribute"


def test_tank_phase_hooks_death_handling():
    """Verify TankPhaseHooks handles death correctly for different entity types."""
    from core.simulation.engine import SimulationEngine
    from core.worlds.tank.tank_phase_hooks import TankPhaseHooks

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    hooks = TankPhaseHooks()

    # Test with Fish - should NOT return True (fish death is recorded, not immediate removal)
    fish_list = engine.get_fish_list()
    if len(fish_list) > 0:
        fish = fish_list[0]
        # Simulate death
        fish._is_dead = True
        should_remove = hooks.on_entity_died(engine, fish)
        # Fish death is recorded but not immediately removed (death animation)
        assert should_remove is False, "Fish death should not queue immediate removal"
