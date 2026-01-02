import json
from pathlib import Path

path = Path(
    r"c:\shared\bolaris\tank\data\tanks\3a0dee57-25bc-4adb-839f-87d1bb2ccb86\snapshots\snapshot_20260101_192200.json"
)

print(f"Checking {path}")
if path.exists():
    print(f"Size: {path.stat().st_size} bytes")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        print("JSON Load Success")
        print("Keys:", list(data.keys()))
        print("Entities count:", len(data.get("entities", [])))
    except Exception as e:
        print(f"JSON Load Failed: {e}")
        # Print first 100 chars
        with open(path, "r") as f:
            print("Head:", f.read(100))
else:
    print("File not found")
