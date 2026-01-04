from core.config.fish import OVERFLOW_ENERGY_BANK_MULTIPLIER
from core.entities import Food


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
    """Test that overflow energy from gain_energy() queues food spawns.

    In the current design, gain_energy() applies energy immediately and
    routes overflow to food spawns via request_spawn(). No separate
    _resolve_energy step is needed.
    """
    engine = simulation_engine
    fish = engine.get_fish_list()[0]

    # Set fish to max capacity in both main energy and overflow bank
    fish.energy = fish.max_energy
    fish._reproduction_component.overflow_energy_bank = (
        fish.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
    )

    before = sum(isinstance(e, Food) for e in engine.get_all_entities())
    assert engine._entity_mutations.pending_spawn_count() == 0

    # gain_energy() now applies immediately and queues overflow food
    fish.gain_energy(10.0)

    # Overflow food should be queued immediately (no separate resolve step)
    assert engine._entity_mutations.pending_spawn_count() == 1
    engine._apply_entity_mutations("test_overflow")

    after = sum(isinstance(e, Food) for e in engine.get_all_entities())
    assert after == before + 1
