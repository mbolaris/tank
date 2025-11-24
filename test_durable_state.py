#!/usr/bin/env python3
"""
Durable State Test Script for Tank World

This script tests the durable state persistence functionality by:
1. Creating a new tank with fish
2. Running simulation for a period
3. Saving a snapshot
4. Simulating server restart by creating fresh registry
5. Loading the snapshot
6. Verifying all state was preserved correctly

Usage:
    python test_durable_state.py
"""

import json
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.tank_registry import TankRegistry
from backend.tank_persistence import save_tank_state, load_tank_state, restore_tank_from_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def wait_for_frames(manager, target_frame: int, timeout: float = 10.0):
    """Wait for simulation to reach a certain frame number."""
    start = time.time()
    while manager.runner.world.frame_count < target_frame:
        if time.time() - start > timeout:
            raise TimeoutError(f"Simulation did not reach frame {target_frame} in {timeout}s")
        time.sleep(0.1)


def verify_state_match(original_state, restored_state, tank_id: str):
    """Verify that original and restored states match."""
    errors = []

    # Check frame number
    if original_state['frame'] != restored_state['frame']:
        errors.append(
            f"Frame mismatch: original={original_state['frame']}, "
            f"restored={restored_state['frame']}"
        )

    # Check entity counts
    orig_entities = {e['type']: e for e in original_state['entities']}
    rest_entities = {e['type']: e for e in restored_state['entities']}

    orig_fish = [e for e in original_state['entities'] if e['type'] == 'Fish']
    rest_fish = [e for e in restored_state['entities'] if e['type'] == 'Fish']

    if len(orig_fish) != len(rest_fish):
        errors.append(
            f"Fish count mismatch: original={len(orig_fish)}, "
            f"restored={len(rest_fish)}"
        )

    # Check ecosystem stats
    orig_eco = original_state['ecosystem']
    rest_eco = restored_state['ecosystem']

    eco_fields = ['total_births', 'total_deaths', 'generation', 'current_population']
    for field in eco_fields:
        if orig_eco.get(field) != rest_eco.get(field):
            errors.append(
                f"Ecosystem {field} mismatch: original={orig_eco.get(field)}, "
                f"restored={rest_eco.get(field)}"
            )

    # Check metadata
    orig_meta = original_state['metadata']
    rest_meta = restored_state['metadata']

    if orig_meta['name'] != rest_meta['name']:
        errors.append(
            f"Tank name mismatch: original={orig_meta['name']}, "
            f"restored={rest_meta['name']}"
        )

    if errors:
        logger.error("State verification failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("✓ State verification passed!")
    return True


def main():
    """Run the durable state test."""
    print("\n" + "=" * 60)
    print("DURABLE STATE TEST - Tank World")
    print("=" * 60 + "\n")

    # Phase 1: Create and populate tank
    print("Phase 1: Creating tank and adding fish...")
    registry = TankRegistry(create_default=False)

    manager = registry.create_tank(
        name="Durable Test Tank",
        description="Testing durable state persistence",
        seed=42,  # Deterministic seed
    )

    logger.info(f"Created tank: {manager.tank_id}")

    # Start the simulation
    manager.start(start_paused=False)
    logger.info("Simulation started")

    # Add some fish using engine's spawn method
    tank_world = manager.runner.world
    for i in range(5):
        tank_world.engine.spawn_emergency_fish()

    initial_fish_count = len(tank_world.engine.get_fish_list())
    logger.info(f"Added {initial_fish_count} fish")

    # Phase 2: Run simulation
    print("\nPhase 2: Running simulation for 100 frames...")
    target_frame = 100
    wait_for_frames(manager, target_frame)

    current_frame = tank_world.frame_count
    fish_count_before_save = len(tank_world.engine.get_fish_list())
    generation_before_save = tank_world.ecosystem.current_generation

    logger.info(f"Simulation reached frame {current_frame}")
    logger.info(f"Fish count: {fish_count_before_save}")
    logger.info(f"Generation: {generation_before_save}")
    logger.info(f"Total births: {tank_world.ecosystem.total_births}")
    logger.info(f"Total deaths: {tank_world.ecosystem.total_deaths}")

    # Phase 3: Save snapshot
    print("\nPhase 3: Saving snapshot...")
    snapshot_path = save_tank_state(manager.tank_id, manager)
    logger.info(f"Snapshot saved to: {snapshot_path}")

    # Load the snapshot data for verification
    with open(snapshot_path, 'r') as f:
        original_snapshot_data = json.load(f)

    logger.info(f"Snapshot contains {len(original_snapshot_data['entities'])} entities")

    # Phase 4: Simulate server restart
    print("\nPhase 4: Simulating server restart...")
    logger.info("Stopping original simulation...")
    manager.stop()

    # Clear registry (simulate server restart)
    del registry
    del manager

    logger.info("Creating fresh registry (simulating server restart)...")
    new_registry = TankRegistry(create_default=False)

    # Phase 5: Restore from snapshot
    print("\nPhase 5: Restoring from snapshot...")
    logger.info(f"Loading snapshot: {snapshot_path}")

    restored_manager = restore_tank_from_snapshot(snapshot_path, new_registry)
    logger.info(f"Tank restored: {restored_manager.tank_id}")

    # Start the restored simulation
    restored_manager.start(start_paused=True)
    logger.info("Restored simulation started (paused)")

    # Phase 6: Verify state
    print("\nPhase 6: Verifying restored state...")
    restored_tank_world = restored_manager.runner.world

    # Save restored state and compare snapshots
    import tempfile
    restored_snapshot_path = save_tank_state(restored_manager.tank_id, restored_manager)

    # Load restored snapshot for comparison
    with open(restored_snapshot_path, 'r') as f:
        restored_snapshot_data = json.load(f)

    # Compare states
    verification_passed = verify_state_match(
        original_snapshot_data,
        restored_snapshot_data,
        restored_manager.tank_id
    )

    # Additional detailed checks
    print("\nDetailed State Comparison:")
    print(f"  Frame Number:")
    print(f"    Original:  {original_snapshot_data['frame']}")
    print(f"    Restored:  {restored_snapshot_data['frame']}")
    print(f"    Match: {'✓' if original_snapshot_data['frame'] == restored_snapshot_data['frame'] else '✗'}")

    orig_fish = [e for e in original_snapshot_data['entities'] if e['type'] == 'Fish']
    rest_fish = [e for e in restored_snapshot_data['entities'] if e['type'] == 'Fish']

    print(f"\n  Fish Count:")
    print(f"    Original:  {len(orig_fish)}")
    print(f"    Restored:  {len(rest_fish)}")
    print(f"    Match: {'✓' if len(orig_fish) == len(rest_fish) else '✗'}")

    print(f"\n  Generation:")
    orig_gen = original_snapshot_data['ecosystem']['generation']
    rest_gen = restored_snapshot_data['ecosystem']['generation']
    print(f"    Original:  {orig_gen}")
    print(f"    Restored:  {rest_gen}")
    print(f"    Match: {'✓' if orig_gen == rest_gen else '✗'}")

    print(f"\n  Total Births:")
    orig_births = original_snapshot_data['ecosystem']['total_births']
    rest_births = restored_snapshot_data['ecosystem']['total_births']
    print(f"    Original:  {orig_births}")
    print(f"    Restored:  {rest_births}")
    print(f"    Match: {'✓' if orig_births == rest_births else '✗'}")

    print(f"\n  Total Deaths:")
    orig_deaths = original_snapshot_data['ecosystem']['total_deaths']
    rest_deaths = restored_snapshot_data['ecosystem']['total_deaths']
    print(f"    Original:  {orig_deaths}")
    print(f"    Restored:  {rest_deaths}")
    print(f"    Match: {'✓' if orig_deaths == rest_deaths else '✗'}")

    # Sample fish details
    if len(orig_fish) > 0 and len(rest_fish) > 0:
        print(f"\n  Sample Fish Details (first fish):")
        orig_first = orig_fish[0]
        # Find corresponding fish by ID (note: IDs will be different after restoration)
        # Instead, compare by position or other properties
        rest_first = rest_fish[0]

        print(f"    Energy:")
        print(f"      Original:  {orig_first.get('energy', 'N/A')}")
        print(f"      Restored:  {rest_first.get('energy', 'N/A')}")

        print(f"    Generation:")
        print(f"      Original:  {orig_first.get('generation', 'N/A')}")
        print(f"      Restored:  {rest_first.get('generation', 'N/A')}")

        print(f"    Age:")
        print(f"      Original:  {orig_first.get('age', 'N/A')}")
        print(f"      Restored:  {rest_first.get('age', 'N/A')}")

    # Cleanup
    print("\nPhase 7: Cleanup...")
    restored_manager.stop()
    logger.info("Restored simulation stopped")

    # Final result
    print("\n" + "=" * 60)
    if verification_passed:
        print("✓ DURABLE STATE TEST PASSED")
        print("=" * 60)
        print("\nAll state was successfully preserved and restored!")
        print(f"Snapshot location: {snapshot_path}")
        return 0
    else:
        print("✗ DURABLE STATE TEST FAILED")
        print("=" * 60)
        print("\nSome state mismatches were detected.")
        print("Check the logs above for details.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
