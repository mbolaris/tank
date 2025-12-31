import pytest

from core.config.fish import OVERFLOW_ENERGY_BANK_MULTIPLIER
from core.entities import Food
from core.simulation.entity_manager import MutationLockError


def test_collision_removal_is_queued(simulation_engine):
    engine = simulation_engine
    fish = engine.get_fish_list()[0]
    fish.energy = fish.max_energy * 0.2

    food = Food(engine.environment, fish.pos.x, fish.pos.y, food_type="energy")
    food.energy = 0.05
    food.max_energy = 0.05
    engine.request_spawn(food, reason="test")
    engine._apply_entity_mutations("test_setup")

    assert food in engine.get_all_entities()
    assert engine._entity_mutations.pending_removal_count() == 0

    engine.collision_system.update(engine.frame_count)

    assert engine._entity_mutations.is_pending_removal(food)
    assert food in engine.get_all_entities()

    engine._apply_entity_mutations("test_collision")
    assert food not in engine.get_all_entities()


def test_overflow_energy_spawns_food_via_queue(simulation_engine):
    engine = simulation_engine
    fish = engine.get_fish_list()[0]

    fish.energy = fish.max_energy
    fish._reproduction_component.overflow_energy_bank = (
        fish.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
    )

    before = sum(isinstance(e, Food) for e in engine.get_all_entities())
    assert engine._entity_mutations.pending_spawn_count() == 0

    fish.gain_energy(10.0)

    assert engine._entity_mutations.pending_spawn_count() == 1
    engine._apply_entity_mutations("test_overflow")

    after = sum(isinstance(e, Food) for e in engine.get_all_entities())
    assert after == before + 1


def test_mutation_lock_prevents_direct_add(simulation_engine):
    """Verify that direct entity additions raise during update loop."""
    engine = simulation_engine

    # Create a food entity to add
    food = Food(engine.environment, 100, 100, food_type="energy")

    # Manually lock mutations (simulating being inside update loop)
    engine._entity_manager.lock_mutations("test_phase")

    # Attempting to add directly should raise MutationLockError
    with pytest.raises(MutationLockError) as exc_info:
        engine._entity_manager.add(food)

    assert "Cannot add entity during test_phase phase" in str(exc_info.value)
    assert "request_spawn" in str(exc_info.value)

    # Unlock and verify add works
    engine._entity_manager.unlock_mutations()
    result = engine._entity_manager.add(food)
    assert result is True
    assert food in engine.get_all_entities()


def test_mutation_lock_prevents_direct_remove(simulation_engine):
    """Verify that direct entity removals raise during update loop."""
    engine = simulation_engine
    fish = engine.get_fish_list()[0]

    # Manually lock mutations (simulating being inside update loop)
    engine._entity_manager.lock_mutations("test_phase")

    # Attempting to remove directly should raise MutationLockError
    with pytest.raises(MutationLockError) as exc_info:
        engine._entity_manager.remove(fish)

    assert "Cannot remove entity during test_phase phase" in str(exc_info.value)
    assert "request_remove" in str(exc_info.value)

    # Unlock and verify remove works
    engine._entity_manager.unlock_mutations()
    engine._entity_manager.remove(fish)
    assert fish not in engine.get_all_entities()


def test_internal_flag_bypasses_mutation_lock(simulation_engine):
    """Verify that _internal=True bypasses the mutation lock.

    This is used by the engine when applying queued mutations.
    """
    engine = simulation_engine

    food = Food(engine.environment, 100, 100, food_type="energy")

    # Lock mutations
    engine._entity_manager.lock_mutations("test_phase")

    # Direct add should raise
    with pytest.raises(MutationLockError):
        engine._entity_manager.add(food)

    # But _internal=True should work
    result = engine._entity_manager.add(food, _internal=True)
    assert result is True
    assert food in engine.get_all_entities()

    # Same for remove
    with pytest.raises(MutationLockError):
        engine._entity_manager.remove(food)

    engine._entity_manager.remove(food, _internal=True)
    assert food not in engine.get_all_entities()

    engine._entity_manager.unlock_mutations()


def test_entity_collection_stable_during_collision_phase(simulation_engine):
    """Verify entity collection remains stable during collision processing.

    When collision system processes collisions and removes food, the food
    should remain in the collection until the mutation flush.
    """
    engine = simulation_engine
    fish = engine.get_fish_list()[0]
    fish.energy = fish.max_energy * 0.2

    # Create food at fish position
    food = Food(engine.environment, fish.pos.x, fish.pos.y, food_type="energy")
    food.energy = 0.05
    food.max_energy = 0.05
    engine.request_spawn(food, reason="test")
    engine._apply_entity_mutations("test_setup")

    initial_entities = set(engine.get_all_entities())
    assert food in initial_entities

    # Process collision - this should queue removal but not modify collection
    engine._entity_manager.lock_mutations("collision")

    engine.collision_system.update(engine.frame_count)

    # Entity collection should be unchanged
    current_entities = set(engine.get_all_entities())
    assert current_entities == initial_entities
    assert food in current_entities

    # But removal should be queued
    assert engine._entity_mutations.is_pending_removal(food)

    engine._entity_manager.unlock_mutations()

    # Now apply mutations
    engine._apply_entity_mutations("test_collision")
    assert food not in engine.get_all_entities()


def test_update_loop_locks_and_unlocks_mutations(simulation_engine):
    """Verify the update loop properly locks and unlocks mutations."""
    engine = simulation_engine

    # Initially mutations should not be locked
    assert not engine._entity_manager.mutation_locked

    # Run one frame
    engine.update()

    # After update, mutations should be unlocked again
    assert not engine._entity_manager.mutation_locked
