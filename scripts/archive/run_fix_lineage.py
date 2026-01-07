import subprocess
import sys
import urllib.request

url = "http://localhost:8000/api/lineage"
print("fetching", url)
with urllib.request.urlopen(url) as r:
    data = r.read()
with open("scripts/lineage_snapshot.json", "wb") as f:
    f.write(data)
print("wrote snapshot, running fixer")
rc = subprocess.call(
    [sys.executable, "scripts/fix_lineage.py", "--file", "scripts/lineage_snapshot.json", "--fix"]
)
print("fixer rc", rc)
