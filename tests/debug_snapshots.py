
from backend.tank_persistence import find_all_tank_snapshots, list_tank_snapshots
from pathlib import Path

print("DATA_DIR exists:", Path("data/tanks").exists())
print("Listing data/tanks content:")
for item in Path("data/tanks").iterdir():
    print(f"  {item.name} (is_dir={item.is_dir()})")
    if item.is_dir():
        snapshots = list_tank_snapshots(item.name)
        print(f"    Snapshots found: {len(snapshots)}")
        for snap in snapshots:
            print(f"      - {snap['filename']}")

print("\nRunning find_all_tank_snapshots():")
found = find_all_tank_snapshots()
print(f"Found {len(found)} tanks with snapshots: {found}")
