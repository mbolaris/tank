"""Energy Economy Bug Hunter

Specifically looks for bugs in the energy flow:
1. Energy leaks (consumption without recording)
2. Double counting
3. Energy gain vs loss imbalances
4. Food collision issues
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import logging

logging.basicConfig(level=logging.WARNING)

from core.entities import Fish, Food
from core.entities.plant import PlantNectar
from core.tank_world import TankWorld, TankWorldConfig


def trace_energy_economy(tank: TankWorld, frames: int = 500):
    """Trace energy flow through the system to find bugs."""

    print("\n" + "="*70)
    print("ENERGY ECONOMY BUG ANALYSIS")
    print("="*70)

    # Track totals
    total_food_energy_spawned = 0.0
    total_food_energy_eaten = 0.0
    total_energy_consumed = 0.0
    fish_energy_start = 0.0
    fish_energy_end = 0.0

    # Track individual fish for one sample
    sample_fish = None
    sample_energy_log = []

    entities = tank.engine.get_all_entities()
    fish_list = [e for e in entities if isinstance(e, Fish)]
    if fish_list:
        sample_fish = fish_list[0]
        fish_energy_start = sum(f.energy for f in fish_list)

    prev_food_energy_sum = sum(
        e.energy for e in entities
        if isinstance(e, Food) or isinstance(e, PlantNectar)
    )

    for frame in range(frames):
        # Snapshot before update
        entities = tank.engine.get_all_entities()
        fish_list = [e for e in entities if isinstance(e, Fish)]
        food_list = [e for e in entities if isinstance(e, Food) or isinstance(e, PlantNectar)]

        fish_energy_before = sum(f.energy for f in fish_list)
        food_energy_before = sum(f.energy for f in food_list)

        # Track sample fish
        if sample_fish and sample_fish in fish_list:
            sample_energy_log.append(sample_fish.energy)

        # Run update
        tank.update()

        # Snapshot after update
        entities_after = tank.engine.get_all_entities()
        fish_list_after = [e for e in entities_after if isinstance(e, Fish)]
        food_list_after = [e for e in entities_after if isinstance(e, Food) or isinstance(e, PlantNectar)]

        fish_energy_after = sum(f.energy for f in fish_list_after)
        food_energy_after = sum(f.energy for f in food_list_after)

        # Calculate energy transfers
        fish_energy_delta = fish_energy_after - fish_energy_before
        food_energy_delta = food_energy_after - food_energy_before

        # New food spawned = positive food delta when no eating happened
        new_food_spawned = max(0, food_energy_after - food_energy_before + (fish_energy_after - fish_energy_before))

        # Frame 100 checkpoint
        if frame == 100:
            print("\nFrame 100 checkpoint:")
            print(f"  Fish count: {len(fish_list_after)}")
            print(f"  Food count: {len(food_list_after)}")
            print(f"  Total fish energy: {fish_energy_after:.1f}")
            print(f"  Total food energy: {food_energy_after:.1f}")
            if sample_fish and sample_fish in fish_list_after:
                print(f"  Sample fish energy: {sample_fish.energy:.1f}")

    # Final stats
    entities = tank.engine.get_all_entities()
    fish_list = [e for e in entities if isinstance(e, Fish)]
    food_list = [e for e in entities if isinstance(e, Food) or isinstance(e, PlantNectar)]

    fish_energy_end = sum(f.energy for f in fish_list)

    print("\n" + "-"*70)
    print("ENERGY FLOW SUMMARY")
    print("-"*70)

    print("\nFish energy:")
    print(f"  Start: {fish_energy_start:.1f}")
    print(f"  End: {fish_energy_end:.1f}")
    print(f"  Net change: {fish_energy_end - fish_energy_start:.1f}")

    print("\nFinal state:")
    print(f"  Fish count: {len(fish_list)}")
    print(f"  Food count: {len(food_list)}")

    # Analyze sample fish energy trend
    if sample_energy_log:
        print(f"\nSample fish energy trend (first {min(len(sample_energy_log), 10)} frames):")
        for i, e in enumerate(sample_energy_log[:10]):
            print(f"  Frame {i}: {e:.2f}")

        if len(sample_energy_log) > 1:
            avg_drain = (sample_energy_log[0] - sample_energy_log[-1]) / len(sample_energy_log)
            print(f"\n  Average energy drain: {avg_drain:.4f} per frame")
            print(f"  At 30fps: {avg_drain * 30:.2f} per second")
            print(f"  Time to starvation from 75 energy: {75 / (avg_drain * 30):.1f} seconds")

    # Check ecosystem stats if available
    if tank.ecosystem:
        print("\n" + "-"*70)
        print("ECOSYSTEM ENERGY TRACKING")
        print("-"*70)
        summary = tank.ecosystem.get_energy_source_summary()
        for source, amount in summary.items():
            print(f"  {source}: {amount:.1f}")

        # Check for imbalances
        total_gained = sum(v for k, v in summary.items() if not k.startswith('death'))
        print(f"\n  Total energy gained by fish: {total_gained:.1f}")

        death_causes = dict(tank.ecosystem.death_causes)
        print(f"\n  Deaths: {death_causes}")


def main():
    print("Starting energy economy bug hunt...")

    config = TankWorldConfig(
        max_population=100,
        auto_food_enabled=True,
    )

    tank = TankWorld(config=config)
    tank.setup()

    # Spawn initial population
    for _ in range(15):
        tank.engine.spawn_emergency_fish()

    fish_count = len([e for e in tank.engine.get_all_entities() if isinstance(e, Fish)])
    print(f"Starting with {fish_count} fish")

    trace_energy_economy(tank, frames=500)


if __name__ == "__main__":
    main()
