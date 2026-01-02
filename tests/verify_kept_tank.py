import logging

from backend.tank_persistence import (
    find_all_tank_snapshots,
    load_tank_state,
    restore_tank_from_snapshot,
)
from core.simulation.engine import SimulationEngine

logging.basicConfig(level=logging.INFO)

# Find the tank we kept
snapshots = find_all_tank_snapshots()
if not snapshots:
    print("ERROR: No snapshots found after cleanup!")
    exit(1)

tank_id = list(snapshots.keys())[0]
snapshot_path = snapshots[tank_id]
print(f"Testing restoration of tank {tank_id} from {snapshot_path}")

# Load and Restore
snapshot = load_tank_state(snapshot_path)
if not snapshot:
    print("ERROR: Failed to load snapshot JSON")
    exit(1)

engine = SimulationEngine(headless=True)
engine.setup()


# Mock world wrapper
class MockWorld:
    def __init__(self, engine):
        self.engine = engine
        self.paused = True
        self.rng = engine.rng  # Emulate adapter check


world = MockWorld(engine)

try:
    success = restore_tank_from_snapshot(snapshot, world)
    if success:
        print(f"SUCCESS: Restored tank {tank_id} with {len(engine.entities_list)} entities.")
    else:
        print("FAILURE: restore_tank_from_snapshot returned False")
except Exception as e:
    print(f"CRASH: {e}")
    import traceback

    traceback.print_exc()
