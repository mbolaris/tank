from pathlib import Path
import backend.tank_persistence
from backend.tank_persistence import DATA_DIR, find_all_tank_snapshots

print(f"DATA_DIR from module: {DATA_DIR}")
print(f"Resolved DATA_DIR: {DATA_DIR.resolve()}")

print("\n--- Listing data/tanks ---")
if DATA_DIR.exists():
    for p in DATA_DIR.iterdir():
        print(f"{p.name} (is_dir={p.is_dir()})")
else:
    print("DATA_DIR does not exist")

print("\n--- Listing data/tanks_backup ---")
backup = Path("data/tanks_backup")
if backup.exists():
    for p in backup.iterdir():
        print(f"{p.name}")
else:
    print("tanks_backup does not exist")

print("\n--- find_all_tank_snapshots result ---")
snapshots = find_all_tank_snapshots()
print(f"Found {len(snapshots)} snapshots:")
for tid, path in snapshots.items():
    print(f"  {tid}: {path}")
