import requests
import sys

try:
    response = requests.get("http://localhost:8000/api/transfers?limit=1&success_only=true")
    response.raise_for_status()
    print("Endpoint /api/transfers is working.")
    print(response.json())
except Exception as e:
    print(f"Error accessing /api/transfers: {e}")
    sys.exit(1)
