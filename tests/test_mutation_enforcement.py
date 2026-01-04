"""Tests to verify mutation ownership enforcement.

This module tests that the engine properly guards against unsafe
mid-phase mutations, ensuring all game logic uses the mutation queue.
"""

import pytest

from core.entities import Fish, Food
from core.movement_strategy import AlgorithmicMovement
from core.update_phases import UpdatePhase


def test_direct_mutation_blocked_during_collision_phase(simulation_engine):
    """Verify add_entity/remove_entity raise errors during COLLISION phase."""
    engine = simulation_engine
    env = engine.environment

    # Create test entity
    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )

    # Direct mutations should work before tick starts (phase is None)
    assert engine._current_phase is None
    engine.add_entity(fish)
    assert fish in engine.get_all_entities()

    # Simulate being mid-tick (engine sets this during update())
    engine._current_phase = UpdatePhase.COLLISION

    # Direct add_entity should raise error
    new_fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=150,
        y=150,
        speed=2.0,
    )
    with pytest.raises(RuntimeError, match="Unsafe call to add_entity.*COLLISION.*request_spawn"):
        engine.add_entity(new_fish)

    # Direct remove_entity should raise error
    with pytest.raises(
        RuntimeError, match="Unsafe call to remove_entity.*COLLISION.*request_remove"
    ):
        engine.remove_entity(fish)

    # Verify entity wasn't modified
    assert fish in engine.get_all_entities()
    assert new_fish not in engine.get_all_entities()

    # Reset phase
    engine._current_phase = None


def test_direct_mutation_blocked_during_reproduction_phase(simulation_engine):
    """Verify add_entity/remove_entity raise errors during REPRODUCTION phase."""
    engine = simulation_engine
    env = engine.environment

    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    engine.add_entity(fish)

    # Simulate being in REPRODUCTION phase
    engine._current_phase = UpdatePhase.REPRODUCTION

    new_fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=150,
        y=150,
        speed=2.0,
    )
    with pytest.raises(RuntimeError, match="Unsafe call to add_entity.*REPRODUCTION"):
        engine.add_entity(new_fish)

    with pytest.raises(RuntimeError, match="Unsafe call to remove_entity.*REPRODUCTION"):
        engine.remove_entity(fish)

    # Reset phase
    engine._current_phase = None


def test_request_api_works_during_any_phase(simulation_engine):
    """Verify request_spawn/request_remove work regardless of phase."""
    engine = simulation_engine
    env = engine.environment

    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    food = Food(env, 200, 200, food_type="energy")

    # Test during different phases
    for phase in [UpdatePhase.COLLISION, UpdatePhase.REPRODUCTION, UpdatePhase.SPAWN]:
        engine._current_phase = phase

        # Request API should work during any phase
        assert engine.request_spawn(fish, reason="test_spawn") is True
        assert engine.request_remove(food, reason="test_remove") is True

        # Verify they're queued but not applied yet
        assert engine._entity_mutations.pending_spawn_count() > 0
        assert engine._entity_mutations.pending_removal_count() > 0

        # Clear the queue for next iteration
        engine._entity_mutations.drain_spawns()
        engine._entity_mutations.drain_removals()

    # Reset phase
    engine._current_phase = None


def test_direct_mutation_allowed_outside_tick(simulation_engine):
    """Verify add_entity/remove_entity work when phase is None (setup/persistence)."""
    engine = simulation_engine
    env = engine.environment

    # Explicitly ensure we're outside a tick
    assert engine._current_phase is None

    # These should work (privileged infrastructure operations)
    fish1 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    fish2 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=200,
        y=200,
        speed=2.0,
    )
    food = Food(env, 150, 150, food_type="energy")

    engine.add_entity(fish1)
    engine.add_entity(fish2)
    engine.add_entity(food)

    assert fish1 in engine.get_all_entities()
    assert fish2 in engine.get_all_entities()
    assert food in engine.get_all_entities()

    engine.remove_entity(fish2)
    assert fish2 not in engine.get_all_entities()
    assert fish1 in engine.get_all_entities()


def test_mutation_queue_deduplication(simulation_engine):
    """Verify queue prevents duplicate spawn/remove requests."""
    engine = simulation_engine
    env = engine.environment

    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )

    # First spawn request should succeed
    assert engine.request_spawn(fish, reason="first") is True
    assert engine._entity_mutations.pending_spawn_count() == 1

    # Second spawn request for same entity should fail (deduplication)
    assert engine.request_spawn(fish, reason="duplicate") is False
    assert engine._entity_mutations.pending_spawn_count() == 1

    # Remove request should cancel pending spawn
    assert engine.request_remove(fish, reason="cancel") is True
    assert engine._entity_mutations.pending_spawn_count() == 0
    assert engine._entity_mutations.pending_removal_count() == 1


def test_phase_tracking_during_full_update(simulation_engine):
    """Verify _current_phase is set/cleared correctly during update()."""
    engine = simulation_engine

    # Before update, phase should be None
    assert engine._current_phase is None

    # After full update, phase should be back to None
    engine.update()
    assert engine._current_phase is None

    # Verify we can still do privileged operations
    env = engine.environment
    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    engine.add_entity(fish)  # Should not raise
    engine.remove_entity(fish)  # Should not raise
