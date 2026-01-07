"""Verify emergency (soup) fish spawning works in empty/low-population tanks."""

import sys

sys.path.insert(0, ".")

from core.config.ecosystem import CRITICAL_POPULATION_THRESHOLD, EMERGENCY_SPAWN_COOLDOWN
from core.entities import Fish
from core.tank_world import TankWorld


def count_fish(world):
    """Count fish in the simulation."""
    return len([e for e in world.entities_list if isinstance(e, Fish)])


def test_emergency_spawn_in_empty_tank():
    """Test that fish spawn automatically when tank is empty."""
    print("=" * 60)
    print("TEST: Emergency spawn in empty tank")
    print("=" * 60)

    # Create a tank
    world = TankWorld(seed=42)
    world.setup()

    # Clear all fish to simulate empty tank
    fish_to_remove = [e for e in world.entities_list if isinstance(e, Fish)]
    for fish in fish_to_remove:
        world.engine.remove_entity(fish)

    initial_count = count_fish(world)
    print(f"Initial fish count after clearing: {initial_count}")
    print(f"Ecosystem: {world.engine.ecosystem}")
    print(f"CRITICAL_POPULATION_THRESHOLD: {CRITICAL_POPULATION_THRESHOLD}")
    print(f"EMERGENCY_SPAWN_COOLDOWN: {EMERGENCY_SPAWN_COOLDOWN} frames (6 seconds at 30fps)")

    # Run simulation for enough frames to trigger emergency spawn
    # Emergency spawn happens every EMERGENCY_SPAWN_COOLDOWN=180 frames when fish_count < CRITICAL_POPULATION_THRESHOLD
    frames_to_run = EMERGENCY_SPAWN_COOLDOWN + 50  # Extra buffer

    print(f"\nRunning {frames_to_run} frames...")

    spawn_events = []
    for frame in range(frames_to_run):
        prev_count = count_fish(world)
        world.update()
        new_count = count_fish(world)

        if new_count > prev_count:
            spawn_events.append((frame, prev_count, new_count))
            print(f"  Frame {frame}: Fish spawned! {prev_count} -> {new_count}")

    final_count = count_fish(world)
    print(f"\nFinal fish count: {final_count}")
    print(f"Spawn events: {len(spawn_events)}")

    if final_count > initial_count:
        print("[PASS] Emergency spawning is working!")
        return True
    else:
        print("[FAIL] No fish spawned in empty tank!")
        return False


def test_emergency_spawn_in_low_population():
    """Test that fish spawn when population is below critical threshold."""
    print("\n" + "=" * 60)
    print("TEST: Emergency spawn in low-population tank")
    print("=" * 60)

    # Create a tank
    world = TankWorld(seed=42)
    world.setup()

    # Remove fish until below critical threshold
    fish_list = [e for e in world.entities_list if isinstance(e, Fish)]
    target_count = CRITICAL_POPULATION_THRESHOLD - 5  # Keep 5 fish (below threshold of 10)

    for fish in fish_list[target_count:]:
        world.engine.remove_entity(fish)

    initial_count = count_fish(world)
    print(f"Initial fish count (below threshold): {initial_count}")
    print(f"CRITICAL_POPULATION_THRESHOLD: {CRITICAL_POPULATION_THRESHOLD}")

    # Run simulation
    frames_to_run = EMERGENCY_SPAWN_COOLDOWN + 50
    print(f"\nRunning {frames_to_run} frames...")

    spawn_events = []
    for frame in range(frames_to_run):
        prev_count = count_fish(world)
        world.update()
        new_count = count_fish(world)

        if new_count > prev_count:
            spawn_events.append((frame, prev_count, new_count))
            print(f"  Frame {frame}: Fish spawned! {prev_count} -> {new_count}")

    final_count = count_fish(world)
    print(f"\nFinal fish count: {final_count}")
    print(f"Spawn events: {len(spawn_events)}")

    if final_count > initial_count:
        print("[PASS] Emergency spawning is working!")
        return True
    else:
        print("[FAIL] No fish spawned in low-population tank!")
        return False


def diagnose_spawn_conditions():
    """Diagnose why spawning might not be happening."""
    print("\n" + "=" * 60)
    print("DIAGNOSTICS: Spawn conditions")
    print("=" * 60)

    world = TankWorld(seed=42)
    world.setup()

    engine = world.engine

    # Clear all fish
    fish_to_remove = [e for e in world.entities_list if isinstance(e, Fish)]
    for fish in fish_to_remove:
        engine.remove_entity(fish)

    print(f"ecosystem: {engine.ecosystem}")
    print(f"environment: {engine.environment}")
    print(f"fish_count: {count_fish(world)}")
    print(f"frame_count: {engine.frame_count}")
    print(f"last_emergency_spawn_frame: {engine.last_emergency_spawn_frame}")

    frames_since = engine.frame_count - engine.last_emergency_spawn_frame
    print(f"frames_since_last_spawn: {frames_since}")
    print(f"EMERGENCY_SPAWN_COOLDOWN: {EMERGENCY_SPAWN_COOLDOWN}")
    print(f"Cooldown satisfied: {frames_since >= EMERGENCY_SPAWN_COOLDOWN}")

    # Check spawn probability
    fish_list = engine.get_fish_list()
    fish_count = len(fish_list)

    from core.config.ecosystem import MAX_POPULATION

    print(
        f"\nfish_count < MAX_POPULATION: {fish_count} < {MAX_POPULATION} = {fish_count < MAX_POPULATION}"
    )
    print(
        f"fish_count < CRITICAL_POPULATION_THRESHOLD: {fish_count} < {CRITICAL_POPULATION_THRESHOLD} = {fish_count < CRITICAL_POPULATION_THRESHOLD}"
    )

    if fish_count < CRITICAL_POPULATION_THRESHOLD:
        print("spawn_probability = 1.0 (100%)")
    else:
        population_ratio = (fish_count - CRITICAL_POPULATION_THRESHOLD) / (
            MAX_POPULATION - CRITICAL_POPULATION_THRESHOLD
        )
        spawn_probability = (1.0 - population_ratio) ** 2 * 0.3
        print(f"spawn_probability = {spawn_probability:.4f}")


if __name__ == "__main__":
    diagnose_spawn_conditions()

    result1 = test_emergency_spawn_in_empty_tank()
    result2 = test_emergency_spawn_in_low_population()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Empty tank test: {'PASS' if result1 else 'FAIL'}")
    print(f"Low population test: {'PASS' if result2 else 'FAIL'}")

    sys.exit(0 if (result1 and result2) else 1)
