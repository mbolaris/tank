import sys
import logging
from backend.tank_persistence import load_tank_state, restore_tank_from_snapshot
from core.worlds.tank.backend import TankWorldBackendAdapter
from core.simulation.engine import SimulationEngine

# Setup logging
logging.basicConfig(level=logging.DEBUG)

snapshot_path = r"c:\shared\bolaris\tank\data\tanks\3a0dee57-25bc-4adb-839f-87d1bb2ccb86\snapshots\snapshot_20260101_192200.json"

print(f"Loading snapshot from {snapshot_path}")
snapshot = load_tank_state(snapshot_path)
if not snapshot:
    print("Failed to load snapshot")
    sys.exit(1)

print(f"Snapshot loaded. Version: {snapshot.get('version')}")

# Create a mock/real storage for restoration
print("Creating Engine...")
engine = SimulationEngine(headless=True)
engine.setup()  # Initialize managers including root_spot_manager


# Adapter wrapper as expected by restore_tank_from_snapshot
class MockWorld:
    def __init__(self, engine):
        self.engine = engine
        self.paused = True


world = MockWorld(engine)

print("Attempting restoration...")
try:
    success = restore_tank_from_snapshot(snapshot, world)
    if success:
        print("Restoration SUCCESS!")
        print(f"Entities: {len(engine.entities_list)}")
    else:
        print("Restoration FAILED (returned False)")
except Exception as e:
    print(f"Restoration CRASHED: {e}")
    import traceback

    traceback.print_exc()
