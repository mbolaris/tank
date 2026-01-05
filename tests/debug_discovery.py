import logging
from pathlib import Path

from backend.world_persistence import DATA_DIR, find_all_world_snapshots

# Setup logging to stdout
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("backend.world_persistence")
logger.setLevel(logging.INFO)

print(f"Current Working Directory: {Path.cwd()}")
print(f"DATA_DIR: {DATA_DIR} (Resolved: {DATA_DIR.resolve()})")
print(f"DATA_DIR Exists: {DATA_DIR.exists()}")

if DATA_DIR.exists():
    print("Direct Listing of DATA_DIR:")
    for p in DATA_DIR.iterdir():
        print(f"  {p.name} (is_dir={p.is_dir()})")
        if p.is_dir():
            snap_dir = p / "snapshots"
            print(f"    Checking {snap_dir} (exists={snap_dir.exists()})")
            if snap_dir.exists():
                for s in snap_dir.iterdir():
                    print(f"      {s.name}")

print("\nCalling find_all_tank_snapshots()...")
snapshots = find_all_tank_snapshots()
print(f"Result: {snapshots}")

if not snapshots:
    print("FAILURE: No snapshots found via function!")
else:
    print(f"SUCCESS: Found {len(snapshots)} snapshots.")
