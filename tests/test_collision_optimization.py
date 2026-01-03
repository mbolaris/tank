import pytest
from core.entities import Crab, Food
from core.tank_world import TankWorld, TankWorldConfig
from core.math_utils import Vector2

def test_crab_eats_food_optimization():
    # Setup world
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config)
    world.setup()

    # Clear existing entities to ensure only our test crab and food are present
    # This prevents other fish from eating the food before the crab
    world.engine.entities_list.clear()
    if hasattr(world.engine, 'environment') and world.engine.environment:
        world.engine.environment.clear()

    # Create crab and food at same location
    # Note: Access environment via property
    crab = Crab(world.environment)
    crab.pos = Vector2(100.0, 100.0)
    crab.rect.topleft = (100, 100)

    food = Food(world.environment, 100, 100)

    # Add to world
    world.add_entity(crab)
    world.add_entity(food)
    
    # Verify food is present
    assert food in world.entities_list
    
    # Update collision system directly to test the specific phase
    # Note: We need to ensure the engine knows about the entities if we added them via world.add_entity
    # world.add_entity -> engine.add_entity -> entity_manager.add -> adds to grid too.
    
    # Run the collision phase
    # Run the collision phase
    world.engine._phase_collision()
    
    # Verify food is marked for removal
    removals = world.engine._frame_removals
    assert len(removals) > 0, "No removal requests generated"
    assert removals[0].reason == "crab_food_collision", "Wrong removal reason"
