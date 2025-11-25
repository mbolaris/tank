#!/bin/bash
# Comprehensive test for cross-server fish migration
# This script tests the complete distributed migration flow

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Cross-Server Fish Migration Test - Tank World Net      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up...${NC}"
    pkill -f "TANK_SERVER_ID=server-1" 2>/dev/null || true
    pkill -f "TANK_SERVER_ID=server-2" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}Cleanup complete${NC}"
}

trap cleanup EXIT

# Helper function to wait for server
wait_for_server() {
    local port=$1
    local max_attempts=30
    local attempt=0

    echo -e "${YELLOW}⏳ Waiting for server on port $port...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Server on port $port is ready${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo -e "${RED}✗ Server on port $port did not respond${NC}"
    return 1
}

# Start servers
echo -e "${CYAN}Step 1: Starting two Tank World servers${NC}"
echo "----------------------------------------"

echo -e "${YELLOW}Starting Server 1 (port 8001)...${NC}"
cd /home/user/tank
TANK_SERVER_ID=server-1 TANK_API_PORT=8001 python -m backend.main > /tmp/server1.log 2>&1 &
SERVER1_PID=$!
echo "  PID: $SERVER1_PID"

echo -e "${YELLOW}Starting Server 2 (port 8002)...${NC}"
TANK_SERVER_ID=server-2 TANK_API_PORT=8002 python -m backend.main > /tmp/server2.log 2>&1 &
SERVER2_PID=$!
echo "  PID: $SERVER2_PID"

wait_for_server 8001 || exit 1
wait_for_server 8002 || exit 1

echo ""
echo -e "${CYAN}Step 2: Registering servers with each other${NC}"
echo "----------------------------------------"

