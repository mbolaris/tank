"""Diagnose why fish aren't catching food despite plenty being available.

Tracks:
1. Do fish detect nearby food?
2. Are they actually moving toward it?
3. How many collisions (eating) happen per frame?
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import logging

logging.basicConfig(level=logging.WARNING)

from core.entities import Fish, Food
from core.entities.plant import PlantNectar
from core.tank_world import TankWorld, TankWorldConfig


def analyze_food_seeking(tank: TankWorld, frames: int = 1000):
    """Diagnose food-seeking effectiveness."""

    print("\n" + "=" * 70)
    print("FOOD-SEEKING BEHAVIOR DIAGNOSIS")
    print("=" * 70)

    # Per-frame tracking
    total_fish_frames = 0
    fish_near_food_count = 0  # Within 100px of any food
    fish_moving_toward_food_count = 0
    food_eaten_count = 0

    # Track food eaten events
    prev_food_ids = set()

    for frame in range(frames):
        entities = tank.engine.get_all_entities()
        fish_list = [e for e in entities if isinstance(e, Fish)]
        food_list = [e for e in entities if isinstance(e, (Food, PlantNectar))]

        current_food_ids = {id(f) for f in food_list}
        food_eaten_this_frame = len(prev_food_ids - current_food_ids)
        food_eaten_count += food_eaten_this_frame
        prev_food_ids = current_food_ids

        for fish in fish_list:
            if fish.is_dead():
                continue
            total_fish_frames += 1

            # Find nearest food
            nearest_food = None
            nearest_dist = float("inf")
            for food in food_list:
                dx = food.pos.x - fish.pos.x
                dy = food.pos.y - fish.pos.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_food = food

            if nearest_food and nearest_dist < 100:
                fish_near_food_count += 1

                # Check if fish is moving toward food
                if fish.vel.x != 0 or fish.vel.y != 0:
                    to_food_x = nearest_food.pos.x - fish.pos.x
                    to_food_y = nearest_food.pos.y - fish.pos.y
                    # Dot product to check alignment
                    dot = fish.vel.x * to_food_x + fish.vel.y * to_food_y
                    if dot > 0:
                        fish_moving_toward_food_count += 1

        tank.update()

        if frame % 200 == 0:
            avg_vel = 0
            if fish_list:
                avg_vel = sum((f.vel.x**2 + f.vel.y**2) ** 0.5 for f in fish_list) / len(fish_list)
            print(
                f"Frame {frame}: Fish={len(fish_list)}, Food={len(food_list)}, "
                f"FoodEaten={food_eaten_count}, AvgVel={avg_vel:.2f}"
            )

    # Print analysis
    print("\n" + "-" * 70)
    print("FOOD-SEEKING ANALYSIS")
    print("-" * 70)

    if total_fish_frames > 0:
        near_food_pct = fish_near_food_count / total_fish_frames * 100
        moving_toward_pct = fish_moving_toward_food_count / total_fish_frames * 100

        print(f"\nTotal fish-frames analyzed: {total_fish_frames}")
        print(f"Fish near food (<100px): {fish_near_food_count} ({near_food_pct:.1f}%)")
        print(
            f"Fish moving toward nearest food: {fish_moving_toward_food_count} ({moving_toward_pct:.1f}%)"
        )
        print(f"Food eaten (total): {food_eaten_count}")
        print(f"Food eaten per 1000 fish-frames: {food_eaten_count / total_fish_frames * 1000:.1f}")

        print("\n" + "-" * 70)
        print("INTERPRETATION")
        print("-" * 70)

        if near_food_pct < 30:
            print("[!] FOOD DISTRIBUTION ISSUE: Fish are rarely near food")
            print("    Fish and food may be in different parts of the tank")

        if near_food_pct > 30 and moving_toward_pct < near_food_pct * 0.5:
            print("[!] BEHAVIOR ISSUE: Fish near food but not moving toward it")
            print("    Food-seeking behavior may be overridden by other behaviors")

        eat_rate = food_eaten_count / (frames / 30)  # per second
        print(f"\n  Food eating rate: {eat_rate:.2f} food/second")

        if eat_rate < 0.5 and near_food_pct > 30:
            print("[!] CAPTURE ISSUE: Fish are near food but not eating it")
            print("    May be a collision detection or movement speed issue")


def main():
    print("Initializing simulation for food-seeking diagnosis...")

    config = TankWorldConfig(
        max_population=100,
        auto_food_enabled=True,
    )

    tank = TankWorld(config=config)
    tank.setup()

    # Spawn initial population
    for _ in range(20):
        tank.engine.spawn_emergency_fish()

    fish_count = len([e for e in tank.engine.get_all_entities() if isinstance(e, Fish)])
    print(f"Starting with {fish_count} fish")
    print("\nRunning 33 seconds of simulation (1000 frames)...")

    analyze_food_seeking(tank, frames=1000)


if __name__ == "__main__":
    main()
