import urllib.request

url = "http://localhost:8000/api/lineage"
with urllib.request.urlopen(url) as r:
    data = r.read()
open("scripts/lineage_snapshot.json", "wb").write(data)
print("wrote", len(data), "bytes")
