from core.entities import Crab, Food
from core.math_utils import Vector2
from core.worlds import WorldRegistry


def test_crab_eats_food_optimization():
    # Setup world via canonical path
    world = WorldRegistry.create_world("tank", seed=42, headless=True)
    world.reset(seed=42)

    # Clear existing entities to ensure only our test crab and food are present
    # This prevents other fish from eating the food before the crab
    # Use the entity manager's clear method for proper cleanup
    world.world.engine._entity_manager.clear()

    # Create crab and food at same location
    # Note: Access environment via property
    crab = Crab(world.world.environment)
    crab.pos = Vector2(100.0, 100.0)
    crab.rect.topleft = (100, 100)

    food = Food(world.world.environment, 100, 100)

    # Add to world
    world.world.add_entity(crab)
    world.world.add_entity(food)

    # Verify food is present
    assert food in world.world.entities_list

    # Update collision system directly to test the specific phase
    # Note: We need to ensure the engine knows about the entities if we added them via world.add_entity
    # world.add_entity -> engine.add_entity -> entity_manager.add -> adds to grid too.

    # Run the collision phase
    # Run the collision phase
    world.world.engine._phase_collision()

    # Verify food is marked for removal
    removals = world.world.engine._frame_removals
    assert len(removals) > 0, "No removal requests generated"
    assert removals[0].reason == "crab_food_collision", "Wrong removal reason"
