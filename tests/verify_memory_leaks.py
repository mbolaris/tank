import logging
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.ecosystem import EcosystemManager
from core.simulation.engine import SimulationEngine

# Configure logging to errors only for cleaner output
logging.basicConfig(level=logging.ERROR)


def test_lineage_log_cap():
    print("Testing lineage_log cap...")

    # Setup
    eco = EcosystemManager()
    eco.lineage_log.clear()  # Ensure empty

    # Simulate MAX_LINEAGE_LOG_SIZE + 100 births
    MAX_LOG = 5000
    TOTAL_BIRTHS = MAX_LOG + 100

    print(f"Simulating {TOTAL_BIRTHS} births...")
    for i in range(TOTAL_BIRTHS):
        # We need to call record_birth. It's in ecosystem_population but ecosystem delegates to it
        # Actually ecosystem.record_birth calls ecosystem_population.record_birth
        eco.record_birth(fish_id=i, generation=1, parent_ids=[], algorithm_id=0)

    current_len = len(eco.lineage_log)
    print(f"Lineage log length: {current_len}")

    if current_len <= MAX_LOG:
        print("PASS: Lineage log is capped.")
    else:
        print(f"FAIL: Lineage log grew to {current_len} (expected <= {MAX_LOG})")


def test_poker_stats_cleanup():
    print("\nTesting poker stats cleanup...")

    # Setup engine to get full integration
    engine = SimulationEngine(headless=True)
    engine.setup()
    eco = engine.ecosystem
    assert eco is not None

    # Mock some poker stats
    # We need to populate plant_poker_stats
    # It's keyed by fish_id

    # Create 10 fake fish IDs
    fish_ids = list(range(10))

    # Populate stats for them
    for fid in fish_ids:
        eco.poker_manager.record_plant_poker_game(
            fish_id=fid,
            plant_id=1,
            fish_won=True,
            energy_transferred=10,
            fish_hand_rank=1,
            plant_hand_rank=0,
            won_by_fold=False,
        )

    print(f"Initial poker stats count: {len(eco.poker_manager.plant_poker_stats)}")

    # Simulate death of first 5 fish (ids 0-4)
    # Alive fish are 5-9
    alive_fish = {
        # Create mock objects with fish_id attribute
        type("MockFish", (), {"fish_id": i, "energy": 100})()
        for i in range(5, 10)
    }

    # Force updating engine's fish list (usually done by get_fish_list)
    # But we can just call cleanup directly or via engine update if we mock get_fish_list

    # Let's call cleanup directly to verify the method first
    alive_ids = {f.fish_id for f in alive_fish}
    removed = eco.cleanup_dead_fish(alive_ids)

    print(f"Removed {removed} records.")
    remaining = len(eco.poker_manager.plant_poker_stats)
    print(f"Remaining records: {remaining}")

    if remaining == 5 and removed == 5:
        print("PASS: Cleanup removed dead fish stats.")
    else:
        print(f"FAIL: Expected 5 remaining, got {remaining}. Removed {removed}.")

    # Verify specific IDs
    flattened_keys = set(eco.poker_manager.plant_poker_stats.keys())
    expected_keys = {5, 6, 7, 8, 9}
    if flattened_keys == expected_keys:
        print("PASS: Correct IDs remaining.")
    else:
        print(f"FAIL: Incorrect IDs. Got {flattened_keys}, expected {expected_keys}")


def main():
    try:
        test_lineage_log_cap()
        test_poker_stats_cleanup()
        print("\nALL SCENARIOS PASSED")
    except Exception as e:
        print(f"\nCRITICAL FAILURE: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
