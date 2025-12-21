import requests
import json
import time

def verify_poker_score():
    try:
        # Get list of servers
        print("Fetching servers...")
        response = requests.get("http://localhost:8000/api/servers")
        response.raise_for_status()
        data = response.json()
        
        servers = data.get("servers", [])
        print(f"Found {len(servers)} servers")
        
        for server_entry in servers:
            tanks = server_entry.get("tanks", [])
            print(f"Checking {len(tanks)} tanks on server {server_entry['server']['server_id']}")
            
            for tank in tanks:
                stats = tank.get("stats", {})
                print(f"Tank: {tank['tank']['name']}")
                
                # Check for poker_score field
                if "poker_score" in stats:
                    print(f"  [PASS] 'poker_score' field found: {stats['poker_score']}")
                else:
                    print("  [FAIL] 'poker_score' field NOT found")
                    
                if "poker_score_history" in stats:
                     print(f"  [PASS] 'poker_score_history' field found: {len(stats['poker_score_history'])} entries")
                else:
                    print("  [FAIL] 'poker_score_history' field NOT found")

    except Exception as e:
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    verify_poker_score()
