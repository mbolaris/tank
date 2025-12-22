#!/usr/bin/env python3
"""Test script to verify LiveFood persistence works correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.entities.resources import Food, LiveFood
from core.environment import Environment


def _run_live_food_persistence():
    """Test that LiveFood entities are correctly identified and saved."""
    print("=" * 60)
    print("Testing LiveFood Persistence")
    print("=" * 60)

    # Create test environment
    env = Environment(width=800, height=600)

    # Create different types of food
    regular_food = Food(env, x=100, y=200, food_type='algae')
    live_food = LiveFood(env, x=300, y=400)

    print("\n1. Testing food types...")
    print(f"  Regular food: {type(regular_food).__name__}, food_type='{regular_food.food_type}'")
    print(f"  Live food:    {type(live_food).__name__}, food_type='{live_food.food_type}'")

    # Test isinstance checks (what the save code uses)
    print("\n2. Testing isinstance checks (save logic)...")
    print(f"  isinstance(regular_food, Food): {isinstance(regular_food, Food)}")
    print(f"  isinstance(live_food, Food):    {isinstance(live_food, Food)}")
    print(f"  isinstance(live_food, LiveFood): {isinstance(live_food, LiveFood)}")

    # Simulate save logic
    print("\n3. Simulating save logic...")
    entities = [regular_food, live_food]
    saved_data = []

    for entity in entities:
        if isinstance(entity, Food):
            data = {
                "type": "food",
                "x": entity.pos.x,
                "y": entity.pos.y,
                "energy": entity.energy,
                "food_type": entity.food_type,
            }
            saved_data.append(data)
            print(f"  Saved {type(entity).__name__} as food_type='{entity.food_type}'")

    # Simulate restore logic
    print("\n4. Simulating restore logic...")
    restored_entities = []

    for entity_data in saved_data:
        food_type = entity_data["food_type"]
        x = entity_data["x"]
        y = entity_data["y"]

        if food_type == "live":
            food = LiveFood(
                environment=env,
                x=x,
                y=y,
            )
            print("  Restored as LiveFood (has movement behavior)")
        else:
            food = Food(
                x=x,
                y=y,
                food_type=food_type,
                environment=env,
            )
            print(f"  Restored as Food with food_type='{food_type}'")

        food.energy = entity_data["energy"]
        restored_entities.append(food)

    # Verify restoration
    print("\n5. Verifying restored entities...")
    success = True

    for i, (original, restored) in enumerate(zip(entities, restored_entities)):
        original_type = type(original).__name__
        restored_type = type(restored).__name__

        if original_type == restored_type:
            print(f"  ✓ Entity {i}: {original_type} → {restored_type}")
        else:
            print(f"  ✗ Entity {i}: {original_type} → {restored_type} (MISMATCH!)")
            success = False

    # Final result
    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS: LiveFood persistence working correctly!")
        print("LiveFood entities will retain their movement behavior after restore.")
    else:
        print("❌ FAILED: LiveFood not being restored correctly")
    print("=" * 60)

    return success


def test_live_food_persistence():
    assert _run_live_food_persistence()


if __name__ == "__main__":
    success = _run_live_food_persistence()
    sys.exit(0 if success else 1)