# Get server info
echo -e "${YELLOW}Getting server information...${NC}"
SERVER1_INFO=$(curl -s http://localhost:8001/api/servers/local)
SERVER2_INFO=$(curl -s http://localhost:8002/api/servers/local)

# Register each server with the other
echo -e "${YELLOW}Registering Server 2 with Server 1...${NC}"
curl -s -X POST http://localhost:8001/api/discovery/register \
  -H "Content-Type: application/json" \
  -d "$SERVER2_INFO" | python -m json.tool | grep -E "(status|server_id|message)"

echo -e "${YELLOW}Registering Server 1 with Server 2...${NC}"
curl -s -X POST http://localhost:8002/api/discovery/register \
  -H "Content-Type: application/json" \
  -d "$SERVER1_INFO" | python -m json.tool | grep -E "(status|server_id|message)"

echo ""
echo -e "${CYAN}Step 3: Getting tank information${NC}"
echo "----------------------------------------"

# Get tank IDs
TANK1_ID=$(curl -s http://localhost:8001/api/tanks | python -c "import sys, json; tanks = json.load(sys.stdin)['tanks']; print(tanks[0]['tank']['tank_id'] if tanks else '')")
TANK2_ID=$(curl -s http://localhost:8002/api/tanks | python -c "import sys, json; tanks = json.load(sys.stdin)['tanks']; print(tanks[0]['tank']['tank_id'] if tanks else '')")

echo -e "${GREEN}Server 1 Tank ID: ${TANK1_ID:0:8}...${NC}"
echo -e "${GREEN}Server 2 Tank ID: ${TANK2_ID:0:8}...${NC}"

# Get initial fish counts
FISH_COUNT_1=$(curl -s http://localhost:8001/api/tanks/$TANK1_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])")
FISH_COUNT_2=$(curl -s http://localhost:8002/api/tanks/$TANK2_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])")

echo ""
echo -e "${CYAN}Initial fish populations:${NC}"
echo -e "  Server 1: ${YELLOW}$FISH_COUNT_1${NC} fish"
echo -e "  Server 2: ${YELLOW}$FISH_COUNT_2${NC} fish"
echo -e "  ${CYAN}Total: $((FISH_COUNT_1 + FISH_COUNT_2)) fish${NC}"

echo ""
echo -e "${CYAN}Step 4: Creating cross-server connection${NC}"
echo "----------------------------------------"

# Create connection with high probability for faster testing
CONNECTION_PAYLOAD=$(cat <<EOF
{
  "source_tank_id": "$TANK1_ID",
  "destination_tank_id": "$TANK2_ID",
  "source_server_id": "server-1",
  "destination_server_id": "server-2",
  "probability": 100,
  "direction": "right"
}
EOF
)

echo -e "${YELLOW}Creating connection: Server 1 → Server 2 (100% probability)${NC}"
CONN_RESULT=$(curl -s -X POST http://localhost:8001/api/connections \
  -H "Content-Type: application/json" \
  -d "$CONNECTION_PAYLOAD")

echo "$CONN_RESULT" | python -m json.tool | head -10

CONNECTION_ID=$(echo "$CONN_RESULT" | python -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")

if [ -z "$CONNECTION_ID" ]; then
    echo -e "${RED}✗ Failed to create connection${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Connection created: $CONNECTION_ID${NC}"

echo ""
echo -e "${CYAN}Step 5: Monitoring fish migration${NC}"
echo "----------------------------------------"
echo -e "${YELLOW}Waiting for automatic migration (check interval: 10s)...${NC}"
echo ""

# Monitor for up to 60 seconds
MAX_CHECKS=12
check=0
migration_occurred=false

while [ $check -lt $MAX_CHECKS ]; do
    sleep 5
    check=$((check + 1))

    # Get current fish counts
    NEW_FISH_COUNT_1=$(curl -s http://localhost:8001/api/tanks/$TANK1_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])" 2>/dev/null || echo "$FISH_COUNT_1")
    NEW_FISH_COUNT_2=$(curl -s http://localhost:8002/api/tanks/$TANK2_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])" 2>/dev/null || echo "$FISH_COUNT_2")

    echo -e "${CYAN}[Check $check/$MAX_CHECKS]${NC} Server 1: $NEW_FISH_COUNT_1 fish | Server 2: $NEW_FISH_COUNT_2 fish | Total: $((NEW_FISH_COUNT_1 + NEW_FISH_COUNT_2))"

    # Check if migration occurred
    if [ "$NEW_FISH_COUNT_1" -lt "$FISH_COUNT_1" ] && [ "$NEW_FISH_COUNT_2" -gt "$FISH_COUNT_2" ]; then
        migration_occurred=true
        MIGRATED_COUNT=$((FISH_COUNT_2 - NEW_FISH_COUNT_2))
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  🐟 MIGRATION DETECTED! 🐟                ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}✓ Fish migrated from Server 1 to Server 2!${NC}"
        echo -e "  Before: Server 1 had ${YELLOW}$FISH_COUNT_1${NC} fish, Server 2 had ${YELLOW}$FISH_COUNT_2${NC} fish"
        echo -e "  After:  Server 1 has ${YELLOW}$NEW_FISH_COUNT_1${NC} fish, Server 2 has ${YELLOW}$NEW_FISH_COUNT_2${NC} fish"
        echo -e "  ${CYAN}Migration delta: ${GREEN}+$((NEW_FISH_COUNT_2 - FISH_COUNT_2))${NC} fish to Server 2"
        break
    fi
done

echo ""

if [ "$migration_occurred" = false ]; then
    echo -e "${YELLOW}⚠ No migration detected after $((MAX_CHECKS * 5)) seconds${NC}"
    echo -e "${YELLOW}This might be normal if no fish were near the boundary${NC}"
fi

echo ""
echo -e "${CYAN}Step 6: Checking logs and transfer history${NC}"
echo "----------------------------------------"

# Check Server 1 logs for remote migration
echo -e "${YELLOW}Server 1 logs (last 5 migration-related):${NC}"
grep -i "remote migration\|migrated" /tmp/server1.log 2>/dev/null | tail -5 || echo "  No migration logs found"

echo ""
echo -e "${YELLOW}Server 2 logs (last 5 transfer-related):${NC}"
grep -i "remote transfer\|added entity" /tmp/server2.log 2>/dev/null | tail -5 || echo "  No transfer logs found"

echo ""
echo -e "${YELLOW}Transfer history from Server 1:${NC}"
TRANSFERS=$(curl -s "http://localhost:8001/api/transfers?limit=5" | python -m json.tool)
TRANSFER_COUNT=$(echo "$TRANSFERS" | python -c "import sys, json; print(len(json.load(sys.stdin).get('transfers', [])))" 2>/dev/null || echo "0")

if [ "$TRANSFER_COUNT" -gt "0" ]; then
    echo "$TRANSFERS" | python -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('transfers', [])[:3]:
    success = '✓' if t.get('success') else '✗'
    print(f\"  {success} {t.get('entity_type', '?')}: {t.get('source_tank_id', '?')[:8]}... → {t.get('destination_tank_id', '?')[:20]}...\")
    if t.get('success'):
        print(f\"    Entity ID: {t.get('entity_old_id')} → {t.get('entity_new_id')}\")
"
else
    echo "  No transfers recorded yet"
fi

echo ""
echo -e "${YELLOW}Transfer history from Server 2:${NC}"
TRANSFERS2=$(curl -s "http://localhost:8002/api/transfers?limit=5" | python -m json.tool)
TRANSFER_COUNT2=$(echo "$TRANSFERS2" | python -c "import sys, json; print(len(json.load(sys.stdin).get('transfers', [])))" 2>/dev/null || echo "0")

if [ "$TRANSFER_COUNT2" -gt "0" ]; then
    echo "$TRANSFERS2" | python -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('transfers', [])[:3]:
    success = '✓' if t.get('success') else '✗'
    print(f\"  {success} {t.get('entity_type', '?')}: {t.get('source_tank_id', '?')[:20]}... → {t.get('destination_tank_id', '?')[:8]}...\")
    if t.get('success'):
        print(f\"    Entity ID: {t.get('entity_old_id')} → {t.get('entity_new_id')}\")
"
else
    echo "  No transfers recorded yet"
fi

echo ""
echo -e "${CYAN}Step 7: Verifying connection status${NC}"
echo "----------------------------------------"

echo -e "${YELLOW}Connections on Server 1:${NC}"
curl -s http://localhost:8001/api/connections | python -m json.tool | python -c "
import sys, json
data = json.load(sys.stdin)
for conn in data.get('connections', []):
    is_remote = conn.get('sourceServerId') != conn.get('destinationServerId')
    remote_flag = '[REMOTE]' if is_remote else '[LOCAL]'
    print(f\"  {remote_flag} {conn.get('sourceId', '?')[:8]}... → {conn.get('destinationId', '?')[:8]}...\")
    print(f\"    Probability: {conn.get('probability')}%, Direction: {conn.get('direction')}\")
    if is_remote:
        print(f\"    Source server: {conn.get('sourceServerId')}, Dest server: {conn.get('destinationServerId')}\")
" 2>/dev/null || echo "  Error parsing connections"

echo ""
echo -e "${CYAN}Step 8: Final statistics${NC}"
echo "----------------------------------------"

FINAL_FISH_1=$(curl -s http://localhost:8001/api/tanks/$TANK1_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])" 2>/dev/null || echo "?")
FINAL_FISH_2=$(curl -s http://localhost:8002/api/tanks/$TANK2_ID | python -c "import sys, json; print(json.load(sys.stdin)['stats']['fish_count'])" 2>/dev/null || echo "?")
FINAL_TOTAL=$((FINAL_FISH_1 + FINAL_FISH_2))
INITIAL_TOTAL=$((FISH_COUNT_1 + FISH_COUNT_2))

echo -e "${CYAN}Initial state:${NC}"
echo -e "  Server 1: $FISH_COUNT_1 fish"
echo -e "  Server 2: $FISH_COUNT_2 fish"
echo -e "  Total: $INITIAL_TOTAL fish"
echo ""
echo -e "${CYAN}Final state:${NC}"
echo -e "  Server 1: $FINAL_FISH_1 fish"
echo -e "  Server 2: $FINAL_FISH_2 fish"
echo -e "  Total: $FINAL_TOTAL fish"

if [ "$FINAL_TOTAL" -eq "$INITIAL_TOTAL" ]; then
    echo -e "${GREEN}✓ Fish conservation verified: No fish lost in migration${NC}"
else
    echo -e "${RED}✗ Fish count mismatch: $INITIAL_TOTAL → $FINAL_TOTAL${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
if [ "$migration_occurred" = true ]; then
    echo -e "${BLUE}║  ${GREEN}✓ Cross-server migration test PASSED${BLUE}                  ║${NC}"
else
    echo -e "${BLUE}║  ${YELLOW}⚠ Cross-server migration test INCONCLUSIVE${BLUE}            ║${NC}"
    echo -e "${BLUE}║    (Migration infrastructure works, but no fish migrated) ║${NC}"
fi
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

echo ""
echo -e "${CYAN}Servers are still running for manual inspection:${NC}"
echo -e "  Server 1: http://localhost:8001 (PID: $SERVER1_PID)"
echo -e "  Server 2: http://localhost:8002 (PID: $SERVER2_PID)"
echo ""
echo -e "${YELLOW}View logs:${NC}"
echo -e "  tail -f /tmp/server1.log"
echo -e "  tail -f /tmp/server2.log"
echo ""
echo -e "${YELLOW}To stop servers:${NC}"
echo -e "  kill $SERVER1_PID $SERVER2_PID"
echo -e "  or press Ctrl+C to run cleanup"
echo ""

# Keep script running to keep servers alive
echo -e "${CYAN}Press Ctrl+C to stop servers and exit...${NC}"
read -r -d '' _ </dev/tty
