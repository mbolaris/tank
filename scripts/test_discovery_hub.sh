#!/bin/bash
# Test script for discovery hub pattern

set -e

echo "=========================================="
echo "Testing Discovery Hub Pattern"
echo "=========================================="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test servers..."
    pkill -f "TANK_SERVER_ID=hub-server" 2>/dev/null || true
    pkill -f "TANK_SERVER_ID=worker-1" 2>/dev/null || true
    pkill -f "TANK_SERVER_ID=worker-2" 2>/dev/null || true
    sleep 2
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Step 1: Start the discovery hub server
echo "Step 1: Starting discovery hub server on port 8000..."
TANK_SERVER_ID=hub-server TANK_API_PORT=8000 python -m backend.main > /tmp/hub-server.log 2>&1 &
HUB_PID=$!
echo "Hub server started (PID: $HUB_PID)"
sleep 5

# Check if hub server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "ERROR: Hub server failed to start"
    cat /tmp/hub-server.log
    exit 1
fi
echo "✓ Hub server is running"
echo ""

# Step 2: Start worker server 1
echo "Step 2: Starting worker server 1 on port 8001..."
TANK_SERVER_ID=worker-1 TANK_API_PORT=8001 \
  DISCOVERY_SERVER_URL=http://localhost:8000 \
  python -m backend.main > /tmp/worker-1.log 2>&1 &
WORKER1_PID=$!
echo "Worker 1 started (PID: $WORKER1_PID)"
sleep 5

# Check if worker 1 is running
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "ERROR: Worker 1 failed to start"
    cat /tmp/worker-1.log
    exit 1
fi
echo "✓ Worker 1 is running"
echo ""

# Step 3: Start worker server 2
echo "Step 3: Starting worker server 2 on port 8002..."
TANK_SERVER_ID=worker-2 TANK_API_PORT=8002 \
  DISCOVERY_SERVER_URL=http://localhost:8000 \
  python -m backend.main > /tmp/worker-2.log 2>&1 &
WORKER2_PID=$!
echo "Worker 2 started (PID: $WORKER2_PID)"
sleep 5

# Check if worker 2 is running
if ! curl -s http://localhost:8002/health > /dev/null; then
    echo "ERROR: Worker 2 failed to start"
    cat /tmp/worker-2.log
    exit 1
fi
echo "✓ Worker 2 is running"
echo ""

# Step 4: Verify registration
echo "Step 4: Checking server registration on hub..."
sleep 3  # Give time for registration and heartbeats

SERVERS=$(curl -s http://localhost:8000/api/discovery/servers)
echo "$SERVERS" | python3 -m json.tool

# Count registered servers (should be 3: hub + 2 workers)
SERVER_COUNT=$(echo "$SERVERS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('count', len(data.get('servers', []))))")
echo ""
echo "Registered servers: $SERVER_COUNT"

if [ "$SERVER_COUNT" -ge "3" ]; then
    echo "✓ All servers registered successfully!"
else
    echo "✗ Expected 3 servers, found $SERVER_COUNT"
    echo ""
    echo "Hub server log:"
    tail -20 /tmp/hub-server.log
    echo ""
    echo "Worker 1 log:"
    tail -20 /tmp/worker-1.log
    echo ""
    echo "Worker 2 log:"
    tail -20 /tmp/worker-2.log
    exit 1
fi
echo ""

# Step 5: Check worker can see other servers
echo "Step 5: Verifying worker 1 can query hub for servers..."
WORKER_VIEW=$(curl -s http://localhost:8001/api/discovery/servers)
WORKER_COUNT=$(echo "$WORKER_VIEW" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "Worker 1 sees $WORKER_COUNT servers in its local registry"
echo ""

# Step 6: Check server info details
echo "Step 6: Checking server details..."
echo "Hub server info:"
curl -s http://localhost:8000/api/servers/local | python3 -m json.tool | grep -E "(server_id|host|port)"
echo ""
echo "Worker 1 info:"
curl -s http://localhost:8001/api/servers/local | python3 -m json.tool | grep -E "(server_id|host|port)"
echo ""
echo "Worker 2 info:"
curl -s http://localhost:8002/api/servers/local | python3 -m json.tool | grep -E "(server_id|host|port)"
echo ""

echo "=========================================="
echo "✓ Discovery Hub Pattern Test PASSED"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Hub server running on port 8000"
echo "  - Worker 1 auto-registered and sending heartbeats"
echo "  - Worker 2 auto-registered and sending heartbeats"
echo "  - All servers visible in hub's registry"
echo ""
echo "Press Ctrl+C to stop all servers..."
sleep infinity
